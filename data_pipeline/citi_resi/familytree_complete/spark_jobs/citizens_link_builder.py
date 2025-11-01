"""
Citizens Link Builder
Creates parent-child and spouse relationships
"""
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

def main():
    spark = SparkSession.builder \
        .appName("citizens_link_builder") \
        .getOrCreate()
    
    print("=" * 80)
    print("CITIZENS LINK BUILDER")
    print("=" * 80)
    
    # Load tables
    crd = spark.table("lake.bronze.citi_record_detail")
    crm = spark.table("lake.bronze.citi_record_master").select("crm_seq", "spm_person_no")
    aliases = spark.table("lake.silver.citizens_person_alias")
    
    print(f"✓ Loaded {crd.count():,} records from citi_record_detail")
    print(f"✓ Loaded {crm.count():,} records from citi_record_master")
    print(f"✓ Loaded {aliases.count():,} person aliases")
    
    # ==================== PARENT LINKS ====================
    print("\nBuilding parent-child relationships...")
    
    # Map child spm_person_no to entity_person_id
    child_with_eid = crd.join(
        aliases.withColumnRenamed("spm_person_no", "child_spm")
               .withColumnRenamed("entity_person_id", "child_eid"),
        crd.spm_person_no == F.col("child_spm"),
        "left"
    ).select(crd["*"], F.col("child_eid"))
    
    # Map father spm_person_no to entity_person_id
    with_father = child_with_eid.join(
        aliases.withColumnRenamed("spm_person_no", "father_spm")
               .withColumnRenamed("entity_person_id", "father_eid"),
        child_with_eid.spm_person_no_father == F.col("father_spm"),
        "left"
    ).select(child_with_eid["*"], F.col("father_eid"))
    
    # Map mother spm_person_no to entity_person_id
    with_both_parents = with_father.join(
        aliases.withColumnRenamed("spm_person_no", "mother_spm")
               .withColumnRenamed("entity_person_id", "mother_eid"),
        with_father.spm_person_no_mother == F.col("mother_spm"),
        "left"
    ).select(with_father["*"], F.col("mother_eid"))
    
    # Create parent links
    father_links = with_both_parents \
        .filter("father_eid IS NOT NULL AND child_eid IS NOT NULL") \
        .select(
            F.col("father_eid").alias("parent_entity_person_id"),
            F.col("child_eid").alias("child_entity_person_id"),
            F.lit("father").alias("parent_type"),
            F.lit("crd_father").alias("source"),
            F.lit(1.0).alias("confidence")
        ).dropDuplicates()
    
    mother_links = with_both_parents \
        .filter("mother_eid IS NOT NULL AND child_eid IS NOT NULL") \
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
    
    # Map family head (crm_seq -> spm_person_no -> entity_person_id)
    head_with_eid = crm.join(
        aliases,
        crm.spm_person_no == aliases.spm_person_no,
        "left"
    ).select(
        F.col("crm_seq"),
        F.col("entity_person_id").alias("head_eid")
    )
    
    # Get wives (rel1_code = 2)
    wives = with_both_parents \
        .filter("rel1_code = 2") \
        .select(
            F.col("crm_seq"),
            F.col("child_eid").alias("wife_eid")
        ).dropDuplicates()
    
    # Create husband-wife links
    spouse_links = wives.join(
        head_with_eid,
        "crm_seq",
        "left"
    ).filter(
        "wife_eid IS NOT NULL AND head_eid IS NOT NULL AND wife_eid != head_eid"
    ).select(
        F.col("head_eid").alias("husband_entity_person_id"),
        F.col("wife_eid").alias("wife_entity_person_id"),
        F.lit("rel1_code=2").alias("source"),
        F.lit(0.9).alias("confidence")
    ).dropDuplicates()
    
    # ==================== FAMILY MEMBERSHIP ====================
    print("Building family membership...")
    
    family_membership = with_both_parents \
        .filter("child_eid IS NOT NULL AND crm_seq IS NOT NULL") \
        .select(
            F.col("child_eid").alias("entity_person_id"),
            F.col("crm_seq"),
            F.concat(F.lit("FAM:"), F.col("crm_seq")).alias("family_book_id"),
            F.lit("crd").alias("source")
        ).dropDuplicates()
    
    # Add family heads
    family_membership = family_membership.union(
        head_with_eid
        .filter("head_eid IS NOT NULL AND crm_seq IS NOT NULL")
        .select(
            F.col("head_eid").alias("entity_person_id"),
            F.col("crm_seq"),
            F.concat(F.lit("FAM:"), F.col("crm_seq")).alias("family_book_id"),
            F.lit("crm").alias("source")
        )
    ).dropDuplicates(["entity_person_id", "crm_seq"])
    
    # Write to silver layer
    print(f"\n✓ Writing {parent_links.count():,} parent links")
    parent_links.write \
        .mode("overwrite") \
        .format("iceberg") \
        .saveAsTable("lake.silver.citizens_parent_links")
    
    print(f"✓ Writing {spouse_links.count():,} spouse links")
    spouse_links.write \
        .mode("overwrite") \
        .format("iceberg") \
        .saveAsTable("lake.silver.citizens_spouse_links")
    
    print(f"✓ Writing {family_membership.count():,} family memberships")
    family_membership.write \
        .mode("overwrite") \
        .format("iceberg") \
        .saveAsTable("lake.silver.citizens_family_membership")
    
    print("\n" + "=" * 80)
    print("✓ CITIZENS LINK BUILDER COMPLETE")
    print("=" * 80)
    
    spark.stop()

if __name__ == "__main__":
    main()
