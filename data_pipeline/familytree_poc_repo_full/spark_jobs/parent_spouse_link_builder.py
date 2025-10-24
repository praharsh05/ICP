from pyspark.sql import SparkSession, functions as F

spark = SparkSession.builder.appName("parent_spouse_link_builder").getOrCreate()

crd = spark.table("lake.bronze.citi_record_detail")
aliases = spark.table("lake.silver.person_alias")
crm = spark.table("lake.bronze.citi_record_master").select("crm_seq","spm_person_no")

# child mapping
child = crd.join(aliases.withColumnRenamed("spm_person_no","child_spm"), crd.spm_person_no == F.col("child_spm"), "left") \           .select(crd["*"], F.col("entity_person_id").alias("child_eid"))

father = aliases.withColumnRenamed("spm_person_no","father_spm").withColumnRenamed("entity_person_id","father_eid")
mother = aliases.withColumnRenamed("spm_person_no","mother_spm").withColumnRenamed("entity_person_id","mother_eid")

child = child.join(father, child.spm_person_no_father == father.father_spm, "left") \             .join(mother, child.spm_person_no_mother == mother.mother_spm, "left")

parent_links = (
    child.select(F.col("father_eid").alias("parent_entity_person_id"),
                 F.col("child_eid").alias("child_entity_person_id"))
         .where("parent_entity_person_id IS NOT NULL AND child_entity_person_id IS NOT NULL")
         .withColumn("source", F.lit("crd_father"))
         .withColumn("confidence", F.lit(1.0))
    .unionByName(
        child.select(F.col("mother_eid").alias("parent_entity_person_id"),
                     F.col("child_eid").alias("child_entity_person_id"))
             .where("parent_entity_person_id IS NOT NULL AND child_entity_person_id IS NOT NULL")
             .withColumn("source", F.lit("crd_mother"))
             .withColumn("confidence", F.lit(1.0))
    ).dropDuplicates()
)

# Family membership
family_membership = (
    child.select(F.col("child_eid").alias("entity_person_id"), "crm_seq")
         .where("entity_person_id IS NOT NULL AND crm_seq IS NOT NULL")
         .withColumn("source", F.lit("crd"))
         .dropDuplicates()
)

# Head mapping for heuristic husband selection
head_eid = (crm.join(aliases, "spm_person_no", "left")
              .select("crm_seq", F.col("entity_person_id").alias("head_eid"))
)

wives = (child.filter("rel1_code = 2")
              .select("crm_seq", F.col("child_eid").alias("wife_eid"))
              .dropDuplicates()
)

spouse_links = (wives.join(head_eid, "crm_seq", "left")
                     .withColumn("husband_eid", F.col("head_eid"))
                     .where("wife_eid IS NOT NULL AND husband_eid IS NOT NULL")
                     .select(F.col("husband_eid").alias("husband_entity_person_id"),
                             F.col("wife_eid").alias("wife_entity_person_id"))
                     .withColumn("source", F.lit("rel1_code=2"))
                     .withColumn("confidence", F.lit(0.8))
                     .dropDuplicates()
)

spark.sql("CREATE SCHEMA IF NOT EXISTS lake.silver")
parent_links.write.mode("overwrite").saveAsTable("lake.silver.parent_links")
spouse_links.write.mode("overwrite").saveAsTable("lake.silver.spouse_links")
family_membership.write.mode("overwrite").saveAsTable("lake.silver.family_membership")
