import logging
import yaml
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from yaml.loader import SafeLoader

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s', level=logging.INFO, datefmt='%y/%m/%d %H:%M:%S')

logging = logging.getLogger()

creds_bucket = 'system'
creds_path = '/config/cr.yaml'


class CredentialsLoader:
    creds_file = None

    def __init__(self):
        pass
    
    ## S3
    @staticmethod
    def get_s3_client(s3_credentials):
        s3_host = s3_credentials['s3_host']
        s3_access_key = s3_credentials['s3_access_key']
        s3_secret_access_key = s3_credentials['s3_secret_access_key']

        s3 = boto3.resource(
            's3',
            endpoint_url=s3_host,
            aws_access_key_id=s3_access_key,
            aws_secret_access_key=s3_secret_access_key,
            config=Config(signature_version='s3v4'),
            region_name='us-east-1'
        )
        return s3
        
    @staticmethod
    def get_s3_file(bucket, object_name, s3_credentials):
        try:
            s3 = CredentialsLoader.get_s3_client(s3_credentials)
            obj = s3.Bucket(bucket).Object(object_name)
            data = obj.get()['Body'].read().decode('utf-8')
            return data
        except ClientError as e:
            print(e)
        return None

    @staticmethod
    def get_credentials(vendor_name, s3_credentials=None, mounted_path=None):
        if CredentialsLoader.creds_file is None:
            if s3_credentials:
                CredentialsLoader.creds_file = CredentialsLoader.get_s3_file(creds_bucket, creds_path, s3_credentials)
            else:
                with open(mounted_path, 'r') as file:
                    CredentialsLoader.creds_file = file.read()

        try:
            credentials = yaml.load(CredentialsLoader.creds_file, Loader=SafeLoader)
            return credentials[vendor_name]

        except yaml.scanner.ScannerError as sc:
            print(f'!!! YAML is not readable. Problem clue: {sc.problem}')
            print(f'!!! For more troubleshooting, take the file and try to load it manually in localhost.')
            raise Exception('!!! Impossible to proceed without credentials!!!')
        except Exception:
            print('!!! YAML is not readable. Please check if it is well formatted!')
            raise Exception('!!! Impossible to proceed without credentials!!!')
