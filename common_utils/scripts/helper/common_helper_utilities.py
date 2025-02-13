import requests
import json
import csv
import io
import os
import sys
import time

# Custom Dependencies

from common_utils.scripts.creds_loader import CredentialsLoader
from common_utils.scripts.common_utilities import CommonLogging
from common_utils.scripts.s3.common_s3_utilities import CommonS3Utilities
logging = CommonLogging.get_logger()
# ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** *****


class CommonAPIUtilities:

    def __init__(self):
        pass

    @staticmethod
    def make_request(request_method, request_url, request_header, **kwargs):

        request_body_data_json = kwargs.get("request_body_data_json", None)
        request_body_data = kwargs.get("request_body_data", None)
        request_params = kwargs.get("request_params", None)
        sanitized_request_url = kwargs.get("sanitized_request_url", request_url)

        response_output = ""
        response_header = ""
        response = None
        error_details = {"error_flag": False, "error_status_code": 200, "error_msg": ""}

        try:
            logging.info(f"API request: {request_url}")
            if request_method == 'get':
                response = requests.get(
                    request_url,
                    headers=request_header, stream=True, verify=True
                )
            elif request_method == 'post':
                response = requests.post(
                    request_url,
                    json=request_body_data_json,
                    params=request_params,
                    data=request_body_data,
                    headers=request_header, stream=True, verify=True
                )

            if not response.ok:

                if (response.status_code == 500 and str(response.content).__contains__("timeout exceeded") or
                        response.status_code == 502 and str(response.content).__contains__("Bad Gateway") or
                        response.status_code == 503 and str(response.content).__contains__("Temporarily Unavailable") or
                        response.status_code == 500 and str(response.content).__contains__("Something went wrong")):
                    error_msg = "API timeout exceeded / Bad Gateway / Temporarily Unavailable : %s final_api_url %s" \
                                % (str(response.json), sanitized_request_url)
                    logging.error(error_msg)

                    error_details = {"error_flag": True,
                                     "error_status_code": response.status_code,
                                     "error_msg": error_msg}

                else:

                    error_msg = "API fetching issue (status code not ok), response_content: %s status:%s," \
                                " request_url:%s" % (str(response.content), str(response.status_code),
                                                     sanitized_request_url)
                    logging.error(error_msg)
                    raise Exception(error_msg)
            else:
                response_output = response.content
                response_header = response.headers

            return response_header, response_output, error_details
        except Exception as e:

            response_content = str(response.content) if response is not None else None
            response_header = str(response.headers) if response is not None else None
            response_status_code = str(response.status_code) if response is not None else None

            err_msg = "API fetching issue (exception), Error: %s, status:%s," \
                      " response.headers: %s," \
                      " response_content: %s" % (str(e), response_status_code, response_header, response_content)

            if str(e).lower().__contains__("InvalidChunkLength".lower()) or str(e).lower().__contains__(
                    "failed to establish".lower()) or str(e).lower().__contains__("ProxyError".lower()):
                error_details = {
                    "error_flag": True, "error_status_code": response_status_code, "error_msg": str(e)
                }

                logging.error(err_msg)
                return response_header, response_content, error_details
            else:
                logging.error(err_msg)
                raise Exception(err_msg)

    @staticmethod
    def get_api_data(request_url, request_header, **kwargs):
        request_method = kwargs.get("request_method", "get")
        request_body_data_json = kwargs.get("request_body_data_json", None)
        request_body_data = kwargs.get("request_body_data", None)
        request_params = kwargs.get("request_params", None)
        request_max_retries = kwargs.get("request_max_retries", 5)
        request_retry_delay_time = kwargs.get("request_retry_delay_time", 120)
        sanitized_request_url = kwargs.get("sanitized_request_url", request_url)  # Print URL in the Log without key
        request_response_decode_flag = kwargs.get("request_response_decode_flag", True)

        response_header, response_output, error_details = CommonAPIUtilities.make_request(
            request_method, request_url, request_header, request_body_data_json=request_body_data_json,
            request_body_data=request_body_data, request_params=request_params)
        retry_count = 1
        while error_details["error_flag"]:
            time.sleep(request_retry_delay_time)
            response_header, response_output, error_details = CommonAPIUtilities.make_request(
                request_method, request_url, request_header, request_body_data_json=request_body_data_json,
                request_body_data=request_body_data, request_params=request_params)

            if retry_count > request_max_retries:
                raise Exception(" After Retries-The server encountered an error processing the request"
                                " request_url: %s, error_status_code:%s, error_msg:%s"
                                % (sanitized_request_url, str(error_details["error_status_code"]),
                                   str(error_details["error_msg"])))
            retry_count = retry_count + 1

        if response_output is None or len(response_output) == 0:
            raise Exception("Response content is empty,request_url: %s response_text: %s"
                            % (sanitized_request_url, response_output))
        try:
            if request_response_decode_flag:
                data = response_output.decode('utf-8')
                data = data.replace("\x00", "")  # NUL char replace
                return data
            else:
                return response_output

        except Exception as e:
            partial_response_output = str(response_output)[0:100] if str(response_output) is not None else None
            err_msg = f"Data/Header to Json conversion issue, Error: {str(e)}," \
                      f"partial_response_output: {str(partial_response_output)}," \
                      f" request_url:{str(sanitized_request_url)}"
            logging.error(err_msg)
            raise Exception(err_msg)


class CommonProcessHelperUtils:

    @staticmethod
    def create_spark_session(spark_app_name, spark_options=None):
        from pyspark.sql import SparkSession
        try:
            config_options = {"spark.task.maxFailures": "1",
                                     "spark.rpc.message.maxSize": "2047"}
            if spark_options is not None:
                config_options.update(spark_options)

            if spark_app_name is None or spark_app_name == "":
                raise Exception(f"Provide Spark App Name: {str(spark_app_name)}")

            from pyspark.conf import SparkConf

            spark_conf = SparkConf().setAll([(k, v) for k, v in config_options.items()])
            spark = SparkSession.builder.appName(spark_app_name).config(conf=spark_conf)\
                .getOrCreate()
            # Set Spark configurations from the dictionary
            return spark
        except Exception as ex:
            raise Exception(f"Exception while creating spark session, Error:{str(ex)}, "
                            f"spark_options:{str(spark_options)}")

    @staticmethod
    def get_credentials(credentials_vendor_key, minio_s3_credentials):

        # *********************************************************************************
        # Reading Job Credentials
        if credentials_vendor_key is not None and credentials_vendor_key != "":
            return CredentialsLoader.get_credentials(credentials_vendor_key, minio_s3_credentials)
        else:
            return None
        # Reading Credentials
        # *********************************************************************************
    @staticmethod
    def ensure_dependencies(sc, project_abspath, s3_bucket, minio_s3_credentials, project_dir_name="project_name"):
      
        # Zip and upload to S3
        zip_file_path = CommonZipHelperUtils.zip_project(project_abspath)

        # Upload to S3 (MinIO)
        s3_key = f"{project_dir_name}/{project_dir_name}.zip"
        s3_bucket  = s3_bucket.strip('/')
        
        zip_s3_file_path = f"s3://{s3_bucket}/{s3_key}"
        
        logging.info(f"Uploaded zip file to: {zip_s3_file_path}")

        s3_client = CommonS3Utilities.MinioS3Client(minio_s3_credentials).minio_s3_client
        
        try:
            s3_client.upload_file(zip_file_path, s3_bucket, s3_key)
        except Exception as e:
            raise Exception( "Exception occurred while uploading project zip file: %s, Error:%s " % (zip_s3_file_path, str(e)))
        sc.addPyFile(f"{zip_s3_file_path}")

    @staticmethod
    def initialize_read_arguments(spark_options=None, spark_context_log_level="INFO", mount_bucket_name="/workflows"):

        spark_app_name = sys.argv[1]
        spark = CommonProcessHelperUtils.create_spark_session(spark_app_name, spark_options)

        sc = spark.sparkContext
        sc.setLogLevel(spark_context_log_level)

        # *********************************************************************************
        # Reading Job args
        hadoop_custom_arguments = json.loads(sc.getConf().get('spark.hadoop.custom.arguments'))

        spark_job_args = hadoop_custom_arguments["spark_job_args"]
        cluster_details_spark_args = hadoop_custom_arguments["cluster_details_spark_args"]

        minio_s3_credentials = cluster_details_spark_args["s3_credentials"]
        vendor_credentials = CommonProcessHelperUtils.get_credentials(spark_job_args.get("credentials_vendor_key"),
                                                                      minio_s3_credentials)
        # Reading Job args
        # *********************************************************************************
 
        # *********************************************************************************
        # Package the project and add to the sc PyFile
        project_dir_name: str =  spark_job_args["project_dir_name"]
        if project_dir_name is None or len(project_dir_name.strip()) == 0:
            logging.error('! project_dir_name is not provided in the spark_job_args. !!!')
            raise Exception('! project_dir_name is not provided in the spark_job_args. !!!')
        project_abspath = os.path.join(mount_bucket_name, spark_job_args["project_dir_name"])
       
        
        CommonProcessHelperUtils.ensure_dependencies(sc=sc
                                                     ,project_abspath=project_abspath
                                                     ,minio_s3_credentials=minio_s3_credentials
                                                     ,s3_bucket=mount_bucket_name
                                                     ,project_dir_name=project_dir_name
                                                     )
        # *********************************************************************************

        return spark, sc, spark_app_name, spark_job_args, cluster_details_spark_args, minio_s3_credentials,\
               vendor_credentials

    @staticmethod
    def validate_source_columns_with_schema(data_record, configured_columns_details):
        data_api_cols = dict(data_record).keys()
        configured_columns_cols = dict(configured_columns_details).keys()

        no_match_cols_list = list(set(data_api_cols).symmetric_difference(set(configured_columns_cols)))

        if len(no_match_cols_list) > 0:
            err_msg = 'Columns not matching error , no_match_cols_list: %s | data_api_cols: %s ' \
                      '| columns_api_cols: %s' % (str(no_match_cols_list),
                                                  str(data_api_cols), str(configured_columns_cols))
            logging.error(err_msg)
            raise Exception(err_msg)
        else:
            logging.info("Columns matched between source data columns and pre-configured columns")

    @staticmethod
    def get_schema_from_s3(s3_schema_file_path, schema_file_object_key, s3_resource):
        data = CommonS3Utilities.read_file_from_s3(s3_resource, s3_schema_file_path,
                                                   CommonS3Utilities.MINIO_S3_PROTOCOL_PREFIX)

        if data is None or data == "":
            config_schema_json = None
        else:
            config_schema_json = json.loads(data)

        config_table_schema = config_schema_json[schema_file_object_key]
        config_table_schema = config_table_schema["schema"]

        return config_table_schema

    def get_schema_from_local(full_schema_file_path, schema_file_object_key ):
        
        local_abspath = "/" + full_schema_file_path.split("://")[1]
        try:
                with open(local_abspath, "r") as f:
                    config_schema_json = json.loads(f.read())

                    config_table_schema = config_schema_json[schema_file_object_key]
                    config_table_schema = config_table_schema["schema"]
                    return config_table_schema
        except Exception as e:
            raise Exception( "Exception occurred while reading Schema Config File: %s, Error:%s " % (local_abspath, str(e)))

    @staticmethod
    def fetch_processed_values_from_db(spark, table_field_name, output_warehouse_fq_table):
        # Fetching last ingested date from DB
        last_incr_filter_df = spark.sql(
            f"select distinct {table_field_name} as incr_filter_value from {output_warehouse_fq_table}").cache()

        db_incr_filter_value_list = last_incr_filter_df.rdd.map(lambda row: row.asDict()).collect()
        db_incr_filter_value_list = [filter_value['incr_filter_value'] for filter_value in db_incr_filter_value_list]

        logging.info("len(db_incr_filter_value_list): %s" % (str(len(db_incr_filter_value_list))))
        return db_incr_filter_value_list

    @staticmethod
    def get_latest_files_list(processed_file_names_list, input_file_paths_list):

        if len(processed_file_names_list) != 0:
            added_file_paths_list = [file_path for file_path in input_file_paths_list if
                                       os.path.basename(file_path) not in processed_file_names_list]

        else:
            logging.info("It might be first run of the job- No values in the processed list")
            added_file_paths_list = input_file_paths_list

        logging.info("Length of new / added file paths list: %s ,"
                     "" % (str(added_file_paths_list)))

        return added_file_paths_list


class CommonBasicUtilities:

    @staticmethod
    def join_prefixes_with_slash(base_uri, prefix_list):

        try:
            # Removing if any "/" character at end
            base_uri = base_uri[0:len(base_uri) - 1] if base_uri[len(base_uri) - 1] == "/" else base_uri

            api_url = base_uri
            for prefix in prefix_list:
                # Removing if any / character at start
                prefix = prefix[1:len(prefix)] if prefix[0] == "/" else prefix
                # Removing if any / character at end
                prefix = prefix[0:len(prefix) - 1] if prefix[len(prefix) - 1] == "/" else prefix
                api_url = api_url + "/" + prefix

            return api_url

        except Exception as e:
            raise Exception("Exception while joining with slashes, Error:%s, base_uri:%s,"
                            " prefix_list:%s" % (str(e), base_uri, prefix_list))

    @staticmethod
    def load_json_data(data):

        if data is None or data == "":
            raise Exception(f"Data is empty or data is None")

        try:
            response_json = json.loads(data)
            return response_json

        except Exception as e:
            partial_response_output = str(data)[0:100] if str(data) is not None else None
            err_msg = f"Data/Header to Json conversion issue, Error: {str(e)}," \
                      f"partial_response_output: {str(partial_response_output)}"
            logging.error(err_msg)
            raise Exception(err_msg)
    @staticmethod
    def check_not_empty(value: str, message: str) -> None:
        if value is None or not value.strip():
            raise ValueError(message)
    @staticmethod
    def isEmpty(arg: str) -> bool:
            if arg is None or (isinstance(arg, (str, list, tuple, dict, set)) and len(arg) == 0):
                return True
            return False


class CommonFileHelperUtils:

    @staticmethod
    def s3_read_data_from_csv(minio_s3_credentials, s3_file_full_path, csv_delimiter):
        s3_resource = CommonS3Utilities.MinioS3Resource(minio_s3_credentials).minio_s3_resource
        try:
            logging.info("Reading the S3 file: %s" % s3_file_full_path)

            text = CommonS3Utilities.read_file_from_s3(s3_resource, s3_file_full_path,
                                                       CommonS3Utilities.MINIO_S3_PROTOCOL_PREFIX)

            csv.register_dialect('MyDialect', skipinitialspace=True, delimiter=csv_delimiter, strict=True)

            reader = csv.DictReader(io.StringIO(text), dialect='MyDialect')
            response_json = json.loads(json.dumps(list(reader)))

            return response_json

        except Exception as e:
            raise Exception("Exception occurred while reading file, Error:%s, "
                            "s3_file_full_path:%s" % (str(e), s3_file_full_path))
class CommonZipHelperUtils:
    @staticmethod
    def extract_project_name(project_abspath):
        # Remove trailing slash if present
        project_abspath = project_abspath.rstrip('/')
        project_name = os.path.basename(project_abspath)
        return project_name

    @staticmethod
    def zip_project(project_abspath):
        import zipfile
        # Zip file name
        zim_package_name = CommonZipHelperUtils.extract_project_name(project_abspath) +".zip"
        # Absolute path to where you want to save the zip file
        zip_file_abspath = os.path.join(project_abspath, zim_package_name)
        logging.info("zip_file_abspath: %s".format( str(zip_file_abspath)))
        # Create a zip file
        try:
            with zipfile.ZipFile(zip_file_abspath, 'w') as zipf:
                for root, dirs, files in os.walk(project_abspath):
                    for file in files:
                        file_path = os.path.join(root, file)
                        zipf.write(file_path, os.path.relpath(file_path, project_abspath))
        except Exception as e:
            raise Exception("Exception occurred while zipping the project, Error:%s" % (str(e)))

        return zip_file_abspath