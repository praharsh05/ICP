
from pyspark.sql.functions import col
from pyspark.sql import SparkSession
from pyspark.sql.dataframe import DataFrame

from dateutil.relativedelta import relativedelta

class CommonLogging:
    @staticmethod
    def get_logger(log_level_str='INFO'):
        import logging
        try:
            level_num = logging.getLevelName(log_level_str.upper())
            if not isinstance(level_num, int):
                raise ValueError(f"Logging Level is not in predefined list: {str(level_num)}")

        except ValueError:
            level_num = logging.getLevelName('INFO')

        logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s', level=level_num,
                            datefmt='%y/%m/%d %H:%M:%S')

        return logging.getLogger()


logging = CommonLogging.get_logger()


def singleton(class_):
    instances = {}

    def getinstance(*args, **kwargs):
        if class_ not in instances:
            instances[class_] = class_(*args, **kwargs)
        return instances[class_]

    return getinstance


class CommonIcebergUtilities:

    @staticmethod
    def merge_upsert_process(spark, data_df, s3_warehouse_catalog, s3_warehouse_schema,
                             s3_warehouse_ref_table, join_fields):
        logging.info('> Merge data: Start')
        columns = data_df.columns
        new_data = data_df.select(columns)
        update_set_fields = list(set(columns) - set(join_fields))

        logging.info("update_set_fields:" + str(update_set_fields))

        # UPSERT
        new_data.createOrReplaceTempView("new_data")
        logging.info('> Columns: %s' % str(columns))

        # Having null validation , it may take time , so replace primary keys null values to empty spaces
        statement = \
            "MERGE INTO {}.{}.{} t USING new_data s ON {} \
                WHEN MATCHED THEN UPDATE SET {} \
                    WHEN NOT MATCHED THEN INSERT ({}) VALUES ({})".format(
                s3_warehouse_catalog, s3_warehouse_schema, s3_warehouse_ref_table,
                ' AND '.join(map(lambda jc: "((s.J_C=t.J_C) or (s.J_C IS NULL and t.J_C IS NULL))".replace("J_C", jc),
                                 join_fields)),
                ','.join(map(lambda f: 't.' + f + '=' + 's.' + f, update_set_fields)),
                ','.join(columns), ','.join(map(lambda c: 's.' + c, columns))
            )

        '''
        # Without null validation , Make sure to replace primary keys null values to empty spaces
        statement = \
            "MERGE INTO {}.{}.{} t USING new_data s ON {} \
                WHEN MATCHED THEN UPDATE SET {} \
                    WHEN NOT MATCHED THEN INSERT ({}) VALUES ({})".format(
                s3_warehouse_catalog, s3_warehouse_schema, s3_warehouse_ref_table,
                ' AND '.join(map(lambda jc: "(s.J_C=t.J_C)".replace("J_C", jc),
                                 join_fields)),
                ','.join(map(lambda f: 't.' + f + '=' + 's.' + f, update_set_fields)),
                ','.join(columns), ','.join(map(lambda c: 's.' + c, columns))
            )
        '''
        logging.info('Merge Statement: %s' % statement)
        spark.sql(statement).show(truncate=False)
        logging.info('> Merge data: Completed')

    @staticmethod
    def merge_insert_process(spark, data_df, s3_warehouse_catalog, s3_warehouse_schema,
                             s3_warehouse_ref_table, join_fields):
        logging.info('> Merge data: Start')
        columns = data_df.columns
        new_data = data_df.select(columns)

        # Merge insert
        new_data.createOrReplaceTempView("new_data")
        logging.info('> Columns: %s' % str(columns))

        statement = \
            "MERGE INTO {}.{}.{} t USING new_data s ON {} \
             WHEN NOT MATCHED THEN INSERT ({}) VALUES ({})".format(
                s3_warehouse_catalog, s3_warehouse_schema, s3_warehouse_ref_table,
                ' AND '.join(map(lambda jc: "((s.J_C IS NULL and t.J_C IS NULL) or (s.J_C=t.J_C))".replace("J_C", jc),
                                 join_fields)),
                ','.join(columns), ','.join(map(lambda c: 's.' + c, columns))
            )

        logging.info('Merge Statement: %s' % statement)
        spark.sql(statement).show(truncate=False)
        logging.info('> Merge insert data: Completed')

    @staticmethod
    def insert_overwrite_process(spark, data_df,
                                 s3_warehouse_catalog, s3_warehouse_schema, s3_warehouse_ref_table,
                                 warehouse_table_partition_details=None):
        logging.info('> Insert Overwrite data: Start')
        columns = data_df.columns
        new_data = data_df.select(columns)

        # Insert Overwrite
        new_data.createOrReplaceTempView("new_data")
        logging.info('> Columns: %s' % str(columns))

        if warehouse_table_partition_details is None:
            statement = \
                "INSERT OVERWRITE {}.{}.{} SELECT * from new_data".format(
                    s3_warehouse_catalog, s3_warehouse_schema, s3_warehouse_ref_table)

        else:
            statement = \
                "INSERT OVERWRITE {}.{}.{} PARTITION ({} = '{}') SELECT * from new_data".format(
                    s3_warehouse_catalog, s3_warehouse_schema, s3_warehouse_ref_table,
                    warehouse_table_partition_details["partition_column"],
                    warehouse_table_partition_details["partition_column_value"])

        logging.info('Insert Overwrite Statement: %s' % statement)
        spark.sql(statement).show(truncate=False)
        logging.info('> Insert Overwrite data: Completed')

    @staticmethod
    def delete_process(spark, data_df, s3_warehouse_catalog, s3_warehouse_schema,
                       s3_warehouse_ref_table, join_fields):
        logging.info('> Delete Record: Start')

        columns = data_df.columns
        new_data = data_df.select(columns)

        new_data.createOrReplaceTempView("new_data")
        logging.info('> Columns: %s' % str(columns))

        query_statement = \
            "MERGE INTO {}.{}.{} t USING new_data s ON {} \
                WHEN MATCHED THEN DELETE".format(
                s3_warehouse_catalog, s3_warehouse_schema, s3_warehouse_ref_table,
                ' AND '.join(map(lambda f: 's.' + f + '=' + 't.' + f, join_fields)))

        logging.info('Update Merge Statement: %s' % query_statement)
        spark.sql(query_statement).show(truncate=False)
        logging.info('> MERGE Delete Record: Completed')

    @staticmethod
    def optimize_commands(spark, catalog, schema, table):
        fq_table = "{}.{}.{}".format(catalog, schema, table)

        # ******************** ******************* ******************* ******************* *******************
        #             Debug                             #             Debug                               #

        logging.warning(" >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Starting- Before optimizations >>>>>>>>>>")
        logging.info(" >> >> Table History")
        ib_tbl_history = "SELECT * FROM {}.history".format(fq_table)
        spark.sql(ib_tbl_history).show(truncate=False)

        logging.info(" >> >> Data Files")
        ib_tbl_files = "SELECT * FROM {}.files".format(fq_table)
        spark.sql(ib_tbl_files).show(truncate=False)

        logging.info(" >> >> All Data Files")
        ib_tbl_all_data_files = "SELECT * FROM {}.all_data_files".format(fq_table)
        spark.sql(ib_tbl_all_data_files).show(truncate=False)

        logging.info(" >> >> Manifests Files")
        ib_tbl_manifest_files = "SELECT * FROM {}.manifests".format(fq_table)
        spark.sql(ib_tbl_manifest_files).show(truncate=False)

        logging.info(" >> >> All Manifests Files")
        ib_tbl_all_meta_files = "SELECT * FROM {}.all_manifests".format(fq_table)
        spark.sql(ib_tbl_all_meta_files).show(truncate=False)
        #             Debug                             #             Debug                               #
        # ******************** ******************* ******************* ******************* *******************

        logging.info(" >> >> Rewriting data files")
        ib_rw_data_files_query_stmt = "CALL {}.system.rewrite_data_files(table => '{}', " \
                                      "options => map('target-file-size-bytes','524288000'))".format(catalog, fq_table)
        spark.sql(ib_rw_data_files_query_stmt).show(truncate=False)

        logging.info(" >> >> Rewriting manifests files")
        ib_rw_manifests_files_query_stmt = "CALL {}.system.rewrite_manifests(table => '{}', use_caching => false)".format(catalog, fq_table)
        spark.sql(ib_rw_manifests_files_query_stmt).show(truncate=False)       

        logging.info(" >> >> Current snapshots before calling expire snapshots")
        spark.sql("SELECT committed_at, snapshot_id, operation FROM {}.snapshots".format(fq_table)).show(truncate=False)

        from datetime import datetime

        current_timestamp = datetime.today()
        older_than = 7
        retention_unit = "days"

        ex_snp_tmp_str = (current_timestamp - relativedelta(**{retention_unit: older_than})).strftime("%Y-%m-%d %H:%M:%S")

        ib_expire_snapshot_query_stmt = "CALL {}.system.expire_snapshots(table => '{}', older_than => TIMESTAMP '{}'," \
                                        " retain_last => 1, stream_results => true)".format(catalog,
                                                                                            fq_table, ex_snp_tmp_str)

        # ib_expire_snapshot_query_stmt = "CALL {}.system.expire_snapshots(table => '{}'," \
        #                                 " retain_last => 1, stream_results => true)".format(catalog, fq_table)

        try:

            spark.sql(ib_expire_snapshot_query_stmt).show(truncate=False)

        except Exception as e:
            logging.error(">> >>Expiry snapshot-exception in expiring snapshots: >> >> " + str(e))
            pass

        logging.info(" >> >> Current snapshots after calling expire snapshots")
        spark.sql("SELECT committed_at, snapshot_id, operation FROM {}.snapshots".format(fq_table)).show(truncate=False)

        logging.info(" >> >> Remove orphan files")
        ib_rm_orphan_files_query_stmt = "CALL {}.system.remove_orphan_files (table => '{}')".format(catalog, fq_table)
        spark.sql(ib_rm_orphan_files_query_stmt).show(truncate=False)

        # ******************** ******************* ******************* ******************* *******************
        #             Debug                             #             Debug                               #

        logging.warning(" >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> after remove orphan files >>>>>>>>>>>>>>>>>>>>>")
        logging.info(" >> >> Data Files")
        ib_tbl_files = "SELECT * FROM {}.files".format(fq_table)
        spark.sql(ib_tbl_files).show(truncate=False)

        logging.info(" >> >> All Data Files")
        ib_tbl_all_data_files = "SELECT * FROM {}.all_data_files".format(fq_table)
        spark.sql(ib_tbl_all_data_files).show(truncate=False)

        logging.info(" >> >> Manifests Files")
        ib_tbl_manifest_files = "SELECT * FROM {}.manifests".format(fq_table)
        spark.sql(ib_tbl_manifest_files).show(truncate=False)

        logging.info(" >> >> All Manifests Files")
        ib_tbl_all_meta_files = "SELECT * FROM {}.all_manifests".format(fq_table)
        spark.sql(ib_tbl_all_meta_files).show(truncate=False)

        #             Debug                             #             Debug                               #
        # ******************** ******************* ******************* ******************* *******************
        #

    @staticmethod
    def iceberg_load_operation(spark, output_wh_table_load_strategy, data_df, output_warehouse_fq_table,
                               script_adding_columns, merge_data_join_fields=None, input_schema= None
                               , is_repartition_needed= False, repartition_col: str = None):

        table_catalog, table_schema, table = output_warehouse_fq_table.split(".")
        logging.info(f">> >>Table info - {output_warehouse_fq_table}")

        table_col_info = CommonIcebergUtilities.get_tbl_column_info_select(spark, output_warehouse_fq_table)

        logging.info("Table columns info: {}".format(table_col_info))
    
        
        casted_columns = CommonIcebergUtilities.cast_tbl_columns(table_column_info=table_col_info)
        logging.info("Casted table columns: {}".format(casted_columns))

        # Re-ordering of columns as per table
        data_df = data_df.select(*casted_columns)

        if output_wh_table_load_strategy.lower() == "insert_overwrite":
            logging.info(">> >> >> >> Loading table data - INSERT_OVERWRITE")

            data_df.write.format("iceberg").mode("overwrite").save(output_warehouse_fq_table)

            # CommonIcebergUtilities.insert_overwrite_process(spark, data_df, table_catalog, table_schema, table, None)

        elif output_wh_table_load_strategy.lower() == "merge_insert":
            logging.info(">> >> >> >> Loading table data - MERGE_INSERT")
            if merge_data_join_fields is None or not merge_data_join_fields:
                merge_data_join_fields = [x for x in data_df.columns if x not in script_adding_columns]

            logging.info(">> >> >> >> merge_data_join_fields: {}".format(merge_data_join_fields))
            CommonIcebergUtilities.merge_insert_process(spark, data_df, table_catalog, table_schema, table,
                                                        merge_data_join_fields)

        elif output_wh_table_load_strategy.lower() == "merge_upsert":
            logging.info(">> >> >> >> Loading table data - MERGE_UPSERT")
            if merge_data_join_fields is None or not merge_data_join_fields:
                merge_data_join_fields = [x for x in data_df.columns if x not in script_adding_columns]

            logging.info(">> >> >> >> merge_data_join_fields: {}".format(merge_data_join_fields))

            data_df = data_df.sortWithinPartitions(*merge_data_join_fields)
            CommonIcebergUtilities.merge_upsert_process(spark, data_df, table_catalog, table_schema, table,
                                                        merge_data_join_fields)

        elif output_wh_table_load_strategy.lower() == "append":
            logging.info(">> >> >> >> Loading table data - APPEND")
            if is_repartition_needed and repartition_col:
                data_df = data_df.repartition(f"{repartition_col}")
            data_df.writeTo(output_warehouse_fq_table).option("fanout-enabled","true").option("distribution-mode", "none").append()
            

        else:
            raise Exception(
                "Provide proper output_wh_table_load_strategy, provided as:%s" % output_wh_table_load_strategy)

    @staticmethod
    def get_tbl_column_info_describe(spark, output_warehouse_fq_table):
        # Getting columns and data type details of iceberg / warehouse table
        table_details_df = spark.sql("describe {}".format(output_warehouse_fq_table))
        table_details_df = table_details_df.filter((col("data_type").isNotNull()) & (col("data_type") != ""))
        table_details_df = table_details_df.select(*["col_name", "data_type"])
        table_details_dict_list = [row.asDict() for row in table_details_df.collect()]

        table_col_info = {}
        for table_details_dict in table_details_dict_list:
            table_col_info[table_details_dict["col_name"]] = table_details_dict["data_type"]

        return table_col_info

    @staticmethod
    def get_tbl_column_info_select(spark, output_warehouse_fq_table):

        table_cols_df = spark.sql("select * from {} limit 1".format(output_warehouse_fq_table))
        table_col_info = {}
        for col_info in table_cols_df.dtypes:
            table_col_info[col_info[0]] = col_info[1]

        return table_col_info

    @staticmethod
    def cast_tbl_columns(table_column_info, input_schema= None):
        # Now, cast the columns of data_df according to the table column info
        casted_columns = []

        # Loop through each column and cast it to the corresponding type
        if input_schema:
            #if input_schema is provided in the config file --maybe used for col name or type transformation.
            logging.info(">> >> input_schema: {}".format(input_schema))
            for _, value in input_schema.items():
                source_col  = value["source"]
                target_col  = value["target"]
                target_type  = value["target_type"]
                if target_type:
                    target_type  = target_type.upper()
                casted_columns.append(col(source_col).cast(target_type).alias(target_col))
            return casted_columns
        
        for column_name, column_type in table_column_info.items():
            # Cast the column based on the type from the Iceberg table schema
            casted_columns.append(col(column_name).cast(column_type).alias(column_name))
        return casted_columns
    
 
    @staticmethod
    def table_exists(output_warehouse_fq_table: str, spark: SparkSession) -> bool:
        database, table_name = output_warehouse_fq_table.rsplit(".", 1)
        logging.info(f"Schema info -> {database}")
        df = spark.sql(f"SHOW TABLES IN {database}")

        logging.info(">> >> Tables in schema: {}".format(database))
        df.show(20)
        return table_name in df.select("tableName").rdd.flatMap(lambda x: x).collect()
    
    @staticmethod
    def create_table(output_warehouse_fq_table: str, spark: SparkSession, data_df: DataFrame = None,
                      catalog_minio_bucket:str = None, location:str = None, 
                      target_schema_fields = None, column_defs = None, is_oracle_debezium_iceberg_pipeline= None, repartition_col=None):

         # Get the schema from the DataFrame
        if not catalog_minio_bucket:
            raise Exception("Catalog MinIO bucket name must not be null or empty to create table!!!!")
        
        if column_defs is None:
            column_defs = []
            if target_schema_fields:
                for col_name, col_type in target_schema_fields.items():
                    column_defs.append("{} {}".format(col_name, col_type.upper()))
            else:

                for field in data_df.schema.fields:
                    col_name = field.name
                    col_type = field.dataType.simpleString()

                    # 
                    # if col_type.lower().startswith('decimal'): #TODO
                    #     col_type = "double"
                    # if col_type.lower().startswith('timestamp'): #TODO
                    #     col_type = "long"
                    col_type = col_type.upper()  # Convert Spark SQL type to uppercase
                    column_defs.append(f"{col_name} {col_type}")
                

        if is_oracle_debezium_iceberg_pipeline:
            # Extra columns from debezium __table,__source_ts_ms,__db
            #TODO 
            extra_columns = {"__table":"string","__source_ts_ms":"timestamp","__db":"string"}
            for col_name, col_type in extra_columns.items():
                if not any(col_name.upper() in field.upper() for field in column_defs):
                    column_defs.append(f"{col_name} {col_type}")

        # Add 'ingested_at TIMESTAMP' if not already present
        if not any("INGESTED_AT" in field.upper() for field in column_defs):
            column_defs.append("ingested_at TIMESTAMP")

        logging.info(""">>Table schema: {}""".format(column_defs))

        table_catalog, table_schema, table = output_warehouse_fq_table.split(".")
        if not location:
            location = f"s3a://{catalog_minio_bucket}/{table_schema}/{table}"
        
        
        logging.info(">> LOGGING REPARTITION COLUMN -> {}".format(repartition_col))  
        if repartition_col is not None:
            query = f"""
                    CREATE TABLE {output_warehouse_fq_table} (
                        {", ".join(column_defs)}
                    )
                    USING iceberg
                    LOCATION '{location}'  -- Specifies the table's physical location
                    TBLPROPERTIES (
                        'format'='parquet',        -- Storage format
                        'format-version'='2'       -- Iceberg format version
                    )
                """
        else:
            query = f"""
                    CREATE TABLE {output_warehouse_fq_table} (
                        {", ".join(column_defs)}
                    )
                    USING iceberg
                    LOCATION '{location}'  -- Specifies the table's physical location
                    TBLPROPERTIES (
                        'format'='parquet',        -- Storage format
                        'format-version'='2'       -- Iceberg format version
                    )
                """
            

        
        # Execute SQL query
        logging.info(f""">> >> Table '{output_warehouse_fq_table}' will be created at location '{location}'!!!""")
        logging.info(">> >> Create Statement for the table is -> {}".format(query))
        spark.sql(query)
        logging.info(">> >> Table {} created successfully.".format(output_warehouse_fq_table))