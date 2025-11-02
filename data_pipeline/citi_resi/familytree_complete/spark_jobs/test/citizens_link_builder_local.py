"""
Citizens Link Builder (CSV in / CSV out)
Creates parent-child and spouse relationships from CSV inputs.
Place this script next to your CSV files and edit the CONFIG block below.
"""

from pyspark.sql import functions as F
from pyspark.sql import SparkSession


# ── CONFIG: edit only these paths/options ──────────────────────────────────────
# or "./citi_record_detail/*.csv"
CRD_CSV = "./../../data/citi_record_detail.csv"
# or "./citi_record_master/*.csv"
CRM_CSV = "./../../data/citi_record_master.csv"
# the alias CSVs produced by the previous job
ALIASES_CSV = "./out/citizens_person_alias/*.csv"
# local output folder for results
OUTPUT_DIR = "./out/out_links"
DELIMITER = ","                                    # source CSV delimiter
# set False if inputs have no header
HAS_HEADER = True
# set False to read all as strings
INFER_SCHEMA = True
# True => one CSV per output (coalesce to 1)
SINGLE_FILE = True
# ──────────────────────────────────────────────────────────────────────────────

def norm_id(col):
    """
    Normalize ID-like columns:
      - cast to string, trim, collapse spaces
      - strip trailing '.0'
      - drop non-alphanumeric chars
    Produces a join-safe key (e.g., '1000009.0' -> '1000009').
    """
    return F.regexp_replace(
             F.regexp_replace(
               F.regexp_replace(F.trim(F.col(col).cast("string")), r"\s+", ""),
               r"\.0$", ""
             ),
             r"[^0-9A-Za-z]", ""
           )

def main():
    spark = SparkSession.builder \
        .appName("citizens_link_builder_csv_local") \
        .getOrCreate()
    spark.sparkContext.setLogLevel("INFO")

    print("=" * 80)
    print("CITIZENS LINK BUILDER (CSV IN / CSV OUT)")
    print("=" * 80)

    # ---- Read inputs ----------------------------------------------------------
    common_read = (
        spark.read
        .option("header", str(HAS_HEADER).lower())
        .option("inferSchema", str(INFER_SCHEMA).lower())
        .option("sep", DELIMITER)
        .option("mode", "PERMISSIVE")
        .option("multiLine", "true")
        .option("quote", '"')
        .option("escape", '"')
    )

    crd = common_read.csv(CRD_CSV)
    crm = common_read.csv(CRM_CSV)
    aliases = common_read.csv(ALIASES_CSV)

    # Lowercase columns to avoid case mismatches across sources
    crd = crd.toDF(*[c.lower() for c in crd.columns])
    crm = crm.toDF(*[c.lower() for c in crm.columns])
    aliases = aliases.toDF(*[c.lower() for c in aliases.columns])

    print(f"✓ Loaded {crd.count():,} rows from {CRD_CSV}")
    print(f"✓ Loaded {crm.count():,} rows from {CRM_CSV}")
    print(f"✓ Loaded {aliases.count():,} rows from {ALIASES_CSV}")

    # ---- Normalize join keys (fixes parent IDs like '1000009.0') --------------
    # CRD normalization
    crd = (crd
        .withColumn("spm_person_no_n",        norm_id("spm_person_no"))
        .withColumn("spm_person_no_father_n", norm_id("spm_person_no_father"))
        .withColumn("spm_person_no_mother_n", norm_id("spm_person_no_mother"))
        .withColumn("crm_seq_n",              norm_id("crm_seq"))
    )

    # CRM normalization
    crm = (crm
        .withColumn("crm_seq_n",       norm_id("crm_seq"))
        .withColumn("spm_person_no_n", norm_id("spm_person_no"))
        .select("crm_seq_n", "spm_person_no_n")
        .dropDuplicates()
    )

    # Aliases normalization (accepts the real person_alias)
    # Expect columns: spm_person_no, entity_person_id
    aliases = (aliases
        .withColumn("spm_person_no_n", norm_id("spm_person_no"))
        .withColumn("entity_person_id", F.col("entity_person_id").cast("string"))
        .select("spm_person_no_n", "entity_person_id")
        .dropna(subset=["spm_person_no_n", "entity_person_id"])
        .dropDuplicates()
    )

    # ==================== PARENT LINKS ====================
    print("\nBuilding parent-child relationships...")

    # Map child spm_person_no to entity_person_id
    child_with_eid = crd.join(
        aliases.withColumnRenamed("spm_person_no_n", "child_spm"),
        crd.spm_person_no_n == F.col("child_spm"),
        "left"
    ).withColumnRenamed("entity_person_id", "child_eid")

    # Map father spm_person_no to entity_person_id
    with_father = child_with_eid.join(
        aliases.withColumnRenamed("spm_person_no_n", "father_spm"),
        child_with_eid.spm_person_no_father_n == F.col("father_spm"),
        "left"
    ).withColumnRenamed("entity_person_id", "father_eid")

    # Map mother spm_person_no to entity_person_id
    with_both_parents = with_father.join(
        aliases.withColumnRenamed("spm_person_no_n", "mother_spm"),
        with_father.spm_person_no_mother_n == F.col("mother_spm"),
        "left"
    ).withColumnRenamed("entity_person_id", "mother_eid")

    # Create parent links
    father_links = with_both_parents \
        .filter((F.col("father_eid").isNotNull()) & (F.col("child_eid").isNotNull())) \
        .select(
            F.col("father_eid").alias("parent_entity_person_id"),
            F.col("child_eid").alias("child_entity_person_id"),
            F.lit("father").alias("parent_type"),
            F.lit("crd_father").alias("source"),
            F.lit(1.0).alias("confidence")
        ).dropDuplicates()

    mother_links = with_both_parents \
        .filter((F.col("mother_eid").isNotNull()) & (F.col("child_eid").isNotNull())) \
        .select(
            F.col("mother_eid").alias("parent_entity_person_id"),
            F.col("child_eid").alias("child_entity_person_id"),
            F.lit("mother").alias("parent_type"),
            F.lit("crd_mother").alias("source"),
            F.lit(1.0).alias("confidence")
        ).dropDuplicates()

    parent_links = father_links.union(mother_links).dropDuplicates(
        ["parent_entity_person_id", "child_entity_person_id"]
    )

    # ==================== SPOUSE LINKS ====================
    print("Building spouse relationships...")

    # Family head (crm_seq -> spm_person_no -> entity_person_id) on normalized keys
    head_with_eid = crm.join(
        aliases,
        "spm_person_no_n",     # normalized join
        "left"
    ).select(
        F.col("crm_seq_n"),
        F.col("entity_person_id").alias("head_eid")
    )

    # Wives (rel1_code == 2), robust to '2', '02', '2.0'
    wives = with_both_parents.where(
        F.regexp_replace(F.col("rel1_code").cast("string"), r"\.0$", "") == F.lit("2")
    ).select(
        F.col("crm_seq_n"),
        F.col("child_eid").alias("wife_eid")
    ).dropDuplicates()

    spouse_links = wives.join(
        head_with_eid,
        "crm_seq_n",           # normalized join
        "left"
    ).filter(
        (F.col("wife_eid").isNotNull()) &
        (F.col("head_eid").isNotNull()) &
        (F.col("wife_eid") != F.col("head_eid"))
    ).select(
        F.col("head_eid").alias("husband_entity_person_id"),
        F.col("wife_eid").alias("wife_entity_person_id"),
        F.lit("rel1_code=2").alias("source"),
        F.lit(0.9).alias("confidence")
    ).dropDuplicates()

    # ==================== FAMILY MEMBERSHIP ====================
    print("Building family membership...")

    family_membership = with_both_parents \
        .filter(F.col("child_eid").isNotNull() & F.col("crm_seq_n").isNotNull()) \
        .select(
            F.col("child_eid").alias("entity_person_id"),
            F.col("crm_seq_n").alias("crm_seq"),
            F.concat(F.lit("FAM:"), F.col("crm_seq_n")).alias("family_book_id"),
            F.lit("crd").alias("source")
        ).dropDuplicates()

    # Add family heads
    family_membership = family_membership.union(
        head_with_eid
        .filter(F.col("head_eid").isNotNull() & F.col("crm_seq_n").isNotNull())
        .select(
            F.col("head_eid").alias("entity_person_id"),
            F.col("crm_seq_n").alias("crm_seq"),
            F.concat(F.lit("FAM:"), F.col("crm_seq_n")).alias("family_book_id"),
            F.lit("crm").alias("source")
        )
    ).dropDuplicates(["entity_person_id", "crm_seq"])

    # ---- Write outputs as local CSVs ------------------------------------------
    out_parent = f"{OUTPUT_DIR.rstrip('/')}/citizens_parent_links"
    out_spouse = f"{OUTPUT_DIR.rstrip('/')}/citizens_spouse_links"
    out_fam    = f"{OUTPUT_DIR.rstrip('/')}/citizens_family_membership"

    if SINGLE_FILE:
        parent_links_w = parent_links.coalesce(1)
        spouse_links_w = spouse_links.coalesce(1)
        fam_members_w  = family_membership.coalesce(1)
    else:
        parent_links_w = parent_links
        spouse_links_w = spouse_links
        fam_members_w  = family_membership

    print(f"\n✓ Writing parent links CSV to: {out_parent}")
    parent_links_w.write.mode("overwrite").option("header", "true").csv(out_parent)

    print(f"✓ Writing spouse links CSV to: {out_spouse}")
    spouse_links_w.write.mode("overwrite").option("header", "true").csv(out_spouse)

    print(f"✓ Writing family membership CSV to: {out_fam}")
    fam_members_w.write.mode("overwrite").option("header", "true").csv(out_fam)

    print("\n" + "=" * 80)
    print("✓ CITIZENS LINK BUILDER COMPLETE (CSV outputs)")
    print("=" * 80)

    spark.stop()

if __name__ == "__main__":
    main()
