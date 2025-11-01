"""
Citizens Deduplication and Entity Resolution
Handles person_master duplicates using multiple clustering rules
"""
from pyspark.sql import SparkSession, Window
from pyspark.sql import functions as F
from pyspark.sql.types import StringType
import hashlib

def completeness_score(cols):
    """Calculate completeness score based on non-null fields"""
    return sum([
        F.when(F.col(c).isNotNull() & (F.col(c) != ""), 1).otherwise(0) 
        for c in cols
    ])

def main():
    spark = SparkSession.builder \
        .appName("citizens_dedup_entity_builder") \
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions") \
        .config("spark.sql.catalog.lake", "org.apache.iceberg.spark.SparkCatalog") \
        .config("spark.sql.catalog.lake.type", "hadoop") \
        .config("spark.sql.catalog.lake.warehouse", "s3://digixt-lake/warehouse") \
        .getOrCreate()
    
    print("=" * 80)
    print("CITIZENS DEDUPLICATION AND ENTITY RESOLUTION")
    print("=" * 80)
    
    # Read from bronze layer
    person_master = spark.table("lake.bronze.person_master")
    print(f"✓ Loaded {person_master.count():,} records from person_master")
    
    # Normalize fields for matching
    normalized = person_master \
        .withColumn("name_ar_norm", F.lower(F.trim(F.col("spm_full_aname")))) \
        .withColumn("name_en_norm", F.lower(F.trim(F.col("spm_full_ename")))) \
        .withColumn("dob_norm", F.to_date(F.col("spm_dob"))) \
        .withColumn("national_id_norm", 
            F.regexp_replace(F.col("spm_national_id"), r"[\s\-]+", "")) \
        .withColumn("gender_norm", F.upper(F.trim(F.col("spm_gender"))))
    
    # Define clustering rules (priority order)
    
    # Rule 1: National ID + DOB (highest confidence)
    rule1_key = F.when(
        (F.col("national_id_norm").isNotNull()) & 
        (F.col("dob_norm").isNotNull()),
        F.concat_ws("|", F.lit("NID"), F.col("national_id_norm"), F.col("dob_norm"))
    )
    
    # Rule 2: Full Name + DOB + Gender (medium confidence)
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
        F.when(F.col("cluster_key").startsWith("NID|"), 1.0)
         .when(F.col("cluster_key").startsWith("NAME|"), 0.9)
         .otherwise(0.8).alias("confidence"),
        F.lit("person_master").alias("source")
    ).dropDuplicates(["spm_person_no"])
    
    # Write to silver layer
    spark.sql("CREATE SCHEMA IF NOT EXISTS lake.silver") #lake.silver -> transformed.xpin_transformed
    
    print(f"\n✓ Writing {person_entity.count():,} entities to silver.citizens_person_entity")
    person_entity.write \
        .mode("overwrite") \
        .format("iceberg") \
        .saveAsTable("lake.silver.citizens_person_entity")
    
    print(f"✓ Writing {person_alias.count():,} aliases to silver.citizens_person_alias")
    person_alias.write \
        .mode("overwrite") \
        .format("iceberg") \
        .saveAsTable("lake.silver.citizens_person_alias")
    
    print("\n" + "=" * 80)
    print("✓ CITIZENS DEDUPLICATION COMPLETE")
    print("=" * 80)
    
    spark.stop()

if __name__ == "__main__":
    main()
