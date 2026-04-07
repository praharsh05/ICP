import sys
import boto3
import re
import time
from botocore.config import Config
from botocore.exceptions import ClientError
import shutil
import os

# Custom Dependencies
from common_utils.scripts import common_utilities
from common_utils.scripts.common_utilities import CommonLogging
logging = CommonLogging.get_logger()
# ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** *****


class CommonS3Utilities:

    MINIO_S3_PROTOCOL_PREFIX = "s3a://"
    AWS_S3_PROTOCOL_PREFIX = "s3://"

    @common_utilities.singleton
    class AwsS3Session:
        def __init__(self, aws_s3_credentials):
            s3_client_config = Config(region_name=aws_s3_credentials["s3_region"], proxies={
                'http': os.environ.get("https_proxy"), 'https': os.environ.get("https_proxy")
            }, proxies_config={"proxy_ca_bundle": os.environ.get("REQUESTS_CA_BUNDLE")})

            self.aws_s3_client = boto3.client('s3', config=s3_client_config,
                                              aws_access_key_id=aws_s3_credentials["s3_access_key"],
                                              aws_secret_access_key=aws_s3_credentials["s3_secret_access_key"],
                                              verify=os.environ.get("REQUESTS_CA_BUNDLE"))

    @common_utilities.singleton
    class MinioS3Client:
        def __init__(self, minio_s3_credentials):
            self.minio_s3_client = boto3.client(
                's3',
                endpoint_url=minio_s3_credentials["s3_host"],
                aws_access_key_id=minio_s3_credentials["s3_access_key"],
                aws_secret_access_key=minio_s3_credentials["s3_secret_access_key"],
                config=Config(signature_version=minio_s3_credentials["s3_signature_version"]),
                region_name=minio_s3_credentials["s3_region"],
                # verify=True
                verify=os.getenv('REQUESTS_CA_BUNDLE', True)
            )

    @common_utilities.singleton
    class MinioS3Resource:
        def __init__(self, minio_s3_credentials):
            self.minio_s3_resource = boto3.resource(
                's3',
                endpoint_url=minio_s3_credentials["s3_host"],
                aws_access_key_id=minio_s3_credentials["s3_access_key"],
                aws_secret_access_key=minio_s3_credentials["s3_secret_access_key"],
                config=Config(signature_version=minio_s3_credentials["s3_signature_version"]),
                region_name=minio_s3_credentials["s3_region"],
                verify=os.getenv('REQUESTS_CA_BUNDLE', True)
            )

    @staticmethod
    def ls_objects_from_s3(s3_client, s3_full_path, s3_protocol_prefix):
        s3_bucket = ""
        s3_path_prefix = ""
        try:
            s3_bucket, s3_path_prefix = CommonS3Utilities.get_s3_bucket_and_prefix_from_path(
                s3_full_path, s3_protocol_prefix)

            paginator = s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=s3_bucket, Prefix=s3_path_prefix)
            s3_objects_list = []
            for page in pages:
                try:
                    for obj in page['Contents']:
                        s3_objects_list.append("{}{}/".format(s3_protocol_prefix, s3_bucket) + obj['Key'])

                        # if s3_incremental_flag:
                        #
                        #     # Filtering files by modified date
                        #     if obj['LastModified'].date() == (datetime.now().date():
                        #         s3_objects_list.append("{}{}/".format(s3_protocol_prefix, s3_bucket) + obj['Key'])
                        #
                        #     # Filtering files by file name which contains prior date
                        #     # prior_date = str((datetime.now() - timedelta(days=1)).date())
                        #     # if obj['Key'].__contains__(prior_date):
                        #     #     s3_objects_list.append("{}{}/".format(s3_protocol_prefix, s3_bucket) + obj['Key'])
                        #
                        # else:
                        #     s3_objects_list.append("{}{}/".format(s3_protocol_prefix, s3_bucket) + obj['Key'])
                except KeyError as e:
                    logging.warning("No files are available in the path, S3_path:%s" % s3_full_path)

            s3_files_list = [s3_object for s3_object in s3_objects_list if s3_object[-1] != '/']

            logging.info("len(s3_objects_list): %s" % (str(len(s3_objects_list))))

            logging.info("len(s3_files_list): %s" % (str(len(s3_objects_list))))

            return s3_files_list

        except Exception as e:
            raise Exception("Exception occurred while listing files from S3 path, Error:%s ,s3_bucket:%s, "
                            "s3_path_prefix:%s" % (str(e), s3_bucket, s3_path_prefix))

    # ##########################################################################################
    @staticmethod
    def create_pre_signed_url(s3_client, s3_bucket, s3_prefix, expiration=180):

        try:
            pre_signed_url = s3_client.generate_presigned_url('get_object',
                                                              Params={'Bucket': s3_bucket,
                                                                          'Key': s3_prefix
                                                                      },
                                                              ExpiresIn=expiration
                                                              )
        except ClientError as e:
            logging.error(e)
            raise Exception(e)

        # The response contains the pre_signed URL
        return pre_signed_url

    @staticmethod
    def read_file_from_s3(s3_resource, s3_full_path, s3_protocol_prefix):

        try:
            s3_bucket, s3_path_prefix = CommonS3Utilities.get_s3_bucket_and_prefix_from_path(s3_full_path,
                                                                                             s3_protocol_prefix)

            print(f"{s3_bucket}, {s3_path_prefix}")
            response = s3_resource.Object(s3_bucket, s3_path_prefix)
            data = response.get()['Body'].read().decode('utf-8')

            return data
        except Exception as e:
            raise Exception("Exception occurred while reading Config File, Error:%s, s3_full_path: %s"
                             % (str(e), s3_full_path))

    @staticmethod
    def s3_write_file(s3_resource, data_bytes, s3_full_path, s3_protocol_prefix):

        s3_bucket, s3_path_prefix = CommonS3Utilities.get_s3_bucket_and_prefix_from_path(s3_full_path,
                                                                                         s3_protocol_prefix)

        logging.info(">> >> >> s3_bucket:%s, s3_prefix:%s" % (s3_bucket, s3_path_prefix))

        try:
            s3_object = s3_resource.Object(s3_bucket, s3_path_prefix)

            s3_object.put(Body=data_bytes)
        except Exception as e:
            raise Exception("Exception occurred while writing File, Error:%s ,s3_bucket:%s, "
                            "s3_path_prefix:%s" % (str(e), s3_bucket, s3_path_prefix))

    # **********Downloading file with Boto3 download********************************
    @staticmethod
    def s3_download_file(s3_resource, s3_full_path, local_temp_dir_base_path, s3_protocol_prefix):

        try:
            s3_bucket, s3_path_prefix = CommonS3Utilities.get_s3_bucket_and_prefix_from_path(s3_full_path,
                                                                                             s3_protocol_prefix)
            s3_bucket_obj = s3_resource.Bucket(s3_bucket)

            path, filename = os.path.split(s3_path_prefix)
            local_temp_dir_path = os.path.join(local_temp_dir_base_path, path)

            if not os.path.exists(local_temp_dir_path):
                os.makedirs(local_temp_dir_path)
            else:
                shutil.rmtree(local_temp_dir_path)
                os.makedirs(local_temp_dir_path)

            local_temp_file_path = os.path.join(local_temp_dir_path, filename)
            s3_bucket_obj.download_file(s3_path_prefix, local_temp_file_path)
            return local_temp_file_path

        except Exception as e:

            raise Exception("Exception occurred while downloading files from S3 path, Error:%s, s3_full_path:%s, "
                            "local_temp_dir_base_path:%s" % (str(e), s3_full_path, local_temp_dir_base_path))

    @staticmethod
    def s3_upload_file(s3_client, local_temp_file_path,
                       local_temp_dir_base_path, s3_base_path, s3_protocol_prefix):
        try:
            s3_path_prefix = os.path.relpath(local_temp_file_path, local_temp_dir_base_path)
            s3_full_path = os.path.join(s3_base_path, s3_path_prefix)

            s3_bucket, s3_path_prefix = CommonS3Utilities.get_s3_bucket_and_prefix_from_path(
                s3_full_path, s3_protocol_prefix)

            s3_client.upload_file(local_temp_file_path, s3_bucket, s3_path_prefix)

        except Exception as e:
            raise Exception("Exception occurred while uploading file from local path, Error:%s, "
                            "local_temp_file_path:%s, s3_base_path:%s" % (str(e), local_temp_file_path, s3_base_path))

    @staticmethod
    def s3_move_file(s3_source_file_full_path, s3_target_file_full_path, s3_resource,  s3_protocol_prefix):

        try:
            s3_source_bucket, s3_source_file_path_prefix = CommonS3Utilities.get_s3_bucket_and_prefix_from_path(
                s3_source_file_full_path, s3_protocol_prefix)

            s3_target_bucket, s3_target_file_path_prefix = CommonS3Utilities.get_s3_bucket_and_prefix_from_path(
                s3_target_file_full_path, s3_protocol_prefix)

            for obj in s3_resource.Bucket(s3_source_bucket).objects.filter(Prefix=s3_source_file_path_prefix):
                copy_source = {'Bucket': s3_source_bucket, 'Key': obj.key}
                new_obj_key = obj.key.replace(s3_source_file_path_prefix, s3_target_file_path_prefix)
                new_obj = s3_resource.Bucket(s3_target_bucket).Object(new_obj_key)
                new_obj.copy(copy_source)
                obj.delete()

        except Exception as e:
            raise Exception("Exception occurred while moving File, Error:%s, "
                            "s3_file_full_path:%s" % (str(e), s3_source_file_full_path))

    @staticmethod
    def s3_move_files_pending_to_processed(s3_file_full_path_list, s3_resource,  s3_protocol_prefix):

        for s3_file_full_path in s3_file_full_path_list:

            try:

                CommonS3Utilities.s3_move_file(s3_file_full_path,
                                               s3_file_full_path.replace('/pending/', '/processed/'),
                                               s3_resource, s3_protocol_prefix)
            except Exception as e:
                raise Exception("Exception occurred while moving File, Error:%s, "
                                "s3_file_full_path:%s" % (str(e), s3_file_full_path))

    @staticmethod
    def get_s3_bucket_and_prefix_from_path(s3_full_path, s3_protocol_prefix):

        s3_bucket, s3_path_prefix = s3_full_path.replace(s3_protocol_prefix, "").split("/", 1)
        return s3_bucket, s3_path_prefix

