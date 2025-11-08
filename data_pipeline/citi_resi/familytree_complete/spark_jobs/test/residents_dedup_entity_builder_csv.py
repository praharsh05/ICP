# """
# Residents Deduplication - Based on echannels_residency_requests
# CSV-based version - Reading from new_data folder
# """
# from pyspark.sql import SparkSession, Window
# from pyspark.sql import functions as F
# from pyspark.sql.types import StringType
# import hashlib


# # ── CONFIG: edit these paths only ──────────────────────────────────────────────
# ERR_PATH   = "./new_data_sc_map/echannels_residency_requests.csv"         # e.g. "./person_master.csv" or "./person_master/*.csv"
# FR_PATH   = "./new_data_sc_map/LOOKUP_FAMILY_RELATIONSHIPS.csv"
# VL_PATH   = "./new_data_sc_map/VALUE_LANGUAGES.csv"
# ERM_PATH   = "./new_data_sc_map/ECHANNELS_REQUEST_MASTER.csv"
# ERA_PATH   = "./new_data_sc_map/ECHANNELS_REQUEST_APPLICATIONS.csv"
# RT_PATH   = "./new_data_sc_map/RESI_TRANS.csv"
# OUTPUT_DIR   = "./new_data_sc_map/output"                       # local folder for outputs
# DELIMITER    = ","                           # CSV delimiter
# HAS_HEADER   = True                          # set False if no header in source CSV
# INFER_SCHEMA = True                          # set False to read all columns as strings
# SINGLE_FILE  = True                          # True = one CSV per table (coalesce to 1)
# # ──────────────────────────────────────────────────────────────────────────────



# def main():
#     spark = SparkSession.builder \
#         .appName("residents_dedup_entity_builder") \
#         .config("spark.sql.legacy.timeParserPolicy", "LEGACY") \
#         .getOrCreate()
    
#     print("RESIDENTS DEDUPLICATION - CSV VERSION (new_data)")
    
#     # Read CSV files from new_data folder
#     print("Reading CSV files from /jobs/data/new_data/...")

#     # residents = spark.read.csv(
#     #     "/jobs/data/new_data/echannels_residency_requests.csv",
#     #     header=True,
#     #     inferSchema=True
#     # )

#     residents = spark.read \
#         .option("header", str(HAS_HEADER).lower()) \
#         .option("inferSchema", str(INFER_SCHEMA).lower()) \
#         .option("sep", DELIMITER) \
#         .option("mode", "PERMISSIVE") \
#         .option("multiLine", "true") \
#         .option("quote", '"') \
#         .option("escape", '"') \
#         .csv(ERR_PATH)

#     # family_relationships = spark.read.csv(
#     #     "/jobs/data/new_data/LOOKUP_FAMILY_RELATIONSHIPS.csv",
#     #     header=True,
#     #     inferSchema=True
#     # )

#     family_relationships = spark.read \
#         .option("header", str(HAS_HEADER).lower()) \
#         .option("inferSchema", str(INFER_SCHEMA).lower()) \
#         .option("sep", DELIMITER) \
#         .option("mode", "PERMISSIVE") \
#         .option("multiLine", "true") \
#         .option("quote", '"') \
#         .option("escape", '"') \
#         .csv(FR_PATH)

#     # value_languages = spark.read.csv(
#     #     "/jobs/data/new_data/VALUE_LANGUAGES.csv",
#     #     header=True,
#     #     inferSchema=True
#     # )

#     value_languages = spark.read \
#         .option("header", str(HAS_HEADER).lower()) \
#         .option("inferSchema", str(INFER_SCHEMA).lower()) \
#         .option("sep", DELIMITER) \
#         .option("mode", "PERMISSIVE") \
#         .option("multiLine", "true") \
#         .option("quote", '"') \
#         .option("escape", '"') \
#         .csv(VL_PATH)

#     # request_master = spark.read.csv(
#     #     "/jobs/data/new_data/ECHANNELS_REQUEST_MASTER.csv",
#     #     header=True,
#     #     inferSchema=True
#     # )

#     request_master = spark.read \
#         .option("header", str(HAS_HEADER).lower()) \
#         .option("inferSchema", str(INFER_SCHEMA).lower()) \
#         .option("sep", DELIMITER) \
#         .option("mode", "PERMISSIVE") \
#         .option("multiLine", "true") \
#         .option("quote", '"') \
#         .option("escape", '"') \
#         .csv(ERM_PATH)

#     # request_applications = spark.read.csv(
#     #     "/jobs/data/new_data/ECHANNELS_REQUEST_APPLICATIONS.csv",
#     #     header=True,
#     #     inferSchema=True
#     # )

#     request_applications = spark.read \
#         .option("header", str(HAS_HEADER).lower()) \
#         .option("inferSchema", str(INFER_SCHEMA).lower()) \
#         .option("sep", DELIMITER) \
#         .option("mode", "PERMISSIVE") \
#         .option("multiLine", "true") \
#         .option("quote", '"') \
#         .option("escape", '"') \
#         .csv(ERA_PATH)

#     # resi_trans = spark.read.csv(
#     #     "/jobs/data/new_data/RESI_TRANS.csv",
#     #     header=True,
#     #     inferSchema=True
#     # )

#     resi_trans = spark.read \
#         .option("header", str(HAS_HEADER).lower()) \
#         .option("inferSchema", str(INFER_SCHEMA).lower()) \
#         .option("sep", DELIMITER) \
#         .option("mode", "PERMISSIVE") \
#         .option("multiLine", "true") \
#         .option("quote", '"') \
#         .option("escape", '"') \
#         .csv(RT_PATH)
    
#     print("✓ All CSV files loaded from new_data folder")
    
#     # Register as temporary views for SQL queries
#     residents.createOrReplaceTempView("echannels_residency_requests")
#     family_relationships.createOrReplaceTempView("LOOKUP_FAMILY_RELATIONSHIPS")
#     value_languages.createOrReplaceTempView("VALUE_LANGUAGES")
#     request_master.createOrReplaceTempView("ECHANNELS_REQUEST_MASTER")
#     request_applications.createOrReplaceTempView("ECHANNELS_REQUEST_APPLICATIONS")
#     resi_trans.createOrReplaceTempView("RESI_TRANS")
    
#     # Execute the residents query
#     residents_query = """
#     SELECT
#         A.SPONSOR_NUMBER,
#         RT.SPM_PERSON_NO AS SPM_PERSON_NO,
#         A.ID,
#         A.ENGLISH_FULL_NAME,
#         A.ARABIC_FULL_NAME,
#         A.DATE_OF_BIRTH,
#         A.PASSPORT_NUMBER,
#         A.PASSPORT_ISSUE_DATE,
#         A.PASSPORT_EXPIRE_DATE,
#         A.LOCAL_MOBILE_NUMBER,
#         A.EMAIL_ADDRESS,
#         A.PERSON_UNIFIED_NUMBER,
#         A.LOOKUP_CURR_NATIONALITY_ID,
#         A.LOOKUP_GENDER_ID,
#         A.LOOKUP_FAMILY_RELATIONSHIP_ID,
#         C.LOCALIZED_VALUE AS PERSON_TO_SPONSOR_RELATION,
#         RT.RTR_CREATE_DATE,
#         RT.RMA_SEQNO,
#         RT.RMA_YEAR,
#         A.CREATION_DATE
#     FROM echannels_residency_requests A
#     LEFT JOIN LOOKUP_FAMILY_RELATIONSHIPS B
#         ON CAST(A.LOOKUP_FAMILY_RELATIONSHIP_ID AS INT) = CAST(B.ID AS INT)
#     LEFT JOIN VALUE_LANGUAGES C
#         ON B.NAME_ID = C.VALUE_LANGUAGE_GROUP_ID AND C.LOOKUP_LANGUAGE_ID = 2
#     INNER JOIN ECHANNELS_REQUEST_MASTER RM
#         ON A.ID = RM.ID AND RM.LOOKUP_LAST_ACTION_ID = 6
#     INNER JOIN ECHANNELS_REQUEST_APPLICATIONS RA
#         ON RM.ID = RA.REQUEST_ID
#     INNER JOIN RESI_TRANS RT
#         ON RA.UDB_TRANSACTION_NO = RT.RTR_NO 
#         AND RA.UDB_TRANSACTION_YEAR = RT.RTR_YEAR
#     WHERE RM.LOOKUP_LAST_ACTION_ID = 6
#         AND A.LOOKUP_FAMILY_RELATIONSHIP_ID IN ('2', '3', '4')
#         AND RA.LOOKUP_MODULE_ID = 1
#     """
    
#     residents_raw = spark.sql(residents_query)
#     print(f"✓ Query executed: {residents_raw.count()} records found")
    
#     # Normalization
#     normalized = residents_raw \
#         .withColumn("passport_norm", F.upper(F.regexp_replace(F.col("PASSPORT_NUMBER"), r"[\s\-]+", ""))) \
#         .withColumn("dob_norm", F.to_date(F.col("DATE_OF_BIRTH"))) \
#         .withColumn("name_norm", F.lower(F.trim(F.col("ENGLISH_FULL_NAME"))))
    
#     # Clustering rules
#     rule1 = F.when(
#         F.col("SPM_PERSON_NO").isNotNull(),
#         F.concat_ws("|", F.lit("SPM"), F.col("SPM_PERSON_NO"))
#     )
    
#     rule2 = F.when(
#         (F.col("passport_norm").isNotNull()) & (F.col("dob_norm").isNotNull()),
#         F.concat_ws("|", F.lit("PASS"), F.col("passport_norm"), F.col("dob_norm"))
#     )
    
#     fallback = F.concat_ws("|", F.lit("REQ"), F.col("ID"), F.col("SPONSOR_NUMBER"))
    
#     clustered = normalized.withColumn("cluster_key", F.coalesce(rule1, rule2, fallback))
    
#     @F.udf(returnType=StringType())
#     def generate_resident_id(cluster_key):
#         if cluster_key:
#             hash_value = hashlib.sha256(cluster_key.encode('utf-8')).hexdigest()
#             return f"R:{hash_value}"
#         return None
    
#     entities = clustered.withColumn("entity_person_id", generate_resident_id(F.col("cluster_key")))
    
#     # Select best record per entity (most complete, most recent)
#     window = Window.partitionBy("entity_person_id").orderBy(
#         F.coalesce(F.col("RTR_CREATE_DATE"), F.col("CREATION_DATE")).desc_nulls_last()
#     )
    
#     best_records = entities \
#         .withColumn("rank", F.row_number().over(window)) \
#         .filter(F.col("rank") == 1) \
#         .drop("rank")
    
#     # Create person_entity table
#     person_entity = best_records.select(
#         F.col("entity_person_id"),
#         F.col("SPM_PERSON_NO").alias("primary_spm_person_no"),
#         F.col("ARABIC_FULL_NAME").alias("full_name_ar"),
#         F.col("ENGLISH_FULL_NAME").alias("full_name_en"),
#         F.coalesce(F.col("ENGLISH_FULL_NAME"), F.col("ARABIC_FULL_NAME")).alias("full_name"),
#         F.when(F.col("LOOKUP_GENDER_ID") == 1, "M")
#          .when(F.col("LOOKUP_GENDER_ID") == 2, "F")
#          .otherwise(None).alias("sex"),
#         F.col("DATE_OF_BIRTH").alias("dob"),
#         F.col("PASSPORT_NUMBER").alias("passport"),
#         F.col("LOCAL_MOBILE_NUMBER").alias("mobile"),
#         F.col("EMAIL_ADDRESS").alias("email"),
#         F.col("LOOKUP_CURR_NATIONALITY_ID").alias("nationality_code"),
#         F.col("SPONSOR_NUMBER").alias("sponsor_number"),
#         F.col("PERSON_TO_SPONSOR_RELATION").alias("relation_to_sponsor"),
#         F.col("LOOKUP_FAMILY_RELATIONSHIP_ID").alias("relationship_code"),
#         F.col("RMA_SEQNO").alias("residency_seq"),
#         F.col("RMA_YEAR").alias("residency_year"),
#         F.coalesce(F.col("RTR_CREATE_DATE"), F.col("CREATION_DATE")).alias("updated_at"),
#         F.lit("resident").alias("person_type")
#     )
    
#     # Create person_alias
#     person_alias = entities \
#         .filter(F.col("SPM_PERSON_NO").isNotNull()) \
#         .select("entity_person_id", "SPM_PERSON_NO", "cluster_key") \
#         .withColumn("confidence", F.when(F.col("cluster_key").startswith("SPM|"), 1.0).otherwise(0.9)) \
#         .withColumn("source", F.lit("echannels_residency_requests")) \
#         .drop("cluster_key") \
#         .dropDuplicates(["SPM_PERSON_NO"])
    

#     # ── Write outputs as local CSVs ──────────────────────────────────────────────
#     out_entity = f"{OUTPUT_DIR.rstrip('/')}/residents_person_entity"
#     out_alias  = f"{OUTPUT_DIR.rstrip('/')}/residents_person_alias"
    
#     # Write to CSV files
#     print(f"✓ Writing {person_entity.count()} resident entities to CSV")
#     person_entity.coalesce(1).write \
#         .mode("overwrite") \
#         .option("header", "true") \
#         .csv(out_entity)
    
#     print(f"✓ Writing {person_alias.count()} resident aliases to CSV")
#     person_alias.coalesce(1).write \
#         .mode("overwrite") \
#         .option("header", "true") \
#         .csv(out_alias)
    
#     print("✓ RESIDENTS DEDUPLICATION COMPLETE")
#     print("Output files saved in:")
#     print("  - /jobs/output/residents_person_entity/")
#     print("  - /jobs/output/residents_person_alias/")
    
#     spark.stop()


# if __name__ == "__main__":
#     main()


"""
Residents Deduplication - Enhanced Version
Includes all attributes needed for Neo4j relationships
Based on echannels_residency_requests with full attribute extraction
"""
from pyspark.sql import SparkSession, Window
from pyspark.sql import functions as F
from pyspark.sql.types import StringType
import hashlib


# ── CONFIG ─────────────────────────────────────────────────────────────────────
ERR_PATH   = "./new_data_sc_map/echannels_residency_requests_v2.csv"
FR_PATH    = "./new_data_sc_map/LOOKUP_FAMILY_RELATIONSHIPS.csv"
VL_PATH    = "./new_data_sc_map/VALUE_LANGUAGES.csv"
ERM_PATH   = "./new_data_sc_map/echannels_request_master_v2.csv"
ERA_PATH   = "./new_data_sc_map/echannels_request_applications_v2.csv"
RT_PATH    = "./new_data_sc_map/resi_trans_v2.csv"
OUTPUT_DIR = "./new_data_sc_map/output/residents_v2"
DELIMITER  = ","
HAS_HEADER = True
INFER_SCHEMA = True
# ───────────────────────────────────────────────────────────────────────────────


def main():
    spark = SparkSession.builder \
        .appName("residents_dedup_entity_builder_enhanced") \
        .config("spark.sql.legacy.timeParserPolicy", "LEGACY") \
        .getOrCreate()
    
    print("=" * 80)
    print("RESIDENTS DEDUPLICATION - ENHANCED VERSION (with full attributes)")
    print("=" * 80)
    
    # Read CSV files
    print("Reading CSV files...")

    residents = spark.read \
        .option("header", str(HAS_HEADER).lower()) \
        .option("inferSchema", str(INFER_SCHEMA).lower()) \
        .option("sep", DELIMITER) \
        .option("mode", "PERMISSIVE") \
        .option("multiLine", "true") \
        .option("quote", '"') \
        .option("escape", '"') \
        .csv(ERR_PATH)

    family_relationships = spark.read \
        .option("header", str(HAS_HEADER).lower()) \
        .option("inferSchema", str(INFER_SCHEMA).lower()) \
        .option("sep", DELIMITER) \
        .option("mode", "PERMISSIVE") \
        .option("multiLine", "true") \
        .option("quote", '"') \
        .option("escape", '"') \
        .csv(FR_PATH)

    value_languages = spark.read \
        .option("header", str(HAS_HEADER).lower()) \
        .option("inferSchema", str(INFER_SCHEMA).lower()) \
        .option("sep", DELIMITER) \
        .option("mode", "PERMISSIVE") \
        .option("multiLine", "true") \
        .option("quote", '"') \
        .option("escape", '"') \
        .csv(VL_PATH)

    request_master = spark.read \
        .option("header", str(HAS_HEADER).lower()) \
        .option("inferSchema", str(INFER_SCHEMA).lower()) \
        .option("sep", DELIMITER) \
        .option("mode", "PERMISSIVE") \
        .option("multiLine", "true") \
        .option("quote", '"') \
        .option("escape", '"') \
        .csv(ERM_PATH)

    request_applications = spark.read \
        .option("header", str(HAS_HEADER).lower()) \
        .option("inferSchema", str(INFER_SCHEMA).lower()) \
        .option("sep", DELIMITER) \
        .option("mode", "PERMISSIVE") \
        .option("multiLine", "true") \
        .option("quote", '"') \
        .option("escape", '"') \
        .csv(ERA_PATH)

    resi_trans = spark.read \
        .option("header", str(HAS_HEADER).lower()) \
        .option("inferSchema", str(INFER_SCHEMA).lower()) \
        .option("sep", DELIMITER) \
        .option("mode", "PERMISSIVE") \
        .option("multiLine", "true") \
        .option("quote", '"') \
        .option("escape", '"') \
        .csv(RT_PATH)
    
    print("✓ All CSV files loaded")
    
    # Register as temporary views for SQL queries
    residents.createOrReplaceTempView("echannels_residency_requests")
    family_relationships.createOrReplaceTempView("LOOKUP_FAMILY_RELATIONSHIPS")
    value_languages.createOrReplaceTempView("VALUE_LANGUAGES")
    request_master.createOrReplaceTempView("ECHANNELS_REQUEST_MASTER")
    request_applications.createOrReplaceTempView("ECHANNELS_REQUEST_APPLICATIONS")
    resi_trans.createOrReplaceTempView("RESI_TRANS")
    
    # Execute the residents query with ALL attributes
    residents_query = """
    SELECT
        A.ID,
        A.SPM_PERSON_NO,
        A.SPONSOR_NUMBER,
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
        RT.SPM_PERSON_NO AS SPONSOR_SPM_PERSON_NO,
        RT.EST_ID,
        RT.RTR_CREATE_DATE,
        RT.RMA_SEQNO,
        RT.RMA_YEAR,
        A.CREATION_DATE
    FROM echannels_residency_requests A
    LEFT JOIN LOOKUP_FAMILY_RELATIONSHIPS B
        ON CAST(A.LOOKUP_FAMILY_RELATIONSHIP_ID AS INT) = CAST(B.ID AS INT)
    LEFT JOIN VALUE_LANGUAGES C
        ON B.NAME_ID = C.VALUE_LANGUAGE_GROUP_ID AND C.LOOKUP_LANGUAGE_ID = 2
    INNER JOIN ECHANNELS_REQUEST_MASTER RM
        ON A.ID = RM.ID AND RM.LOOKUP_LAST_ACTION_ID = 6
    INNER JOIN ECHANNELS_REQUEST_APPLICATIONS RA
        ON RM.ID = RA.REQUEST_ID
    INNER JOIN RESI_TRANS RT
        ON RA.UDB_TRANSACTION_NO = RT.RTR_NO 
        AND RA.UDB_TRANSACTION_YEAR = RT.RTR_YEAR
    WHERE RM.LOOKUP_LAST_ACTION_ID = 6
        AND RA.LOOKUP_MODULE_ID = 1
    """
    
    residents_raw = spark.sql(residents_query)
    print(f"✓ Query executed: {residents_raw.count()} records found")
    
    # Normalization
    normalized = residents_raw \
        .withColumn("passport_norm", F.upper(F.regexp_replace(F.col("PASSPORT_NUMBER"), r"[\s\-]+", ""))) \
        .withColumn("dob_norm", F.to_date(F.col("DATE_OF_BIRTH"))) \
        .withColumn("name_norm", F.lower(F.trim(F.col("ENGLISH_FULL_NAME"))))
    
    # Clustering rules
    rule1 = F.when(
        F.col("SPM_PERSON_NO").isNotNull(),
        F.concat_ws("|", F.lit("SPM"), F.col("SPM_PERSON_NO"))
    )
    
    rule2 = F.when(
        (F.col("passport_norm").isNotNull()) & (F.col("dob_norm").isNotNull()),
        F.concat_ws("|", F.lit("PASS"), F.col("passport_norm"), F.col("dob_norm"))
    )
    
    fallback = F.concat_ws("|", F.lit("REQ"), F.col("ID"), F.col("SPONSOR_NUMBER"))
    
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
        F.coalesce(F.col("RTR_CREATE_DATE"), F.col("CREATION_DATE")).desc_nulls_last()
    )
    
    best_records = entities \
        .withColumn("rank", F.row_number().over(window)) \
        .filter(F.col("rank") == 1) \
        .drop("rank")
    
    # Create person_entity table with ALL attributes for Neo4j
    person_entity = best_records.select(
        F.col("entity_person_id"),
        F.col("SPM_PERSON_NO").alias("primary_spm_person_no"),
        F.col("ARABIC_FULL_NAME").alias("full_name_ar"),
        F.col("ENGLISH_FULL_NAME").alias("full_name_en"),
        F.coalesce(F.col("ENGLISH_FULL_NAME"), F.col("ARABIC_FULL_NAME")).alias("full_name"),
        F.when(F.col("LOOKUP_GENDER_ID") == 1, "M")
         .when(F.col("LOOKUP_GENDER_ID") == 2, "F")
         .otherwise(None).alias("sex"),
        F.col("DATE_OF_BIRTH").alias("dob"),
        F.col("PASSPORT_NUMBER").alias("passport"),
        F.col("PASSPORT_ISSUE_DATE").alias("passport_issue_date"),
        F.col("PASSPORT_EXPIRE_DATE").alias("passport_expiry_date"),
        F.col("PERSON_UNIFIED_NUMBER").alias("unified_number"),
        F.col("LOCAL_MOBILE_NUMBER").alias("mobile"),
        F.col("EMAIL_ADDRESS").alias("email"),
        F.col("LOOKUP_CURR_NATIONALITY_ID").alias("nationality_code"),
        F.col("SPONSOR_NUMBER").alias("sponsor_number"),
        F.col("SPONSOR_SPM_PERSON_NO").alias("sponsor_spm_person_no"),
        F.col("EST_ID").alias("establishment_id"),
        F.col("PERSON_TO_SPONSOR_RELATION").alias("relation_to_sponsor"),
        F.col("LOOKUP_FAMILY_RELATIONSHIP_ID").alias("relationship_code"),
        F.col("RMA_SEQNO").alias("residency_seq"),
        F.col("RMA_YEAR").alias("residency_year"),
        F.coalesce(F.col("RTR_CREATE_DATE"), F.col("CREATION_DATE")).alias("updated_at"),
        F.lit("resident").alias("person_type")
    )
    
    # Create person_alias
    person_alias = entities \
        .filter(F.col("SPM_PERSON_NO").isNotNull()) \
        .select("entity_person_id", "SPM_PERSON_NO", "cluster_key") \
        .withColumn("confidence", F.when(F.col("cluster_key").startswith("SPM|"), 1.0).otherwise(0.9)) \
        .withColumn("source", F.lit("echannels_residency_requests")) \
        .drop("cluster_key") \
        .dropDuplicates(["SPM_PERSON_NO"])
    
    # Write outputs
    out_entity = f"{OUTPUT_DIR.rstrip('/')}/residents_person_entity"
    out_alias  = f"{OUTPUT_DIR.rstrip('/')}/residents_person_alias"
    
    print(f"\n✓ Writing {person_entity.count()} resident entities to CSV")
    person_entity.coalesce(1).write \
        .mode("overwrite") \
        .option("header", "true") \
        .csv(out_entity)
    
    print(f"✓ Writing {person_alias.count()} resident aliases to CSV")
    person_alias.coalesce(1).write \
        .mode("overwrite") \
        .option("header", "true") \
        .csv(out_alias)
    
    print("\n" + "=" * 80)
    print("✓ RESIDENTS DEDUPLICATION COMPLETE (Enhanced)")
    print("=" * 80)
    print("Output files saved in:")
    print("  - residents_person_entity/ (with full attributes)")
    print("  - residents_person_alias/")
    print("=" * 80)
    
    spark.stop()


if __name__ == "__main__":
    main()