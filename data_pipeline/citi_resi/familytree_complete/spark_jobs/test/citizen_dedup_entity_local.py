"""
Citizens Deduplication and Entity Resolution
Reads input from CSV (same folder) and writes outputs as local CSV files.
Paste your filenames/globs below and run with spark-submit.
"""
import hashlib
from pyspark.sql import SparkSession, Window
from pyspark.sql import functions as F
from pyspark.sql.types import StringType

# ── CONFIG: edit these paths only ──────────────────────────────────────────────
INPUT_PATH   = "./new_data_sc_map/person_master.csv"         # e.g. "./person_master.csv" or "./person_master/*.csv"
OUTPUT_DIR   = "./new_data_sc_map/output"                       # local folder for outputs
DELIMITER    = ","                           # CSV delimiter
HAS_HEADER   = True                          # set False if no header in source CSV
INFER_SCHEMA = True                          # set False to read all columns as strings
SINGLE_FILE  = True                          # True = one CSV per table (coalesce to 1)
# ──────────────────────────────────────────────────────────────────────────────

def completeness_score(cols):
    """Calculate completeness score based on non-null fields"""
    return sum([
        F.when(
            F.col(c).isNotNull() & (F.length(F.trim(F.col(c).cast("string"))) > 0),
            1
        ).otherwise(0)
        for c in cols
    ])

def main():
    spark = SparkSession.builder \
        .appName("citizens_dedup_entity_builder_csv") \
        .getOrCreate()

    print("=" * 80)
    print("CITIZENS DEDUPLICATION AND ENTITY RESOLUTION (CSV IN / CSV OUT)")
    print("=" * 80)

    # Read CSV input from same folder
    person_master = spark.read \
        .option("header", str(HAS_HEADER).lower()) \
        .option("inferSchema", str(INFER_SCHEMA).lower()) \
        .option("sep", DELIMITER) \
        .option("mode", "PERMISSIVE") \
        .option("multiLine", "true") \
        .option("quote", '"') \
        .option("escape", '"') \
        .csv(INPUT_PATH)

    print(f"✓ Loaded {person_master.count():,} records from CSV: {INPUT_PATH}")

    # Normalize fields for matching
    normalized = person_master \
    .withColumn("name_ar_norm", F.lower(F.trim(F.col("spm_full_aname")))) \
    .withColumn("name_en_norm", F.lower(F.trim(F.col("spm_full_ename")))) \
    .withColumn("dob_norm", F.to_date(F.col("spm_dob"), "MM/dd/yyyy")) \
    .withColumn("national_id_norm",
        F.regexp_replace(F.col("spm_national_id"), r"[\s\-]+", "")) \
    .withColumn("gender_norm", F.upper(F.trim(F.col("spm_gender").cast("string"))))

    # Clustering rules
    rule1_key = F.when(
        (F.col("national_id_norm").isNotNull()) &
        (F.col("dob_norm").isNotNull()),
        F.concat_ws("|", F.lit("NID"), F.col("national_id_norm"), F.col("dob_norm"))
    )

    rule2_key = F.when(
        (F.col("name_ar_norm").isNotNull()) &
        (F.col("dob_norm").isNotNull()) &
        (F.col("gender_norm").isNotNull()),
        F.concat_ws("|", F.lit("NAME"), F.col("name_ar_norm"),
                    F.col("dob_norm"), F.col("gender_norm"))
    )

    # Fallback: Use spm_person_no as anchor
    anchor_key = F.col("spm_person_no").cast(StringType())

    # Apply clustering
    clustered = normalized.withColumn(
        "cluster_key",
        F.coalesce(rule1_key, rule2_key, anchor_key)
    )

    # Generate entity_person_id as SHA256 hash
    @F.udf(returnType=StringType())
    def generate_entity_id(cluster_key):
        if cluster_key:
            hash_value = hashlib.sha256(cluster_key.encode('utf-8')).hexdigest()
            return f"C:{hash_value}"
        return None

    entities = clustered.withColumn(
        "entity_person_id",
        generate_entity_id(F.col("cluster_key"))
    )

    # Calculate completeness score
    value_cols = [
        "spm_full_aname", "spm_full_ename", "spm_gender", "spm_dob",
        "spm_national_id", "spm_place_of_birth_eng", "nat_code_curr_nat",
        "emi_code", "cit_code"
    ]

    scored = entities.withColumn(
        "completeness",
        completeness_score(value_cols)
    )

    # Select best record per entity
    window = Window.partitionBy("entity_person_id").orderBy(
        F.col("completeness").desc(),
        F.coalesce(F.col("spm_modified_date"), F.col("spm_created_date")).desc_nulls_last()
    )

    best_records = scored \
        .withColumn("rank", F.row_number().over(window)) \
        .filter(F.col("rank") == 1) \
        .drop("rank")

    # Create person_entity table (golden records)
    person_entity = best_records.select(
        F.col("entity_person_id"),
        F.col("spm_person_no").alias("primary_spm_person_no"),
        F.col("spm_full_aname").alias("full_name_ar"),
        F.col("spm_full_ename").alias("full_name_en"),
        F.coalesce(F.col("spm_full_ename"), F.col("spm_full_aname")).alias("full_name"),
        F.when(F.col("spm_gender") == 1, "M")
         .when(F.col("spm_gender") == 2, "F")
         .otherwise(None).alias("sex"),
        F.col("spm_dob").alias("dob"),
        F.col("spm_national_id").alias("national_id"),
        F.col("spm_place_of_birth_eng").alias("place_of_birth"),
        F.col("nat_code_curr_nat").alias("nationality_code"),
        F.col("emi_code").alias("emirate_code"),
        F.col("cit_code").alias("city_code"),
        F.coalesce(F.col("spm_modified_date"), F.col("spm_created_date")).alias("updated_at"),
        F.col("completeness"),
        F.lit("citizen").alias("person_type")
    )

    # Create person_alias table (all spm_person_no mappings)
    person_alias = entities.select(
        F.col("entity_person_id"),
        F.col("spm_person_no"),
        F.col("cluster_key"),
        F.when(F.col("cluster_key").startswith("NID|"), 1.0)
         .when(F.col("cluster_key").startswith("NAME|"), 0.9)
         .otherwise(0.8).alias("confidence"),
        F.lit("person_master_csv").alias("source")
    ).dropDuplicates(["spm_person_no"])

    # ── Write outputs as local CSVs ──────────────────────────────────────────────
    out_entity = f"{OUTPUT_DIR.rstrip('/')}/citizens_person_entity"
    out_alias  = f"{OUTPUT_DIR.rstrip('/')}/citizens_person_alias"

    if SINGLE_FILE:
        pe = person_entity.coalesce(1)
        pa = person_alias.coalesce(1)
    else:
        pe = person_entity
        pa = person_alias

    print(f"\n✓ Writing entities CSV to: {out_entity}")
    pe.write.mode("overwrite").option("header", "true").csv(out_entity)

    print(f"✓ Writing aliases CSV to:  {out_alias}")
    pa.write.mode("overwrite").option("header", "true").csv(out_alias)

    print("\n" + "=" * 80)
    print("✓ CITIZENS DEDUPLICATION COMPLETE (CSV outputs)")
    print("=" * 80)

    spark.stop()

if __name__ == "__main__":
    main()