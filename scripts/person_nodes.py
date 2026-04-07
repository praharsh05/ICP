from __future__ import annotations

# from pyspark.sql.functions import 
# from pyspark.sql.functions import to_date, col, to_timestamp, lit, current_timestamp
from pyspark.sql import functions as F
from pyspark.sql.functions import broadcast
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.window import Window
from typing import Union, List, Tuple, Optional
from datetime import datetime, timedelta, date
from typing import List as _List, Optional as _Optional
from typing import Any, Dict, List, Tuple
from pyspark.sql.types import *
import time
# Custom Dependencies
# TODO: this is added to help airflow detect common_utils as module
import sys
sys.path.append("/workflows/family_tree_data_pipeline/")
print("Sys Path:", sys.path)


from common_utils.scripts.common_utilities import CommonLogging, CommonIcebergUtilities
from common_utils.scripts.helper.common_helper_utilities import CommonBasicUtilities, CommonProcessHelperUtils
from common_utils.scripts.data.common_data_utilities import CommonDataUtilities
from common_utils.scripts.batch_calculator_utils import BatchCalculatorUtils

from common_utils.scripts.db_operations.db_operations_factory import DBOperationsFactory
from common_utils.scripts.db_operations.db_operations import BaseDBOperations

# Custom Data Quality Checker
from common_utils.scripts.data_quality import DataQualityChecker
from pyspark.sql.types import StringType, StructType, StructField

from decimal import Decimal

logging = CommonLogging.get_logger()

# ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** *****

MOUNT_BUCKET = '/workflows'

class Constants:
    DEFAULT_RECORDS_PER_BATCH = 1_00_000
    DEFAULT_NUMBER_OF_PARTITIONS = 1
    DEFAULT_IS_COL_FOR_PARTITION_NULL_SUPP=True

def extract_persons_from_both_sides(df):
        """
        Extract unique persons from both person_no and rltv_person_no

        Args:
            df: Source DataFrame (family_relations)

        Returns:
            DataFrame with deduplicated persons (spm_person_no, sex)
        """
        logging.info("Extracting persons from both sides of relationships")

        # Extract from person_no side
        persons_left = df.select(
            F.col("person_no").alias("spm_person_no"),
            F.col("spm_gender").alias("sex")
        ).distinct()

        # Extract from rltv_person_no side
        persons_right = df.select(
            F.col("rltv_person_no").alias("spm_person_no"),
            F.col("rltv_gender").alias("sex")
        ).distinct()

        # Union and deduplicate
        all_persons = persons_left.union(persons_right)

        # Deduplicate by taking first non-null gender
        persons_deduped = (
            all_persons
            .groupBy("spm_person_no")
            .agg(
                F.first(F.col("sex"), ignorenulls=True).alias("sex")
            )
        )

        logging.info("Persons extracted and deduplicated by spm_person_no")

        return persons_deduped


def dedup_hub_person_master(hub_df):
        """
        Deduplicate hub_person_master by keeping the latest record per spm_person_no

        Args:
            hub_df: hub_person_master DataFrame

        Returns:
            DataFrame with one row per spm_person_no containing person_master_hk
        """
        logging.info("Deduplicating hub_person_master by latest load_datetime")

        window = Window.partitionBy("spm_person_no").orderBy(F.desc("load_datetime"))

        hub_deduped = (
            hub_df
            .withColumn("row_num", F.row_number().over(window))
            .filter(F.col("row_num") == 1)
            .drop("row_num")
            .select("spm_person_no", "person_master_hk")
        )

        logging.info("Hub person master deduplicated by latest load_datetime")

        return hub_deduped


def enrich_from_person_master(persons_df, hub_deduped, pit_df):
        """
        Enrich persons with details from pit_person_master via hub hash key

        Args:
            persons_df: Persons DataFrame (spm_person_no, sex)
            hub_deduped: Deduped hub DataFrame (spm_person_no, person_master_hk)
            pit_df: pit_person_master DataFrame

        Returns:
            DataFrame enriched with full_name, spm_dob, nat_code_curr_nat
        """
        logging.info("Enriching persons from person master tables")

        # Join persons with hub to get person_master_hk (broadcast hub — small lookup table)
        persons_with_hk = persons_df.join(
            broadcast(hub_deduped),
            on="spm_person_no",
            how="left"
        )

        # Select only needed columns from pit
        pit_selected = pit_df.select(
            "person_master_hk",
            F.col("spm_full_ename").alias("full_name"),
            "spm_full_aname",
            "spm_dob",
            "nat_code_curr_nat",
            "spm_national_id"
        )

        # Join with pit to get person details
        persons_enriched = (
            persons_with_hk
            .join(pit_selected, on="person_master_hk", how="left")
            .drop("person_master_hk")
        )

        # Log join quality — single aggregation instead of two .count() calls
        stats = persons_enriched.select(
            F.count("*").alias("total"),
            F.sum(F.when(F.col("full_name").isNull(), 1).otherwise(0)).alias("missing_name")
        ).first()
        logging.info("="*80)
        logging.info(f"Persons after master join: {stats['total']:,}, missing name: {stats['missing_name']:,}")
        logging.info("="*80)

        return persons_enriched


def get_passport_numbers(persons_df, hub_ids_df, sat_ids_df):
        """
        Enrich persons with passport numbers from hub_person_ids and sat_person_ids

        Args:
            persons_df: Persons DataFrame
            hub_ids_df: hub_person_ids DataFrame (spm_person_no → person_ids_hk)
            sat_ids_df: sat_person_ids DataFrame (person_ids_hk → id_number)

        Returns:
            DataFrame with passport column added
        """
        logging.info("Enriching persons with passport numbers")

        # Select needed columns from hub (no dedup needed)
        hub_ids_selected = hub_ids_df.select("spm_person_no", "person_ids_hk")

        # Filter sat: exclude deleted records, select passport number
        sat_filtered = (
            sat_ids_df
            .filter(F.col("__op") != "d")
            .select("person_ids_hk", F.col("id_number").alias("passport"))
        )

        # Join persons → hub_person_ids → sat_person_ids
        # Broadcast hub_ids (small lookup). sat_filtered not broadcast — could be large.
        persons_with_passport = (
            persons_df
            .join(broadcast(hub_ids_selected), on="spm_person_no", how="left")
            .join(sat_filtered, on="person_ids_hk", how="left")
            .drop("person_ids_hk")
        )

        # Log join quality — single aggregation instead of two .count() calls
        stats = persons_with_passport.select(
            F.count("*").alias("total"),
            F.sum(F.when(F.col("passport").isNull(), 1).otherwise(0)).alias("missing")
        ).first()
        logging.info("="*80)
        logging.info(f"Persons with passport: {stats['total'] - stats['missing']:,}, missing passport: {stats['missing']:,}")
        logging.info("="*80)

        return persons_with_passport


def get_contact_numbers(persons_df, echannel_df):
        """
        Enrich persons with mobile numbers from pit_echannel_request_master.

        Join path: persons_df.spm_national_id = echannel.applicant_eida_number
        Filter: both sides must have non-null Emirates ID
        Dedup: latest record per EIDA number (by load_datetime desc)

        Args:
            persons_df: Persons DataFrame (must contain spm_national_id)
            echannel_df: pit_echannel_request_master DataFrame

        Returns:
            DataFrame with contact_no column added
        """
        logging.info("Enriching persons with contact numbers from echannel_request_master")

        # Filter echannel — only rows with non-null EIDA number
        echannel_filtered = echannel_df.filter(
            F.col("applicant_eida_number").isNotNull()
            & (F.trim(F.col("applicant_eida_number")) != "")
        )

        # Dedup — latest record per EIDA number
        w = Window.partitionBy("applicant_eida_number").orderBy(F.desc("load_datetime"))
        echannel_deduped = (
            echannel_filtered
            .withColumn("rn", F.row_number().over(w))
            .filter(F.col("rn") == 1)
            .drop("rn")
            .select(
                "applicant_eida_number",
                F.col("applicant_mobile").alias("contact_no")
            )
        )

        # Left join — persons with non-null national ID will match
        # Null spm_national_id won't match any EIDA (equi-join null semantics)
        persons_with_contact = (
            persons_df
            .join(
                echannel_deduped,
                on=(F.col("spm_national_id") == F.col("applicant_eida_number")),
                how="left"
            )
            .drop("applicant_eida_number")
        )

        # Log join quality — single aggregation (1 Spark action)
        stats = persons_with_contact.select(
            F.count("*").alias("total"),
            F.sum(F.when(F.col("contact_no").isNull(), 1).otherwise(0)).alias("missing")
        ).first()
        logging.info("=" * 80)
        logging.info(f"Persons with contact: {stats['total'] - stats['missing']:,}, missing: {stats['missing']:,}")
        logging.info("=" * 80)

        return persons_with_contact


def determine_person_type(df, source_df):
        """
        Determine if person is Citizen or Resident based on relation_source
        
        Logic:
        - If person appears in CITF relationships -> Citizen
        - If person appears in MAN_DEF relationships -> Resident (TODO: Add different logic later)
        - If person appears in SPONS relationships -> Resident
        - If person appears in SPON_DRIVED relationships -> Resident
        - Priority: CITF > MAN_DEF > SPONS > SPON_DRIVED
        
        Args:
            df: Persons DataFrame
            source_df: Original relationship data
            
        Returns:
            DataFrame with person_type column
        """
        logging.info("Determining person types (Citizen/Resident)")

        # Single-pass: extract all person-source mappings from both sides of relationships
        # Previously this scanned source_df 8 times (4 sources x 2 sides) and did 4 joins
        person_sources = (
            source_df.select(
                F.col("person_no").alias("spm_person_no"),
                F.col("relation_source")
            )
            .union(
                source_df.select(
                    F.col("rltv_person_no").alias("spm_person_no"),
                    F.col("relation_source")
                )
            )
            .withColumn(
                "priority",
                F.when(F.col("relation_source") == "CITF", 1)
                .when(F.col("relation_source") == "MAN_DEF", 2)
                .when(F.col("relation_source") == "SPONS", 3)
                .when(F.col("relation_source") == "SPON_DRIVED", 4)
                .otherwise(99)
            )
        )

        # Keep highest priority source per person using window function
        w = Window.partitionBy("spm_person_no").orderBy("priority")

        best_source = (
            person_sources
            .withColumn("rn", F.row_number().over(w))
            .filter(F.col("rn") == 1)
            .withColumn(
                "person_type",
                # CITF = citizen, everything else = resident
                # TODO: Add different classification logic for MAN_DEF in future iterations
                F.when(F.col("relation_source") == "CITF", "citizen")
                .otherwise("resident")
            )
            .select("spm_person_no", "person_type")
        )

        # Single join instead of 4
        df_with_type = (
            df.join(best_source, on="spm_person_no", how="left")
            .fillna("unknown", subset=["person_type"])
        )

        logging.info("Person types determined (Citizen/Resident)")

        return df_with_type


def enrich_person_attributes(df):
        """
        Add additional attributes to person nodes
        
        Args:
            df: Persons DataFrame
            
        Returns:
            Enriched DataFrame
        """
        logging.info("Enriching person attributes")
        
        # Add node labels based on person_type
        df_enriched = df.withColumn(
            "labels",
            F.when(F.col("person_type") == "citizen", F.lit("Person:Citizen"))
            .when(F.col("person_type") == "resident", F.lit("Person:Resident"))
            .otherwise(F.lit("Person"))
        )
        
        # Convert binary gender (0=Female, 1=Male) to M/F strings
        df_enriched = df_enriched.withColumn(
            "sex",
            F.when(F.col("sex") == "0", F.lit('F'))
            .when(F.col("sex") == "1", F.lit('M'))
            .when(F.upper(F.col("sex")).isin(['M', 'MALE']), F.lit('M'))
            .when(F.upper(F.col("sex")).isin(['F', 'FEMALE']), F.lit('F'))
            .otherwise(F.col("sex"))
        )

        # Rename spm_national_id to national_id for output
        df_enriched = df_enriched.withColumnRenamed("spm_national_id", "national_id")

        return df_enriched

def validate_and_clean(df, spark_session):
        """
        Validate and clean person data
        
        Args:
            df: Persons DataFrame
            
        Returns:
            Cleaned DataFrame
        """
        logging.info("Validating and cleaning person data")
        
        # Remove records with null person_no
        df_clean = df.filter(F.col("spm_person_no").isNotNull())

        # Remove duplicates (shouldn't exist after deduplication, but safety check)
        df_clean = df_clean.dropDuplicates(["spm_person_no"])

        # Validate data quality
        null_checks = DataQualityChecker(spark_session).check_null_values(
            df_clean,
            ['spm_person_no', 'full_name']
        )

        attribute_checks = DataQualityChecker(spark_session).check_person_attributes(df_clean)

        logging.info("="*80)
        logging.info("Person data validated and cleaned")
        logging.info("="*80)

        return df_clean


def write_statistics(df, output_path):
        """Write summary statistics"""
        stats = (
            df.groupBy("person_type", "sex")
            .count()
            .orderBy("person_type", "sex")
        )
        
        stats_path = f"{output_path}/statistics/person_stats.csv"
        (
            stats
            .coalesce(1)
            .write
            .mode("overwrite")
            .option("header", "true")
            .csv(stats_path)
        )
        
        logging.info(f"Statistics written to: {stats_path}")
        
        # Also log to console
        logging.info("="*80)
        logging.info("Person statistics:")
        stats.show()
        logging.info("="*80)


def write_output(df, output_path, partition_by_type: bool = True):
        """
        Write person nodes to CSV files in MinIO
        
        Args:
            df: Persons DataFrame
            partition_by_type: Whether to partition output by person_type
        """
        logging.info(f"Writing output to: {output_path}")
        
        # Fix label format: "Person:Citizen" → "Person;Citizen" for neo4j-admin import
        df_fixed = df.withColumn(
            "labels",
            F.regexp_replace(F.col("labels"), ":", ";")
        )

        # Select and rename columns for neo4j-admin import format
        output_df = df_fixed.select(
            F.col("spm_person_no").alias("personId:ID"),
            F.col("full_name").alias("fullName"),
            F.col("spm_full_aname").alias("arabicName"),
            F.col("sex").alias("sex"),
            F.col("person_type").alias("personType"),
            F.col("labels").alias(":LABEL"),
            F.col("spm_dob").alias("dob"),
            F.col("nat_code_curr_nat").alias("nationality"),
            "passport",
            "contact_no",
            "national_id"
        )
        
        try:
            if partition_by_type:
                # Write partitioned by person_type for easier loading
                (
                    output_df
                    .repartition(10, "personType")  # More files for parallel Neo4j import
                    .write
                    .mode("overwrite")
                    .option("header", "true")
                    .option("quote", '"')
                    .option("escape", '"')
                    .partitionBy("personType")
                    .csv(f"{output_path}/persons")
                )
                logging.info("="*80)
                logging.info("Successfully wrote partitioned person data")
                logging.info("="*80)
            else:
                # Write as single CSV
                (
                    output_df
                    .coalesce(1)
                    .write
                    .mode("overwrite")
                    .option("header", "true")
                    .option("quote", '"')
                    .option("escape", '"')
                    .csv(f"{output_path}/persons_all")
                )
                
                logging.info("="*80)
                logging.info("Successfully wrote single person CSV")
                logging.info("="*80)
            
            # Write summary statistics
            write_statistics(df, output_path)
            
        except Exception as e:
            logging.error(f"Failed to write output: {str(e)}")
            raise



def run(source_df, hub_df, pit_df, hub_ids_df, sat_ids_df, echannel_df, output_path, spark_session):
        """Execute the complete extraction pipeline"""
        logging.info("="*80)
        logging.info("Starting Person Node Extraction")
        logging.info("="*80)

        start_time = datetime.now()

        try:
            # Cache source_df — used in both extract_persons and determine_person_type
            source_df.cache()

            # Step 1: Extract person IDs and gender from both sides
            persons_df = extract_persons_from_both_sides(source_df)

            # Step 2: Dedup hub_person_master by latest load_datetime
            hub_deduped = dedup_hub_person_master(hub_df)

            # Step 3a: Enrich from person master (hub -> pit join for name, DOB, nationality)
            persons_df = enrich_from_person_master(persons_df, hub_deduped, pit_df)

            # Step 3b: Enrich with passport numbers (hub_person_ids -> sat_person_ids)
            persons_df = get_passport_numbers(persons_df, hub_ids_df, sat_ids_df)

            # Step 3c: Enrich with contact numbers (spm_national_id → echannel.applicant_eida_number)
            persons_df = get_contact_numbers(persons_df, echannel_df)

            # Step 4: Determine person types
            persons_df = determine_person_type(persons_df, source_df)

            # Step 5: Enrich attributes (labels, gender conversion, rename national_id)
            persons_df = enrich_person_attributes(persons_df)

            # Step 6: Validate and clean
            persons_df = validate_and_clean(persons_df, spark_session)

            # Step 7: Write output
            write_output(persons_df, output_path)

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            logging.info("="*80)
            logging.info(f"Person Node Extraction completed successfully in {duration:.2f} seconds")
            logging.info("="*80)

            return persons_df

        except Exception as e:
            logging.error(f"Person extraction failed: {str(e)}", exc_info=True)
            raise



def main(spark_session):
    try:
        parquet_path = str(spark_job_args.get("parquet_path"))
        logging.info("The family_relations parquet path is --> {}".format(parquet_path))

        hub_path = str(spark_job_args.get("hub_person_master_path"))
        logging.info("The hub_person_master parquet path is --> {}".format(hub_path))

        pit_path = str(spark_job_args.get("pit_person_master_path"))
        logging.info("The pit_person_master parquet path is --> {}".format(pit_path))

        hub_ids_path = str(spark_job_args.get("hub_person_ids_path"))
        logging.info("The hub_person_ids parquet path is --> {}".format(hub_ids_path))

        sat_ids_path = str(spark_job_args.get("sat_person_ids_path"))
        logging.info("The sat_person_ids parquet path is --> {}".format(sat_ids_path))

        echannel_path = str(spark_job_args.get("pit_echannel_request_master_path"))
        logging.info("The pit_echannel_request_master parquet path is --> {}".format(echannel_path))

        csv_output_path = str(spark_job_args.get("output_path"))
        logging.info("The CSV output path for Neo4j is --> {}".format(csv_output_path))

        # Read all 6 parquet sources
        df = spark.read.parquet(parquet_path)
        hub_df = spark.read.parquet(hub_path)
        pit_df = spark.read.parquet(pit_path)
        hub_ids_df = spark.read.parquet(hub_ids_path)
        sat_ids_df = spark.read.parquet(sat_ids_path)
        echannel_df = spark.read.parquet(echannel_path)

        run(df, hub_df, pit_df, hub_ids_df, sat_ids_df, echannel_df, csv_output_path, spark_session)

    except Exception as ex:
        logging.error(ex)
        sc.stop()
        raise Exception('! Something went wrong with this job')

    finally:
        logging.info('Stopping...')
        sc.stop()


if __name__ == '__main__':
    # Provide Spark Session additional config options as dictionary
    spark_options = {
        "spark.sql.shuffle.partitions": "80",                       # 2x core count (40 cores)
        "spark.sql.adaptive.enabled": "true",                        # enable AQE
        "spark.sql.adaptive.coalescePartitions.enabled": "true",     # auto-coalesce small partitions
        "spark.sql.autoBroadcastJoinThreshold": "104857600",         # 100MB (up from 10MB default)
        "spark.sql.catalog.my_catalog.write.distribution-mode": "hash",
        "write.target-file-size-bytes": "134217728",
        "spark.sql.iceberg.fanout-enabled": "true",
    }
    spark, sc, spark_app_name, spark_job_args, cluster_details_spark_args, minio_s3_credentials,\
    credentials  = CommonProcessHelperUtils.\
                                            initialize_read_arguments(spark_options=spark_options, mount_bucket_name=MOUNT_BUCKET)
    logging.info(f"spark_job_args: {spark_job_args}")

    main(spark)
    exit()
