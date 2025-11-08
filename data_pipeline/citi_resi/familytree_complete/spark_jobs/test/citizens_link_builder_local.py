# """
# Citizens Link Builder (CSV in / CSV out)
# Creates parent-child and spouse relationships from CSV inputs.
# Place this script next to your CSV files and edit the CONFIG block below.
# """

# from pyspark.sql import functions as F
# from pyspark.sql import SparkSession


# # ── CONFIG: edit only these paths/options ──────────────────────────────────────
# # or "./citi_record_detail/*.csv"
# CRD_CSV = "./new_data_sc_map/citi_record_detail.csv"
# # or "./citi_record_master/*.csv"
# CRM_CSV = "./new_data_sc_map/citi_record_master.csv"
# # the alias CSVs produced by the previous job
# ALIASES_CSV = "./new_data_sc_map/output/citizens_person_alias/*.csv"
# # local output folder for results
# OUTPUT_DIR = "./new_data_sc_map/output/links"
# DELIMITER = ","                                    # source CSV delimiter
# # set False if inputs have no header
# HAS_HEADER = True
# # set False to read all as strings
# INFER_SCHEMA = True
# # True => one CSV per output (coalesce to 1)
# SINGLE_FILE = True
# # ──────────────────────────────────────────────────────────────────────────────

# def norm_id(col):
#     """
#     Normalize ID-like columns:
#       - cast to string, trim, collapse spaces
#       - strip trailing '.0'
#       - drop non-alphanumeric chars
#     Produces a join-safe key (e.g., '1000009.0' -> '1000009').
#     """
#     return F.regexp_replace(
#              F.regexp_replace(
#                F.regexp_replace(F.trim(F.col(col).cast("string")), r"\s+", ""),
#                r"\.0$", ""
#              ),
#              r"[^0-9A-Za-z]", ""
#            )

# def main():
#     spark = SparkSession.builder \
#         .appName("citizens_link_builder_csv_local") \
#         .getOrCreate()
#     spark.sparkContext.setLogLevel("INFO")

#     print("=" * 80)
#     print("CITIZENS LINK BUILDER (CSV IN / CSV OUT)")
#     print("=" * 80)

#     # ---- Read inputs ----------------------------------------------------------
#     common_read = (
#         spark.read
#         .option("header", str(HAS_HEADER).lower())
#         .option("inferSchema", str(INFER_SCHEMA).lower())
#         .option("sep", DELIMITER)
#         .option("mode", "PERMISSIVE")
#         .option("multiLine", "true")
#         .option("quote", '"')
#         .option("escape", '"')
#     )

#     crd = common_read.csv(CRD_CSV)
#     crm = common_read.csv(CRM_CSV)
#     aliases = common_read.csv(ALIASES_CSV)

#     # Lowercase columns to avoid case mismatches across sources
#     crd = crd.toDF(*[c.lower() for c in crd.columns])
#     crm = crm.toDF(*[c.lower() for c in crm.columns])
#     aliases = aliases.toDF(*[c.lower() for c in aliases.columns])

#     print(f"✓ Loaded {crd.count():,} rows from {CRD_CSV}")
#     print(f"✓ Loaded {crm.count():,} rows from {CRM_CSV}")
#     print(f"✓ Loaded {aliases.count():,} rows from {ALIASES_CSV}")

#     # ---- Normalize join keys (fixes parent IDs like '1000009.0') --------------
#     # CRD normalization
#     crd = (crd
#         .withColumn("spm_person_no_n",        norm_id("spm_person_no"))
#         .withColumn("spm_person_no_father_n", norm_id("spm_person_no_father"))
#         .withColumn("spm_person_no_mother_n", norm_id("spm_person_no_mother"))
#         .withColumn("crm_seq_n",              norm_id("crm_seq"))
#     )

#     # CRM normalization
#     crm = (crm
#         .withColumn("crm_seq_n",       norm_id("crm_seq"))
#         .withColumn("spm_person_no_n", norm_id("spm_person_no"))
#         .select("crm_seq_n", "spm_person_no_n")
#         .dropDuplicates()
#     )

#     # Aliases normalization (accepts the real person_alias)
#     # Expect columns: spm_person_no, entity_person_id
#     aliases = (aliases
#         .withColumn("spm_person_no_n", norm_id("spm_person_no"))
#         .withColumn("entity_person_id", F.col("entity_person_id").cast("string"))
#         .select("spm_person_no_n", "entity_person_id")
#         .dropna(subset=["spm_person_no_n", "entity_person_id"])
#         .dropDuplicates()
#     )

#     # ==================== PARENT LINKS ====================
#     print("\nBuilding parent-child relationships...")

#     # Map child spm_person_no to entity_person_id
#     child_with_eid = crd.join(
#         aliases.withColumnRenamed("spm_person_no_n", "child_spm"),
#         crd.spm_person_no_n == F.col("child_spm"),
#         "left"
#     ).withColumnRenamed("entity_person_id", "child_eid")

#     # Map father spm_person_no to entity_person_id
#     with_father = child_with_eid.join(
#         aliases.withColumnRenamed("spm_person_no_n", "father_spm"),
#         child_with_eid.spm_person_no_father_n == F.col("father_spm"),
#         "left"
#     ).withColumnRenamed("entity_person_id", "father_eid")

#     # Map mother spm_person_no to entity_person_id
#     with_both_parents = with_father.join(
#         aliases.withColumnRenamed("spm_person_no_n", "mother_spm"),
#         with_father.spm_person_no_mother_n == F.col("mother_spm"),
#         "left"
#     ).withColumnRenamed("entity_person_id", "mother_eid")

#     # Create parent links
#     father_links = with_both_parents \
#         .filter((F.col("father_eid").isNotNull()) & (F.col("child_eid").isNotNull())) \
#         .select(
#             F.col("father_eid").alias("parent_entity_person_id"),
#             F.col("child_eid").alias("child_entity_person_id"),
#             F.lit("father").alias("parent_type"),
#             F.lit("crd_father").alias("source"),
#             F.lit(1.0).alias("confidence")
#         ).dropDuplicates()

#     mother_links = with_both_parents \
#         .filter((F.col("mother_eid").isNotNull()) & (F.col("child_eid").isNotNull())) \
#         .select(
#             F.col("mother_eid").alias("parent_entity_person_id"),
#             F.col("child_eid").alias("child_entity_person_id"),
#             F.lit("mother").alias("parent_type"),
#             F.lit("crd_mother").alias("source"),
#             F.lit(1.0).alias("confidence")
#         ).dropDuplicates()

#     parent_links = father_links.union(mother_links).dropDuplicates(
#         ["parent_entity_person_id", "child_entity_person_id"]
#     )

#     # ==================== SPOUSE LINKS ====================
#     print("Building spouse relationships...")

#     # Family head (crm_seq -> spm_person_no -> entity_person_id) on normalized keys
#     head_with_eid = crm.join(
#         aliases,
#         "spm_person_no_n",     # normalized join
#         "left"
#     ).select(
#         F.col("crm_seq_n"),
#         F.col("entity_person_id").alias("head_eid")
#     )

#     # Wives (rel1_code == 2), robust to '2', '02', '2.0'
#     wives = with_both_parents.where(
#         F.regexp_replace(F.col("rel1_code").cast("string"), r"\.0$", "") == F.lit("2")
#     ).select(
#         F.col("crm_seq_n"),
#         F.col("child_eid").alias("wife_eid")
#     ).dropDuplicates()

#     spouse_links = wives.join(
#         head_with_eid,
#         "crm_seq_n",           # normalized join
#         "left"
#     ).filter(
#         (F.col("wife_eid").isNotNull()) &
#         (F.col("head_eid").isNotNull()) &
#         (F.col("wife_eid") != F.col("head_eid"))
#     ).select(
#         F.col("head_eid").alias("husband_entity_person_id"),
#         F.col("wife_eid").alias("wife_entity_person_id"),
#         F.lit("rel1_code=2").alias("source"),
#         F.lit(0.9).alias("confidence")
#     ).dropDuplicates()

#     # ==================== FAMILY MEMBERSHIP ====================
#     print("Building family membership...")

#     family_membership = with_both_parents \
#         .filter(F.col("child_eid").isNotNull() & F.col("crm_seq_n").isNotNull()) \
#         .select(
#             F.col("child_eid").alias("entity_person_id"),
#             F.col("crm_seq_n").alias("crm_seq"),
#             F.concat(F.lit("FAM:"), F.col("crm_seq_n")).alias("family_book_id"),
#             F.lit("crd").alias("source")
#         ).dropDuplicates()

#     # Add family heads
#     family_membership = family_membership.union(
#         head_with_eid
#         .filter(F.col("head_eid").isNotNull() & F.col("crm_seq_n").isNotNull())
#         .select(
#             F.col("head_eid").alias("entity_person_id"),
#             F.col("crm_seq_n").alias("crm_seq"),
#             F.concat(F.lit("FAM:"), F.col("crm_seq_n")).alias("family_book_id"),
#             F.lit("crm").alias("source")
#         )
#     ).dropDuplicates(["entity_person_id", "crm_seq"])

#     # ---- Write outputs as local CSVs ------------------------------------------
#     out_parent = f"{OUTPUT_DIR.rstrip('/')}/citizens_parent_links"
#     out_spouse = f"{OUTPUT_DIR.rstrip('/')}/citizens_spouse_links"
#     out_fam    = f"{OUTPUT_DIR.rstrip('/')}/citizens_family_membership"

#     if SINGLE_FILE:
#         parent_links_w = parent_links.coalesce(1)
#         spouse_links_w = spouse_links.coalesce(1)
#         fam_members_w  = family_membership.coalesce(1)
#     else:
#         parent_links_w = parent_links
#         spouse_links_w = spouse_links
#         fam_members_w  = family_membership

#     print(f"\n✓ Writing parent links CSV to: {out_parent}")
#     parent_links_w.write.mode("overwrite").option("header", "true").csv(out_parent)

#     print(f"✓ Writing spouse links CSV to: {out_spouse}")
#     spouse_links_w.write.mode("overwrite").option("header", "true").csv(out_spouse)

#     print(f"✓ Writing family membership CSV to: {out_fam}")
#     fam_members_w.write.mode("overwrite").option("header", "true").csv(out_fam)

#     print("\n" + "=" * 80)
#     print("✓ CITIZENS LINK BUILDER COMPLETE (CSV outputs)")
#     print("=" * 80)

#     spark.stop()

# if __name__ == "__main__":
#     main()

"""
Citizens Link Builder - V5 SIMPLIFIED WITH SIBLING RELATIONSHIPS
- Removed biological parent fields
- Parent-child links based ONLY on spm_person_no_father/mother
- NEW: Sibling relationship builder (full, half-paternal, half-maternal, step)
- Does NOT form links to foreign men with Emirati women
"""
from pyspark.sql import functions as F
from pyspark.sql import SparkSession

# ── CONFIG ─────────────────────────────────────────────────────────────────
CRD_CSV = "./new_data_sc_map/citi_record_detail_enriched_v5.csv"
CRM_CSV = "./new_data_sc_map/citi_record_master_enriched_v5.csv"
PERSON_CSV = "./new_data_sc_map/person_master_enriched_v5.csv"
ALIASES_CSV = "./new_data_sc_map/output/citizens_v5/citizens_person_alias/*.csv"
ENTITY_CSV = "./new_data_sc_map/output/citizens_v5/citizens_person_entity/*.csv"
OUTPUT_DIR = "./new_data_sc_map/output/citizens_v5"
DELIMITER = ","
HAS_HEADER = True
INFER_SCHEMA = True
SINGLE_FILE = True
# ───────────────────────────────────────────────────────────────────────────

def main():
    spark = SparkSession.builder \
        .appName("citizens_link_builder_v5") \
        .config("spark.sql.legacy.timeParserPolicy", "LEGACY") \
        .getOrCreate()

    print("=" * 80)
    print("CITIZENS LINK BUILDER - V5 (SIMPLIFIED + SIBLING RELATIONSHIPS)")
    print("=" * 80)

    # Common read function
    def common_read(path):
        return spark.read \
            .option("header", str(HAS_HEADER).lower()) \
            .option("inferSchema", str(INFER_SCHEMA).lower()) \
            .option("sep", DELIMITER) \
            .csv(path)

    # Read inputs
    print(f"Reading {CRD_CSV}...")
    crd = common_read(CRD_CSV)

    print(f"Reading {CRM_CSV}...")
    crm = common_read(CRM_CSV)

    print(f"Reading {PERSON_CSV}...")
    person_master = common_read(PERSON_CSV)

    print(f"Reading {ALIASES_CSV}...")
    aliases = common_read(ALIASES_CSV)

    print(f"Reading {ENTITY_CSV}...")
    entities = common_read(ENTITY_CSV)

    print(f"✓ Loaded CRD: {crd.count():,} records")
    print(f"✓ Loaded CRM: {crm.count():,} records")
    print(f"✓ Loaded Person Master: {person_master.count():,} records")
    print(f"✓ Loaded Aliases: {aliases.count():,} records")
    print(f"✓ Loaded Entities: {entities.count():,} records")

    # Normalize crm_seq
    crd = crd.withColumn("crm_seq_n", F.trim(F.col("crm_seq")))
    crm = crm.withColumn("crm_seq_n", F.trim(F.col("crm_seq")))

    # Join CRD with CRM to get event flags
    crd_with_flags = crd.join(
        crm.select("crm_seq_n", "divorce_event_flag", "widow_event_flag", "book_status"),
        "crm_seq_n",
        "left"
    )

    # Join CRD with person data
    crd_with_person = crd_with_flags.join(
        person_master.select(
            F.col("spm_person_no"),
            F.col("spm_gender").alias("person_gender"),
            F.col("is_emirati").alias("person_is_emirati"),
            F.col("naturalized_flag").alias("person_naturalized_flag")
        ),
        "spm_person_no",
        "left"
    )

    # ═══════════════════════════════════════════════════════════════════════
    # PARENT-CHILD LINKS (SIMPLIFIED)
    # ═══════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("BUILDING PARENT-CHILD LINKS (SIMPLIFIED)")
    print("=" * 80)

    # Extract father-child relationships (SIMPLIFIED - no biological fields)
    father_child = crd_with_person.filter(
        (F.col("spm_person_no_father").isNotNull()) &
        (F.trim(F.col("spm_person_no_father")) != "")
    ).select(
        F.col("spm_person_no_father").alias("father_spm"),
        F.col("spm_person_no").alias("child_spm"),
        F.col("crm_seq_n"),
        F.col("person_is_emirati").alias("child_is_emirati"),
        F.col("crd_del_flag")
    )

    # Extract mother-child relationships (SIMPLIFIED - no biological fields)
    mother_child = crd_with_person.filter(
        (F.col("spm_person_no_mother").isNotNull()) &
        (F.trim(F.col("spm_person_no_mother")) != "")
    ).select(
        F.col("spm_person_no_mother").alias("mother_spm"),
        F.col("spm_person_no").alias("child_spm"),
        F.col("crm_seq_n"),
        F.col("person_is_emirati").alias("child_is_emirati"),
        F.col("crd_del_flag")
    )

    # Convert to entity IDs - Father links
    father_eid = father_child \
        .join(aliases.select("spm_person_no", "entity_person_id"),
            father_child["father_spm"] == aliases["spm_person_no"], "left") \
        .withColumnRenamed("entity_person_id", "parent_entity_person_id") \
        .drop("spm_person_no")

    father_eid = father_eid \
        .join(aliases.select("spm_person_no", "entity_person_id"),
            father_eid["child_spm"] == aliases["spm_person_no"], "left") \
        .withColumnRenamed("entity_person_id", "child_entity_person_id") \
        .drop("spm_person_no")

    # Convert to entity IDs - Mother links
    mother_eid = mother_child \
        .join(aliases.select("spm_person_no", "entity_person_id"),
            mother_child["mother_spm"] == aliases["spm_person_no"], "left") \
        .withColumnRenamed("entity_person_id", "parent_entity_person_id") \
        .drop("spm_person_no")

    mother_eid = mother_eid \
        .join(aliases.select("spm_person_no", "entity_person_id"),
            mother_eid["child_spm"] == aliases["spm_person_no"], "left") \
        .withColumnRenamed("entity_person_id", "child_entity_person_id") \
        .drop("spm_person_no")

    # Combine parent links
    parent_links = father_eid.withColumn("relationship_type", F.lit("father")) \
        .union(
            mother_eid.withColumn("relationship_type", F.lit("mother"))
        )

    parent_links = parent_links.select(
        "parent_entity_person_id",
        "child_entity_person_id",
        "relationship_type",
        "crm_seq_n",
        "child_is_emirati",
        "crd_del_flag"
    ).filter(
        F.col("parent_entity_person_id").isNotNull() &
        F.col("child_entity_person_id").isNotNull()
    ).dropDuplicates()

    print(f"✓ Extracted {parent_links.count():,} parent-child links")

    # ═══════════════════════════════════════════════════════════════════════
    # SIBLING RELATIONSHIPS (NEW!)
    # ═══════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("BUILDING SIBLING RELATIONSHIPS")
    print("=" * 80)

    # Get all children with their parents (ONLY children - rel1_code 3 or 4)
    children_with_parents = crd.filter(
        F.col("rel1_code").isin([3, 4])
    ).select(
        F.col("spm_person_no").alias("child_id"),
        F.col("spm_person_no_father").alias("father_id"),
        F.col("spm_person_no_mother").alias("mother_id"),
        F.col("crm_seq")
    )

    print(f"  Found {children_with_parents.count():,} children for sibling analysis")

    # Self-join to find potential siblings
    siblings_raw = children_with_parents.alias("c1").join(
        children_with_parents.alias("c2"),
        # Don't match a child with itself
        F.col("c1.child_id") != F.col("c2.child_id")
    )

    # Classify sibling types based on shared parents
    sibling_links = siblings_raw.withColumn(
        "sibling_type",
        F.when(
            # Full siblings: Same father AND same mother
            (F.col("c1.father_id") == F.col("c2.father_id")) &
            (F.col("c1.mother_id") == F.col("c2.mother_id")),
            "full_sibling"
        ).when(
            # Half-sibling (paternal): Same father, different mother
            (F.col("c1.father_id") == F.col("c2.father_id")) &
            (F.col("c1.mother_id") != F.col("c2.mother_id")),
            "half_sibling_paternal"
        ).when(
            # Half-sibling (maternal): Same mother, different father
            (F.col("c1.father_id") != F.col("c2.father_id")) &
            (F.col("c1.mother_id") == F.col("c2.mother_id")),
            "half_sibling_maternal"
        ).otherwise("no_biological_relation")
    ).filter(
        # Only keep actual siblings (not "no_biological_relation")
        F.col("sibling_type") != "no_biological_relation"
    )

    # Convert to entity IDs for sibling 1
    sibling_eid = sibling_links \
        .join(aliases.select("spm_person_no", "entity_person_id"),
              sibling_links["c1.child_id"] == aliases["spm_person_no"], "left") \
        .withColumnRenamed("entity_person_id", "sibling1_entity_person_id") \
        .drop("spm_person_no")

    # Convert to entity IDs for sibling 2
    sibling_eid = sibling_eid \
        .join(aliases.select("spm_person_no", "entity_person_id"),
              sibling_eid["c2.child_id"] == aliases["spm_person_no"], "left") \
        .withColumnRenamed("entity_person_id", "sibling2_entity_person_id") \
        .drop("spm_person_no")

    # Final sibling links
    sibling_links_final = sibling_eid.select(
        F.col("sibling1_entity_person_id"),
        F.col("sibling2_entity_person_id"),
        F.col("sibling_type"),
        F.col("c1.father_id").alias("shared_father"),
        F.col("c1.mother_id").alias("shared_mother")
    ).filter(
        F.col("sibling1_entity_person_id").isNotNull() &
        F.col("sibling2_entity_person_id").isNotNull()
    ).dropDuplicates()

    # Count each sibling type
    full_siblings = sibling_links_final.filter(F.col("sibling_type") == "full_sibling").count()
    half_paternal = sibling_links_final.filter(F.col("sibling_type") == "half_sibling_paternal").count()
    half_maternal = sibling_links_final.filter(F.col("sibling_type") == "half_sibling_maternal").count()

    print(f"✓ Extracted {sibling_links_final.count():,} sibling relationships:")
    print(f"  - Full siblings (same father & mother): {full_siblings}")
    print(f"  - Half-siblings paternal (same father): {half_paternal}")
    print(f"  - Half-siblings maternal (same mother): {half_maternal}")

    # ═══════════════════════════════════════════════════════════════════════
    # STEP-SIBLING RELATIONSHIPS (OPTIONAL - through spouse links)
    # ═══════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("IDENTIFYING STEP-SIBLING RELATIONSHIPS")
    print("=" * 80)

    # Step-siblings are children who:
    # 1. Have NO shared biological parent
    # 2. But their parents are married to each other

    # Get all spouse pairs (heads + wives)
    heads = crd_with_person.filter(F.col("rel1_code") == 1).select(
        F.col("spm_person_no").alias("head_spm"),
        F.col("crm_seq_n"),
        F.col("person_gender").alias("head_gender")
    )

    spouses = crd_with_person.filter(F.col("rel1_code") == 2).select(
        F.col("spm_person_no").alias("spouse_spm"),
        F.col("crm_seq_n"),
        F.col("crd_del_flag")
    )

    # Join to get married pairs
    married_pairs = heads.join(spouses, "crm_seq_n").filter(
        F.col("crd_del_flag") == 0  # Only active marriages
    )

    # Filter out female-headed books (foreign husbands)
    married_pairs = married_pairs.filter(F.col("head_gender") != 2)

    # Get children of each parent
    head_children = children_with_parents.select(
        F.col("father_id").alias("parent_id"),
        F.col("child_id").alias("head_child_id")
    )

    spouse_children = children_with_parents.select(
        F.col("mother_id").alias("parent_id"),
        F.col("child_id").alias("spouse_child_id")
    )

    # Find step-siblings: children of husband and children of wife with no shared parent
    step_siblings_raw = married_pairs \
        .join(head_children, married_pairs["head_spm"] == head_children["parent_id"], "left") \
        .join(spouse_children, married_pairs["spouse_spm"] == spouse_children["parent_id"], "left") \
        .filter(
            F.col("head_child_id").isNotNull() &
            F.col("spouse_child_id").isNotNull()
        )

    # Check they don't share biological parents
    step_siblings = step_siblings_raw.join(
        children_with_parents.alias("c1"),
        F.col("head_child_id") == F.col("c1.child_id")
    ).join(
        children_with_parents.alias("c2"),
        F.col("spouse_child_id") == F.col("c2.child_id")
    ).filter(
        # No shared father AND no shared mother
        (F.col("c1.father_id") != F.col("c2.father_id")) &
        (F.col("c1.mother_id") != F.col("c2.mother_id"))
    ).select(
        F.col("head_child_id").alias("stepsibling1_spm"),
        F.col("spouse_child_id").alias("stepsibling2_spm"),
        F.col("crm_seq_n").alias("family_book")
    )

    # Convert to entity IDs
    step_sibling_eid = step_siblings \
        .join(aliases.select("spm_person_no", "entity_person_id"),
              step_siblings["stepsibling1_spm"] == aliases["spm_person_no"], "left") \
        .withColumnRenamed("entity_person_id", "stepsibling1_entity_id") \
        .drop("spm_person_no")

    step_sibling_eid = step_sibling_eid \
        .join(aliases.select("spm_person_no", "entity_person_id"),
              step_sibling_eid["stepsibling2_spm"] == aliases["spm_person_no"], "left") \
        .withColumnRenamed("entity_person_id", "stepsibling2_entity_id") \
        .drop("spm_person_no")

    step_sibling_links = step_sibling_eid.select(
        F.col("stepsibling1_entity_id"),
        F.col("stepsibling2_entity_id"),
        F.lit("step_sibling").alias("sibling_type"),
        F.col("family_book")
    ).filter(
        F.col("stepsibling1_entity_id").isNotNull() &
        F.col("stepsibling2_entity_id").isNotNull()
    ).dropDuplicates()

    step_sibling_count = step_sibling_links.count()
    print(f"✓ Found {step_sibling_count} step-sibling relationships")
    print(f"  (Children whose parents are married but share no biological parent)")

    # ═══════════════════════════════════════════════════════════════════════
    # SPOUSE LINKS (WITH crd_del_flag)
    # ═══════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("BUILDING SPOUSE LINKS (WITH crd_del_flag)")
    print("=" * 80)

    # Get spouses with crd_del_flag
    spouses_all = crd_with_person.filter(F.col("rel1_code") == 2).select(
        F.col("spm_person_no"),
        F.col("crm_seq_n"),
        F.col("marriage_contract_date"),
        F.col("person_gender").alias("spouse_gender"),
        F.col("person_is_emirati").alias("spouse_is_emirati"),
        F.col("person_naturalized_flag").alias("spouse_naturalized"),
        F.col("crd_del_flag")
    )

    # Join spouses with heads
    spouse_pairs = spouses_all \
        .join(heads, "crm_seq_n") \
        .select(
            F.col("head_spm").alias("husband_spm"),
            F.col("spm_person_no").alias("wife_spm"),
            F.col("crm_seq_n"),
            F.col("marriage_contract_date"),
            F.col("head_gender"),
            F.col("spouse_is_emirati").alias("wife_is_emirati"),
            F.col("spouse_naturalized").alias("wife_naturalized"),
            F.col("crd_del_flag")
        )

    # CRITICAL: Filter out female-headed books (foreign husbands NOT in dataset)
    print("\n⚠ Filtering out female-headed books (foreign husbands)...")
    female_heads = spouse_pairs.filter(F.col("head_gender") == 2)
    female_head_count = female_heads.count()
    
    if female_head_count > 0:
        print(f"  Found {female_head_count} female-headed family books")
        print(f"  Foreign husbands are NOT in citizens' family books")
        spouse_pairs = spouse_pairs.filter(F.col("head_gender") != 2)
    
    # Track active vs divorced spouses
    active_spouses = spouse_pairs.filter(F.col("crd_del_flag") == 0).count()
    divorced_spouses = spouse_pairs.filter(F.col("crd_del_flag") == 1).count()
    
    print(f"✓ Spouse statistics:")
    print(f"  - Active spouses (crd_del_flag=0): {active_spouses}")
    print(f"  - Divorced/inactive spouses (crd_del_flag=1): {divorced_spouses}")

    # Convert to entity IDs
    spouse_eid = spouse_pairs \
        .join(aliases.select("spm_person_no", "entity_person_id"),
              spouse_pairs["husband_spm"] == aliases["spm_person_no"], "left") \
        .withColumnRenamed("entity_person_id", "husband_entity_person_id") \
        .drop("spm_person_no")

    spouse_eid = spouse_eid \
        .join(aliases.select("spm_person_no", "entity_person_id"),
              spouse_eid["wife_spm"] == aliases["spm_person_no"], "left") \
        .withColumnRenamed("entity_person_id", "wife_entity_person_id") \
        .drop("spm_person_no")

    spouse_links = spouse_eid.select(
        "husband_entity_person_id",
        "wife_entity_person_id",
        "crm_seq_n",
        "marriage_contract_date",
        "wife_is_emirati",
        "wife_naturalized",
        "crd_del_flag"
    ).filter(
        F.col("husband_entity_person_id").isNotNull() &
        F.col("wife_entity_person_id").isNotNull()
    ).dropDuplicates()

    print(f"✓ Created {spouse_links.count():,} spouse links")

    # ═══════════════════════════════════════════════════════════════════════
    # FEMALE-HEADED BOOKS
    # ═══════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("IDENTIFYING FEMALE-HEADED BOOKS")
    print("=" * 80)

    all_heads = heads.join(
        aliases.select("spm_person_no", "entity_person_id"),
        heads["head_spm"] == aliases["spm_person_no"],
        "left"
    )

    female_heads_detailed = all_heads.filter(F.col("head_gender") == 2)
    female_head_final_count = female_heads_detailed.count()

    print(f"✓ Identified {female_head_final_count} female-headed family books")
    print(f"  These represent Emirati women married to foreign men")

    female_heads_out = female_heads_detailed.select(
        "entity_person_id",
        "head_spm",
        "crm_seq_n"
    )

    # ═══════════════════════════════════════════════════════════════════════
    # FAMILY MEMBERSHIP
    # ═══════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("BUILDING FAMILY MEMBERSHIP")
    print("=" * 80)

    all_members = crd_with_person.select(
        F.col("spm_person_no"),
        F.col("crm_seq_n"),
        F.col("rel1_code"),
        F.col("person_gender").alias("spm_gender"),
        F.col("person_is_emirati").alias("is_emirati"),
        F.col("crd_del_flag")
    )

    family_membership = all_members \
        .join(aliases.select("spm_person_no", "entity_person_id"),
              "spm_person_no", "left") \
        .select(
            "entity_person_id",
            "crm_seq_n",
            F.when(F.col("rel1_code") == 1, "head")
             .when(F.col("rel1_code") == 2, "spouse")
             .when(F.col("rel1_code").isin([3, 4]), "child")
             .otherwise("other").alias("role_in_family"),
            "spm_gender",
            "is_emirati",
            "crd_del_flag"
        ).filter(F.col("entity_person_id").isNotNull()) \
        .dropDuplicates()

    print(f"✓ Extracted {family_membership.count():,} family memberships")

    # ═══════════════════════════════════════════════════════════════════════
    # WRITE OUTPUTS
    # ═══════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("WRITING OUTPUTS")
    print("=" * 80)

    out_parent = f"{OUTPUT_DIR.rstrip('/')}/citizens_parent_links"
    out_spouse = f"{OUTPUT_DIR.rstrip('/')}/citizens_spouse_links"
    out_sibling = f"{OUTPUT_DIR.rstrip('/')}/citizens_sibling_links"
    out_step_sibling = f"{OUTPUT_DIR.rstrip('/')}/citizens_step_sibling_links"
    out_family = f"{OUTPUT_DIR.rstrip('/')}/citizens_family_membership"
    out_female = f"{OUTPUT_DIR.rstrip('/')}/citizens_female_heads"

    if SINGLE_FILE:
        pl = parent_links.coalesce(1)
        sl = spouse_links.coalesce(1)
        sib = sibling_links_final.coalesce(1)
        step_sib = step_sibling_links.coalesce(1)
        fm = family_membership.coalesce(1)
        fh = female_heads_out.coalesce(1)
    else:
        pl = parent_links
        sl = spouse_links
        sib = sibling_links_final
        step_sib = step_sibling_links
        fm = family_membership
        fh = female_heads_out

    print(f"✓ Writing parent links to: {out_parent}")
    pl.write.mode("overwrite").option("header", "true").csv(out_parent)

    print(f"✓ Writing spouse links to: {out_spouse}")
    sl.write.mode("overwrite").option("header", "true").csv(out_spouse)

    print(f"✓ Writing sibling links to: {out_sibling}")
    sib.write.mode("overwrite").option("header", "true").csv(out_sibling)

    print(f"✓ Writing step-sibling links to: {out_step_sibling}")
    step_sib.write.mode("overwrite").option("header", "true").csv(out_step_sibling)

    print(f"✓ Writing family membership to: {out_family}")
    fm.write.mode("overwrite").option("header", "true").csv(out_family)

    print(f"✓ Writing female heads to: {out_female}")
    fh.write.mode("overwrite").option("header", "true").csv(out_female)

    # ═══════════════════════════════════════════════════════════════════════
    # VALIDATION SUMMARY
    # ═══════════════════════════════════════════════════════════════════════

    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY - V5 (SIMPLIFIED + SIBLING RELATIONSHIPS)")
    print("=" * 80)
    print(f"Parent-Child Links:                  {parent_links.count():,}")
    print(f"Spouse Links:                        {spouse_links.count():,}")
    print(f"  - Active (crd_del_flag=0):         {active_spouses}")
    print(f"  - Divorced (crd_del_flag=1):       {divorced_spouses}")
    print(f"Sibling Links (NEW):                 {sibling_links_final.count():,}")
    print(f"  - Full siblings:                   {full_siblings}")
    print(f"  - Half-siblings (paternal):        {half_paternal}")
    print(f"  - Half-siblings (maternal):        {half_maternal}")
    print(f"Step-Sibling Links (NEW):            {step_sibling_count}")
    print(f"Female-Headed Books:                 {female_head_final_count}")
    print(f"Family Memberships:                  {family_membership.count():,}")
    print("=" * 80)
    print("\n✓ LINK BUILDER COMPLETE - V5")
    print("  Biological fields removed - simplified structure")
    print("  Sibling relationships identified (full/half/step)")
    print("  Foreign husbands NOT included in spouse links")
    print("=" * 80)

    spark.stop()

if __name__ == "__main__":
    main()