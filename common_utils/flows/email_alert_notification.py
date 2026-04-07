from datetime import timedelta, datetime
from airflow import DAG
from airflow.operators.dummy import DummyOperator
from airflow.operators.python_operator import PythonOperator
from airflow.providers.cncf.kubernetes.operators.spark_kubernetes import SparkKubernetesOperator
from airflow.providers.cncf.kubernetes.sensors.spark_kubernetes import SparkKubernetesSensor
from airflow.utils.task_group import TaskGroup
from botocore.client import Config
from airflow.exceptions import AirflowSkipException
from airflow.providers.trino.hooks.trino import TrinoHook
from airflow.models import Variable
from airflow.utils.dates import days_ago
from botocore.exceptions import ClientError
from time import time
import logging as log
import json
import boto3
import requests
import re
from airflow.operators.email_operator import EmailOperator
from airflow.utils.email import send_email
import datetime
from datetime import datetime
import jinja2
import os
import logging
from airflow.providers.postgres.operators.postgres import PostgresOperator 
from airflow.providers.postgres.hooks.postgres import PostgresHook
import airflow
from packaging import version

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s', level=logging.INFO, datefmt='%y/%m/%d %H:%M:%S')

logging = logging.getLogger()

DIR_AIRFLOW_DAG_ENV = "/opt/airflow/dags"
DIR_AIRFLOW_LOG_ENV = "/opt/airflow/logs"
        
class EmailAlert:
    @staticmethod
    
    def on_failure_callback(email_to,airflow_url): 
        
        def send_failure_alert(context):
            global_vars = Variable.get("GLOBALS", deserialize_json=True)
            env_name=global_vars["env_name"]
            log_url=airflow_url + "/log" + context.get("task_instance").log_url.split("/log")[1]
    
            title = "<Lakehouse-{}> Airflow Alert: {} DAG Failed".format(env_name,context.get("task_instance").dag_id)
            body = """    Dear Team, <br>    <br>    Failed Task Name: {}. <br>    <br>     Please check the below mentioned url. <br>    <br>     Airflow Job Url: <a href={}>{}</a>  """.format(context.get("task_instance").task_id,log_url,log_url)
            send_email(email_to,title,body)
            
        return send_failure_alert

    def on_success_callback(email_to,airflow_url):
        
        def send_success_alert(context):
    
            title = "DEV DataLake Airflow Alert: {} DAG Succeeded".format(context.get("task_instance").dag_id)
            body = """    Dear Team, <br>    <br>    {} - All the Task are executed successfully. <br>    <br>  """.format(context.get("task_instance").dag_id)
            send_email(email_to,title,body)
        return send_success_alert 