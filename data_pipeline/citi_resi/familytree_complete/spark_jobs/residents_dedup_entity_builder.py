"""
Residents Deduplication - Based on echannels_residency_requests
"""
from pyspark.sql import SparkSession, Window
from pyspark.sql import functions as F
from pyspark.sql.types import StringType
import hashlib

def main():
    spark = SparkSession.builder.appName("residents_dedup_entity_builder").getOrCreate()
    
    print("RESIDENTS DEDUPLICATION")
    
    # Execute the residents query
    residents_query = """
    SELECT
        A.SPONSOR_NUMBER,
        RT.SPM_PERSON_NO AS SPM_PERSON_NO,
        A.ID,
        A.ENGLISH_FULL_NAME,
        A.ARABIC_FULL_NAME,
        A.DATE_OF_BIRTH,
        A.PASSPORT_NUMBER,
        A.PASSPORT_ISSUE_DATE,
        A.PASSPORT_EXPIRE_DATE,
        A.LOCAL_MOBILE_NUMBER,
        A.EMAIL_ADDRESS,
        A.PERSON_UNIFIED_NUMBER,
        A.LOOKUP_CURR_NATIONALITY_ID,
        A.LOOKUP_GENDER_ID,
        A.LOOKUP_FAMILY_RELATIONSHIP_ID,
        C.LOCALIZED_VALUE AS PERSON_TO_SPONSOR_RELATION,
        RT.RTR_CREATE_DATE,
        RT.RMA_SEQNO,
        RT.RMA_YEAR,
        A.CREATION_DATE
    FROM xpin.echannels_residency_requests A
    LEFT JOIN UDB_ECHANNELS.LOOKUP_FAMILY_RELATIONSHIPS B
        ON CAST(A.LOOKUP_FAMILY_RELATIONSHIP_ID AS INT) = CAST(B.ID AS INT)
    LEFT JOIN UDB_ECHANNELS.VALUE_LANGUAGES C
        ON B.NAME_ID = C.VALUE_LANGUAGE_GROUP_ID AND C.LOOKUP_LANGUAGE_ID = 2
    INNER JOIN xpin.ECHANNELS_REQUEST_MASTER RM
        ON A.ID = RM.ID AND RM.LOOKUP_LAST_ACTION_ID = 6
    INNER JOIN xpin.ECHANNELS_REQUEST_APPLICATIONS RA
        ON RM.ID = RA.REQUEST_ID
    INNER JOIN xpin.RESI_TRANS RT
        ON RA.UDB_TRANSACTION_NO = RT.RTR_NO 
        AND RA.UDB_TRANSACTION_YEAR = RT.RTR_YEAR
    WHERE RM.LOOKUP_LAST_ACTION_ID = 6
        AND A.LOOKUP_FAMILY_RELATIONSHIP_ID IN ('2', '3', '4')
        AND RA.LOOKUP_MODULE_ID = 1
    """
    
    residents_raw = spark.sql(residents_query)
    
    # Normalization
    normalized = residents_raw \
        .withColumn("passport_norm", F.upper(F.regexp_replace(F.col("passport_number"), r"[\s\-]+", ""))) \
        .withColumn("dob_norm", F.to_date(F.col("date_of_birth"))) \
        .withColumn("name_norm", F.lower(F.trim(F.col("english_full_name"))))
    
    # Clustering rules
    rule1 = F.when(
        F.col("spm_person_no").isNotNull(),
        F.concat_ws("|", F.lit("SPM"), F.col("spm_person_no"))
    )
    
    rule2 = F.when(
        (F.col("passport_norm").isNotNull()) & (F.col("dob_norm").isNotNull()),
        F.concat_ws("|", F.lit("PASS"), F.col("passport_norm"), F.col("dob_norm"))
    )
    
    fallback = F.concat_ws("|", F.lit("REQ"), F.col("id"), F.col("sponsor_number"))
    
    clustered = normalized.withColumn("cluster_key", F.coalesce(rule1, rule2, fallback))
    
    @F.udf(returnType=StringType())
    def generate_resident_id(cluster_key):
        if cluster_key:
            hash_value = hashlib.sha256(cluster_key.encode('utf-8')).hexdigest()
            return f"R:{hash_value}"
        return None
    
    entities = clustered.withColumn("entity_person_id", generate_resident_id(F.col("cluster_key")))
    
    # Select best record per entity (most complete, most recent)
    window = Window.partitionBy("entity_person_id").orderBy(
        F.coalesce(F.col("rtr_create_date"), F.col("creation_date")).desc_nulls_last()
    )
    
    best_records = entities \
        .withColumn("rank", F.row_number().over(window)) \
        .filter(F.col("rank") == 1) \
        .drop("rank")
    
    # Create person_entity table
    person_entity = best_records.select(
        F.col("entity_person_id"),
        F.col("spm_person_no").alias("primary_spm_person_no"),
        F.col("arabic_full_name").alias("full_name_ar"),
        F.col("english_full_name").alias("full_name_en"),
        F.coalesce(F.col("english_full_name"), F.col("arabic_full_name")).alias("full_name"),
        F.when(F.col("lookup_gender_id") == 1, "M")
         .when(F.col("lookup_gender_id") == 2, "F")
         .otherwise(None).alias("sex"),
        F.col("date_of_birth").alias("dob"),
        F.col("passport_number").alias("passport"),
        F.col("local_mobile_number").alias("mobile"),
        F.col("email_address").alias("email"),
        F.col("lookup_curr_nationality_id").alias("nationality_code"),
        F.col("sponsor_number"),
        F.col("person_to_sponsor_relation").alias("relation_to_sponsor"),
        F.col("lookup_family_relationship_id").alias("relationship_code"),
        F.col("rma_seqno").alias("residency_seq"),
        F.col("rma_year").alias("residency_year"),
        F.coalesce(F.col("rtr_create_date"), F.col("creation_date")).alias("updated_at"),
        F.lit("resident").alias("person_type")
    )
    
    # Create person_alias
    person_alias = entities \
        .filter(F.col("spm_person_no").isNotNull()) \
        .select("entity_person_id", "spm_person_no", "cluster_key") \
        .withColumn("confidence", F.when(F.col("cluster_key").startsWith("SPM|"), 1.0).otherwise(0.9)) \
        .withColumn("source", F.lit("echannels_residency_requests")) \
        .drop("cluster_key") \
        .dropDuplicates(["spm_person_no"])
    
    print(f"✓ Writing {person_entity.count()} resident entities")
    person_entity.write.mode("overwrite").format("iceberg").saveAsTable("lake.silver.residents_person_entity")
    
    print(f"✓ Writing {person_alias.count()} resident aliases")
    person_alias.write.mode("overwrite").format("iceberg").saveAsTable("lake.silver.residents_person_alias")
    
    print("✓ RESIDENTS DEDUPLICATION COMPLETE")
    spark.stop()

if __name__ == "__main__":
    main()
