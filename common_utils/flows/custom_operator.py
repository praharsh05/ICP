import logging
from airflow.providers.cncf.kubernetes.operators.spark_kubernetes import SparkKubernetesOperator
from airflow.providers.cncf.kubernetes.sensors.spark_kubernetes import SparkKubernetesSensor
from airflow.utils.decorators import apply_defaults
from airflow.models import BaseOperator

# Creating custom Airflow spark Kubernetes operator to handle both submit and monitor
# ******************************************************************************************************


class CustomSparkKubernetesSubmitMonitor(BaseOperator):
    @apply_defaults
    def __init__(self, spark_kubernetes_operator_args, spark_kubernetes_sensor_args, global_vars, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.spark_kubernetes_operator_args = spark_kubernetes_operator_args
        self.spark_kubernetes_sensor_args = spark_kubernetes_sensor_args
        self.global_vars = global_vars

    def execute(self, context):
        spark_operator = SparkKubernetesOperator(task_id='spark-submit-task', **self.spark_kubernetes_operator_args)
        kubernetes_sensor = SparkKubernetesSensor(task_id='spark-monitor-task', **self.spark_kubernetes_sensor_args)
        try:
            spark_operator.execute(context)

        except Exception as e:
            if str(e).__contains__("AlreadyExists"):
                logging.warning("Spark Submit - Job already exists:%s" % str(e))
            else:
                logging.error("Spark Submit issue:%s" % str(e.with_traceback()))

                # Inserting Error info to Trino
                # self.insert_trino(context.get("task_instance").dag_id, context.get("task_instance").task_id, str(e))
                raise e

        try:
            kubernetes_sensor.execute(context)

        except Exception as e:
            logging.error("Spark Monitor issue:%s" % str(e))

            # *******
            # Inserting Error info to Trino
            # self.insert_trino(context.get("task_instance").dag_id, context.get("task_instance").task_id, str(e))
            raise e

    # ******************************************************************************************************
    # ******************************************************************************************************
    # Inserting error info to trino
    def insert_trino(self, dag_id, task_id, log_error_info):
        from datetime import datetime
        import re
        now = datetime.now()
        ingested_at = datetime.strptime(now.strftime("%Y-%m-%d %H:%M:%S"), "%Y-%m-%d %H:%M:%S")

        trino_statement = "INSERT INTO {} VALUES" \
                          " ('{}','{}', '{}', timestamp  '{}')".format(self.global_vars["airflow_error_details_table"],
                                                                       dag_id, task_id, log_error_info, ingested_at)

        try:
            from airflow.providers.trino.hooks.trino import TrinoHook
            trino_conn = TrinoHook(self.global_vars["trino_airflow_connections"]["datalake"])
            print(trino_conn)
            cursor = trino_conn.get_cursor()
            cursor.execute(trino_statement)
            response = cursor.fetchone()
            if response:
                print('> Error Details table insert has been completed successfully')
        except Exception as e:
            print('> Execution Failed')
            raise Exception(e, trino_statement)


# ******************************************************************************************************
# ******************************************************************************************************

