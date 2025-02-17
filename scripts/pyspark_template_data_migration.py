# from pyspark.sql.functions import 
import os
from pyspark.sql.types import StructType
from pyspark.sql.functions import to_date, col, to_timestamp, lit, current_timestamp
from pyspark.sql import SparkSession, DataFrame
from typing import Union, List, Tuple
import time
from datetime import datetime, timedelta
# Custom Dependencies
# TODO: this is added to help airflow detect common_utils as module
import sys
sys.path.append("/workflows/pyspark_template/")
print("Sys Path:", sys.path)


from common_utils.scripts.common_utilities import CommonLogging, CommonIcebergUtilities
from common_utils.scripts.helper.common_helper_utilities import CommonBasicUtilities, CommonProcessHelperUtils, CommonAPIUtilities
from common_utils.scripts.data.common_data_utilities import CommonDataUtilities
from common_utils.scripts.s3.common_s3_utilities import CommonS3Utilities

from common_utils.scripts.db_operations.db_operations_factory import DBOperationsFactory
from common_utils.scripts.db_operations.db_operations import BaseDBOperations


logging = CommonLogging.get_logger()

# ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** *****

MOUNT_BUCKET = '/workflows'

class Constants:
    DEFAULT_RECORDS_PER_BATCH = 1_00_000
    DEFAULT_NUMBER_OF_PARTITIONS = 1
    DEFAULT_LOWER_BOUND = 0
    DEFAULT_UPPER_BOUND = DEFAULT_RECORDS_PER_BATCH
    DEFAULT_IS_COL_FOR_PARTITION_NULL_SUPP=False

class DefaultPySparkScript:
    def get_dummy_data():
        data = [
            {
                "full_name":"Haben Tesfamariam Gaim",
                "date_of_birth":  "1980-02-09",
                "position": "Senior  Data Scientist",
                 "salary": 35000.00
            },
            {
                "full_name":"Hana Senay",
                "date_of_birth":  "1984-11-23",
                "position": "Software Engineer",
                 "salary": 27600.00
            },
            {
                "full_name":"Ali Abdu",
               "date_of_birth":  "1985-01-16",
                "position": "Data Engineer",
                 "salary": 30300.00
            }
        ]
        return data
    
    def ingest_data(spark, output_warehouse_fq_table, output_wh_table_load_strategy, catalog_minio_bucket:str = None, location: str = None):
        from pyspark.sql.types import StructType, StructField, StringType, DoubleType, DateType

        data = DefaultPySparkScript.get_dummy_data()
        schema = StructType([
            StructField("full_name", StringType(), True),
            StructField("date_of_birth", StringType(), True),
            StructField("position", StringType(), True),
            StructField("salary", DoubleType(), True)
        ])
        
        data_df = spark.createDataFrame(data, schema=schema)\
                .withColumn("date_of_birth", to_date(col("date_of_birth"), "yyyy-MM-dd"))
        
        data_df = data_df.withColumn("ingested_at", to_timestamp(lit(current_timestamp())))

        script_adding_columns = ["ingested_at"]
        
        data_df.printSchema()
        data_df.cache()

        if not CommonIcebergUtilities.table_exists(output_warehouse_fq_table=output_warehouse_fq_table, spark=spark):
            logging.warning(f""">>Table '{output_warehouse_fq_table}' is not available!!!""")
            CommonIcebergUtilities.create_table(output_warehouse_fq_table=output_warehouse_fq_table,
                                            spark=spark,
                                             data_df=data_df,
                                             catalog_minio_bucket=catalog_minio_bucket,
                                             location=location
                                             )
            
        data_df.show(10, truncate=False)

        CommonIcebergUtilities.iceberg_load_operation(spark=spark,
                                                        output_wh_table_load_strategy=output_wh_table_load_strategy,
                                                        data_df=data_df,
                                                        output_warehouse_fq_table=output_warehouse_fq_table,
                                                        script_adding_columns=script_adding_columns
                                                    )
       
        data_df.unpersist()
        logging.info(">>Data ingestion completed...")
        warehouse_catalog, warehouse_schema, warehouse_ref_table = output_warehouse_fq_table.split(".")

        CommonIcebergUtilities.optimize_commands(spark, warehouse_catalog, warehouse_schema, warehouse_ref_table)

class DataMigrationFromDB:

    @staticmethod
    def calculate_batches(
        lower_bound: Union[str, int, float], 
        upper_bound: Union[str, int, float], 
        num_partitions: int, 
        records_per_batch: int
    ) -> List[Tuple[Union[int, float, str], Union[int, float, str]]]:
        """
        Generates batches within lower and upper bounds for both numerical and date-based partitions.
        Ensures records_per_batch is divisible by num_partitions and distributes records efficiently.
        """

        # Handle date conversion if inputs are strings
        is_datetime_partitioning = isinstance(lower_bound, str) and isinstance(upper_bound, str)
        print(f"""Start of batches calculation -> is_datetime_partitioning: {is_datetime_partitioning}, 
              lower_bound: {lower_bound}, upper_bound: {upper_bound},records_per_batch: {records_per_batch}""")
        
        if is_datetime_partitioning:
            try:
                # Detect format: ISO format (YYYY-MM-DDTHH:MM:SS) or standard format (YYYY-MM-DD HH:MM:SS)
                if "T" in lower_bound:  # ISO format
                    datetime_format = "%Y-%m-%dT%H:%M:%S"
                    time_unit = "seconds"
                elif " " in lower_bound:  # Standard format
                    datetime_format = "%Y-%m-%d %H:%M:%S"
                    time_unit = "seconds"
                else:  # Date format
                    datetime_format = "%Y-%m-%d"
                    time_unit = "days"

                lower_bound = datetime.strptime(lower_bound, datetime_format)
                upper_bound = datetime.strptime(upper_bound, datetime_format)
            except ValueError:
                raise ValueError("Date format must be 'YYYY-MM-DD', 'YYYY-MM-DD HH:MM:SS', or 'YYYY-MM-DDTHH:MM:SS'.")


        if lower_bound > upper_bound:
            raise ValueError(f"lower_bound must be less than upper_bound -> lower_bound:{lower_bound}, upper_bound:{upper_bound}.")
        
        if not is_datetime_partitioning and (lower_bound < 0 or upper_bound < 0):
            raise ValueError(f"lower_bound or upper_bound cannot be negative -> lower_bound:{lower_bound}, upper_bound:{upper_bound}.")
        
        if records_per_batch <= 0:
            raise ValueError(f"records_per_batch must be positive -> records_per_batch:{records_per_batch}.")
        
        # Ensure records_per_batch is a multiple of num_partitions
        # if records_per_batch % num_partitions != 0:
        #     records_per_batch = (records_per_batch // num_partitions) * num_partitions
        
        batches = []
        start = lower_bound

        while start <= upper_bound:
            if is_datetime_partitioning and time_unit:
                # Handle date increments
                if time_unit == "days":
                    end = min(start + timedelta(days=records_per_batch - 1), upper_bound)
                    if (end + timedelta(days=1)) == upper_bound:
                        end = end + timedelta(days=1)
                    batches.append((start.strftime(datetime_format), end.strftime(datetime_format)))
                    start = end + timedelta(days=1)

                elif time_unit == "seconds":
                    end = min(start + timedelta(seconds=records_per_batch - 1), upper_bound)
                    if (end + timedelta(seconds=1)) == upper_bound:
                        end = end + timedelta(seconds=1)
                    batches.append((start.strftime(datetime_format), end.strftime(datetime_format)))
                    start = end + timedelta(seconds=1)

            else:
                # Handle integer/float increments
                end = min(start + records_per_batch - 1, upper_bound)  # Exclusive upper bound except for last batch
                if (end + 1) == upper_bound:
                    end +=1 #Include the upper_bound
                batches.append((start, end))
                start = end + 1  # Move to the next batch start point
        return batches
    

    @staticmethod
    def load_and_optimize(spark:SparkSession, data_df: DataFrame, output_warehouse_fq_table:str, 
                output_wh_table_load_strategy:str, merge_data_join_fields: str=None,
                ):
        
        data_df.cache()

         # Spark V 3.1 does not support data_df.isEmpty(), it's new on 3.3
        # count = data_df.count() # It's expensive, don't use it unless it's there is no other option.
        tmp_df = data_df.take(1)
        logging.info("Read info -> take_one_record from Dataframe len {}".format(len(tmp_df)))
        if len(tmp_df) >= 1:
            script_adding_columns = []
            # Adding this to remove duplicates - we may get duplicates
            if "ingested_at" not in data_df.columns:
                data_df = data_df.withColumn("ingested_at", to_timestamp(lit(current_timestamp())))

                script_adding_columns.append("ingested_at")

            logging.info(">> Dataframe schema: " + str(data_df.schema))
            data_df.show(10)
            CommonIcebergUtilities.iceberg_load_operation(spark, output_wh_table_load_strategy, data_df,output_warehouse_fq_table,
                                                                        script_adding_columns,merge_data_join_fields=None)
        logging.info(f""">>Ingestion to table '{output_warehouse_fq_table}' completed,""")

        data_df.unpersist()
        
        warehouse_catalog, warehouse_schema, warehouse_ref_table = output_warehouse_fq_table.split(".")

        CommonIcebergUtilities.optimize_commands(spark, warehouse_catalog, warehouse_schema, warehouse_ref_table)


    @staticmethod
    def read_and_load_data(dbOps: BaseDBOperations, spark, table_name, column_for_partitioning, selected_columns, 
                            lower_bound, upper_bound,  num_partitions, output_warehouse_fq_table, output_wh_table_load_strategy,
                            is_col_for_partition_null_supp=False, records_per_batch=1_00_000, catalog_minio_bucket:str =None, location:str = None
                            ):
        logging.info(f""">>Table info -> table_name: {table_name},  column_for_partitioning: {column_for_partitioning}, num_partitions: {num_partitions},""")
        
        if not CommonIcebergUtilities.table_exists(output_warehouse_fq_table=output_warehouse_fq_table, spark=spark):
            logging.warning(f""">>Table '{output_warehouse_fq_table}' is not available!!!""")
            if CommonBasicUtilities.isEmpty(selected_columns) :
                selected_columns = "*"
            query  = f"select {selected_columns} from {table_name} limit 1"
            data_df: DataFrame = dbOps.read_data(table_name=table_name,query=query)
            
            CommonIcebergUtilities.create_table(output_warehouse_fq_table=output_warehouse_fq_table,
                                            spark=spark,
                                             data_df=data_df,
                                             catalog_minio_bucket=catalog_minio_bucket,
                                             location=location
                                             )

        if not column_for_partitioning:
            logging.info(f""">>Reading a table: {table_name} where  column_for_partitioning is None/Empty or not provided.
                        If `column_for_partitioning` is not provided or None/Empty, no batching or partitioning will happen -entire table will load on one executor at one time!!""")
        
            data_df: DataFrame = dbOps.read_data(table_name=table_name, column_names=selected_columns)

            DataMigrationFromDB.load_and_optimize(spark=spark, data_df=data_df,output_warehouse_fq_table=output_warehouse_fq_table, 
                                                   output_wh_table_load_strategy=output_wh_table_load_strategy)
        else:
            # column_for_partitioning is provided
            iteration_num = 1

            batches = DataMigrationFromDB.calculate_batches(lower_bound=lower_bound, upper_bound=upper_bound,num_partitions=num_partitions,records_per_batch=records_per_batch)
            logging.info(""">>Batches -> {}""".format(batches))
            for batch in batches:
                start, end = batch

                logging.info(f""">>Iteration : {iteration_num}, lower_bound: {start}, upper_bound: {end}""" )
                
                data_df: DataFrame = dbOps.read_data(table_name=table_name,column_names=selected_columns,column_for_partitioning=column_for_partitioning,
                                        lower_bound=start,upper_bound=end,num_partitions=num_partitions)
                
                DataMigrationFromDB.load_and_optimize(spark=spark, data_df=data_df,output_warehouse_fq_table=output_warehouse_fq_table, 
                                                    output_wh_table_load_strategy=output_wh_table_load_strategy)
                iteration_num +=1

            # check if there is/are any null values for partitioning column and ingest it if is_col_for_partition_null_supp is True
            if is_col_for_partition_null_supp and column_for_partitioning is not None:
                logging.info(f""">>Read Null values for table_name: {table_name},  column_for_partitioning: {column_for_partitioning}, 
                            num_partitions: {num_partitions}, is_col_for_partition_null_supp: {is_col_for_partition_null_supp}""")
                
                if CommonBasicUtilities.isEmpty(selected_columns) :
                    selected_columns = "*"
                query  = f"select {selected_columns} from {table_name} where {column_for_partitioning} is null"
                data_df: DataFrame = dbOps.read_data(table_name=table_name,query=query)

                DataMigrationFromDB.load_and_optimize(spark=spark, data_df=data_df,output_warehouse_fq_table=output_warehouse_fq_table, 
                                                   output_wh_table_load_strategy=output_wh_table_load_strategy)


    @staticmethod        
    def run_ingestion_pipeline(spark: SparkSession, output_wh_table_load_strategy, output_warehouse_fq_table, 
                               output_table_snapshots_delete_period, db_details,location:str = None, 
                               catalog_minio_bucket:str = None
                               ):                                             
      
        db_properties = db_details.get("db_properties", {})
        table_name  = db_details.get("db_table", None)
        column_for_partitioning  = db_details.get("partitioning_column", None)
        lower_bound  = db_details.get("lower_bound", Constants.DEFAULT_LOWER_BOUND)
        upper_bound  = db_details.get("upper_bound", Constants.DEFAULT_UPPER_BOUND)
        num_partitions  = db_details.get("num_partitions", Constants.DEFAULT_NUMBER_OF_PARTITIONS)
        selected_columns  = db_details.get("selected_columns", [])
        is_col_for_partition_null_supp  = bool(db_details.get("is_col_for_partition_null_supp", Constants.DEFAULT_IS_COL_FOR_PARTITION_NULL_SUPP))
        records_per_batch  = db_details.get("records_per_batch", Constants.DEFAULT_RECORDS_PER_BATCH)
        
        
        formated_selected_columns = CommonDataUtilities.parse_selected_columns(selected_columns, column_for_partitioning)
        logging.info("selected_columns: {}".format(str(formated_selected_columns)))

        dbOps: BaseDBOperations = DBOperationsFactory().create(db_properties, spark)
        
        
        DataMigrationFromDB.read_and_load_data(dbOps, spark, table_name, column_for_partitioning, formated_selected_columns, lower_bound, 
                                        upper_bound, num_partitions, output_warehouse_fq_table, output_wh_table_load_strategy, 
                                        is_col_for_partition_null_supp,
                                        records_per_batch=records_per_batch
                                        ,catalog_minio_bucket=catalog_minio_bucket
                                        ,location=location
                                        )


def main():
    try:
       
        db_details = spark_job_args["db_details"]
        operation_type = spark_job_args.get("operation_type", "default")

        
        # Arguments - DW output table
        output_warehouse_fq_table = spark_job_args["output_warehouse_fq_table"]
        output_wh_table_load_strategy = spark_job_args.get("output_wh_table_load_strategy", "APPEND")
        output_table_snapshots_delete_period = spark_job_args.get("output_table_snapshots_delete_period", 60)
        location = spark_job_args.get("output_table_location", None)
        catalog_minio_bucket = spark_job_args.get("catalog_minio_bucket", None) #This is from ENV var, no need to add in the config,
        

        logging.info("""output_warehouse_fq_table: %s, output_wh_table_load_strategy: %s, output_table_snapshots_delete_period: %s
                """.format(output_warehouse_fq_table, output_wh_table_load_strategy, output_table_snapshots_delete_period))

        if operation_type.lower() == "migration":
            DataMigrationFromDB.run_ingestion_pipeline(spark=spark
                                                       ,output_wh_table_load_strategy=output_wh_table_load_strategy
                                                       ,output_warehouse_fq_table=output_warehouse_fq_table
                                                        ,output_table_snapshots_delete_period=output_table_snapshots_delete_period
                                                        ,db_details=db_details
                                                        ,location=location
                                                        ,catalog_minio_bucket=catalog_minio_bucket
                                                        )
        else:
            DefaultPySparkScript.ingest_data(spark=spark
                                             ,output_warehouse_fq_table=output_warehouse_fq_table
                                             ,output_wh_table_load_strategy=output_wh_table_load_strategy
                                             ,location=location
                                             ,catalog_minio_bucket=catalog_minio_bucket
                                             )
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
        "spark.sql.shuffle.partitions": "10",
        "spark.default.parallelism": "10",
    }
    spark, sc, spark_app_name, spark_job_args, cluster_details_spark_args, minio_s3_credentials,\
    credentials  = CommonProcessHelperUtils.\
                                            initialize_read_arguments(spark_options=spark_options, mount_bucket_name=MOUNT_BUCKET)
    logging.info(f"spark_job_args: {spark_job_args}")

    main()
    exit()
