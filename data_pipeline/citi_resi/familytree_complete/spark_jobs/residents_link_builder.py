"""
Residents Link Builder - Creates sponsorship relationships
"""
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

def main():
    spark = SparkSession.builder.appName("residents_link_builder").getOrCreate()
    
    print("RESIDENTS LINK BUILDER")
    
    residents_entity = spark.table("lake.silver.residents_person_entity")
    residents_alias = spark.table("lake.silver.residents_person_alias")
    citizens_alias = spark.table("lake.silver.citizens_person_alias")
    
    # Get sponsors from both citizens and residents
    all_sponsors = citizens_alias \
        .withColumnRenamed("spm_person_no", "sponsor_spm") \
        .withColumnRenamed("entity_person_id", "sponsor_entity_id") \
        .withColumn("sponsor_type", F.lit("citizen")) \
        .select("sponsor_spm", "sponsor_entity_id", "sponsor_type") \
        .union(
            residents_alias \
            .withColumnRenamed("spm_person_no", "sponsor_spm") \
            .withColumnRenamed("entity_person_id", "sponsor_entity_id") \
            .withColumn("sponsor_type", F.lit("resident")) \
            .select("sponsor_spm", "sponsor_entity_id", "sponsor_type")
        )
    
    # Create sponsorship links
    sponsorship_links = residents_entity.join(
        all_sponsors,
        residents_entity.sponsor_number == all_sponsors.sponsor_spm,
        "left"
    ).filter(
        "sponsor_entity_id IS NOT NULL AND entity_person_id IS NOT NULL"
    ).select(
        F.col("sponsor_entity_id").alias("sponsor_entity_person_id"),
        F.col("entity_person_id").alias("sponsored_entity_person_id"),
        F.col("relation_to_sponsor"),
        F.col("relationship_code"),
        F.col("sponsor_type"),
        F.lit("echannels_residency").alias("source"),
        F.lit(1.0).alias("confidence")
    ).dropDuplicates()
    
    # Create family groups
    family_groups = residents_entity.join(
        all_sponsors,
        residents_entity.sponsor_number == all_sponsors.sponsor_spm,
        "left"
    ).filter("sponsor_entity_id IS NOT NULL").select(
        F.col("entity_person_id"),
        F.col("sponsor_entity_id").alias("sponsor_id"),
        F.col("sponsor_number"),
        F.concat(F.lit("SPON:"), F.col("sponsor_number")).alias("family_group_id"),
        F.lit("sponsorship").alias("source")
    ).dropDuplicates()
    
    print(f"✓ Writing {sponsorship_links.count()} sponsorship links")
    sponsorship_links.write.mode("overwrite").format("iceberg").saveAsTable("lake.silver.residents_sponsorship_links")
    
    print(f"✓ Writing {family_groups.count()} family groups")
    family_groups.write.mode("overwrite").format("iceberg").saveAsTable("lake.silver.residents_family_groups")
    
    print("✓ RESIDENTS LINK BUILDER COMPLETE")
    spark.stop()

if __name__ == "__main__":
    main()
