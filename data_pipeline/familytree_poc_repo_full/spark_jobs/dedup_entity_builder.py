from pyspark.sql import SparkSession, functions as F, types as T
from pyspark.sql.window import Window
import hashlib

def completeness_score(cols):
    return sum(F.when(F.col(c).isNotNull(), F.lit(1)).otherwise(F.lit(0)) for c in cols)

spark = SparkSession.builder.appName("dedup_entity_builder").getOrCreate()

pm = spark.table("lake.bronze.person_master")

norm = (pm
    .withColumn("name_norm", F.lower(F.col("full_name")))
    .withColumn("dob_norm", F.to_date("dob"))
    .withColumn("national_id_norm", F.regexp_replace(F.col("national_id"), r"\s+", ""))
    .withColumn("passport_norm", F.upper(F.col("passport")))
    .withColumn("mobile_norm", F.regexp_replace(F.col("mobile"), r"\D+", ""))
    .withColumn("email_norm", F.lower(F.col("email")))
)

rule1_key = F.when(F.col("national_id_norm").isNotNull(),
                   F.concat_ws("|", F.lit("NID"), F.col("national_id_norm"), F.col("name_norm"), F.col("dob_norm"))
                  ).otherwise(
                   F.when(F.col("passport_norm").isNotNull(),
                          F.concat_ws("|", F.lit("PASS"), F.col("passport_norm"), F.col("name_norm"), F.col("dob_norm"))
                         )
                  )

norm = norm.withColumn("rule1_key", rule1_key)
norm = norm.withColumn("anchor_key", F.col("spm_person_no"))
norm = norm.withColumn("cluster_key", F.coalesce("rule1_key","anchor_key"))

udf_hex = F.udf(lambda s: hashlib.sha1((s or '').encode("utf-8")).hexdigest(), T.StringType())
entities = norm.withColumn("entity_person_id", udf_hex(F.col("cluster_key")))

value_cols = ["full_name","sex","dob","national_id","passport","mobile","email","spm_person_no","updated_at"]
scored = entities.withColumn("completeness", completeness_score(value_cols))

win = Window.partitionBy("entity_person_id").orderBy(F.col("completeness").desc(), F.col("updated_at").desc_nulls_last())
best = (scored.withColumn("rn", F.row_number().over(win)).filter("rn = 1").drop("rn"))

person_entity = (best
    .select("entity_person_id","spm_person_no","full_name","sex","dob","national_id","passport","mobile","email","updated_at","completeness")
    .withColumnRenamed("spm_person_no","primary_spm_person_no")
)

person_alias = (entities
    .select("entity_person_id","spm_person_no")
    .withColumn("confidence", F.when(F.col("cluster_key") != F.col("spm_person_no"), F.lit(0.8)).otherwise(F.lit(1.0)))
    .dropDuplicates()
)

spark.sql("CREATE SCHEMA IF NOT EXISTS lake.silver")
person_entity.write.mode("overwrite").saveAsTable("lake.silver.person_entity")
person_alias.write.mode("overwrite").saveAsTable("lake.silver.person_alias")
