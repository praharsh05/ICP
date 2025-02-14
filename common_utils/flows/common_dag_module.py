from datetime import datetime, timedelta
from airflow.models import Variable
from airflow.operators.dummy import DummyOperator as DummyOperator
from airflow.operators.python import PythonOperator
from airflow.utils.task_group import TaskGroup
from airflow.datasets import Dataset
import yaml


class Constants:
    DIR_AIRFLOW_DAG_ENV = "/opt/airflow/dags"
    DIR_AIRFLOW_LOG_ENV = "/opt/airflow/logs"
    S3_PROTOCOL_PREFIX = "s3a://"
    AIRFLOW_TRIGGER_ALL_SUCCESS = "all_success"
    # TODO: DEFAULT_AIRFLOW_HTTPS_PROXY is added for testing
    DEFAULT_AIRFLOW_HTTPS_PROXY = ""
    # provide default list of dependencies list
    # TODO: DEFAULT_IMPORT_STATEMENTS_LIST is empty
    DEFAULT_IMPORT_STATEMENTS_LIST = ""
    # DEFAULT_IMPORT_STATEMENTS_LIST = [f"from transformed.common_utils.dependencies.scripts import common_utilities"]
    # Provide default Python operator callable
      # TODO: DEFAULT_PYTHON_CALLABLE is empty
    DEFAULT_PYTHON_CALLABLE = ""
    # DEFAULT_PYTHON_CALLABLE = "common_utilities.ProcessorUtils.main_trino_process"

    # provide default Spark main script S3 path
    # TODO: DEFAULT_PYSPARK_JOB_MAIN_FILE_S3_PATH is empty since starter is provided under root_project/scripts/
    DEFAULT_PYSPARK_JOB_MAIN_FILE_S3_PATH = ""
   
    # Provide comma separated local paths of Spark (Mounted works volume)
    # TODO: DEFAULT_PYSPARK_DEPENDENCIES_LOCAL_PATH is empty 
    DEFAULT_PYSPARK_DEPENDENCIES_LOCAL_PATH = ""
    

class KubernetesSparkSetup:

    # ***** ***** Pyspark Kubernetes Initialization ***** ***** ***** *****

    @staticmethod
    def handle_min_resources(spark_kubernetes_job_args):
        driver_cores = spark_kubernetes_job_args["driver_cores"]
        executor_cores = spark_kubernetes_job_args["executor_cores"]
        driver_memory = str(spark_kubernetes_job_args["driver_memory"])
        executor_memory = str(spark_kubernetes_job_args["executor_memory"])
        executor_instances = spark_kubernetes_job_args["executor_instances"]

        if str(driver_memory).__contains__("g"):
            d_memory = int(driver_memory.split("g")[0]) * 1024
        elif str(driver_memory).__contains__("m"):
            d_memory = int(driver_memory.split("m")[0])
        else:
            raise Exception("Provide driver_memory in as suffix as 'g' or 'm'")

        if str(executor_memory).__contains__("g"):
            e_memory = int(executor_memory.split("g")[0]) * 1024
        elif str(executor_memory).__contains__("m"):
            e_memory = int(executor_memory.split("m")[0])
        else:
            raise Exception("Provide executor_memory in as suffix as 'g' or 'm'")

        min_cores = str(driver_cores + (executor_instances * executor_cores))
        min_memory = str(d_memory + (executor_instances * e_memory)) + "m"

        return min_cores, min_memory

    @staticmethod
    def create_cluster_details_spark_args(airflow_var_globals, airflow_var_dag_details):
        cluster_details_spark_args = {
            "s3_credentials": {
                "s3_host": airflow_var_globals["s3_host"],
                 "s3_access_key": airflow_var_globals["s3_access_key"],
                "s3_secret_access_key": airflow_var_globals["s3_secret_access_key"],
                "s3_region": airflow_var_globals["s3_region"],
                "s3_signature_version": airflow_var_globals["s3_signature_version"]
            },
             "https_proxy": airflow_var_globals.get("https_proxy", Constants.DEFAULT_AIRFLOW_HTTPS_PROXY),
            "catalog": airflow_var_dag_details.get("catalog", None),
            "catalog_minio_bucket": airflow_var_globals["buckets"][
                airflow_var_dag_details["catalog"]] if airflow_var_dag_details.get("catalog",
                                                                                   None) is not None else None,
            "global_vars": airflow_var_globals,
             "airflow_var_dag_details": airflow_var_dag_details
        }

        return cluster_details_spark_args

    @staticmethod
    def update_default_values_spark_kubernetes_job_args(spark_kubernetes_job_args):
        # Spark code language
        if 'spark_language' not in spark_kubernetes_job_args:
            spark_kubernetes_job_args['spark_language'] = 'python'

        # Spark volcano scheduler default property
        if 'volcano_job_priority' not in spark_kubernetes_job_args:
            spark_kubernetes_job_args['volcano_job_priority'] = 'routine'

        # Spark driver resources
        if 'driver_cores' not in spark_kubernetes_job_args:
            spark_kubernetes_job_args['driver_cores'] = 1
        if 'driver_memory' not in spark_kubernetes_job_args:
            spark_kubernetes_job_args['driver_memory'] = '1g'

        # Spark Executor resources
        if 'executor_instances' not in spark_kubernetes_job_args:
            spark_kubernetes_job_args['executor_instances'] = 1
        if 'executor_cores' not in spark_kubernetes_job_args:
            spark_kubernetes_job_args['executor_cores'] = 1
        if 'executor_memory' not in spark_kubernetes_job_args:
            spark_kubernetes_job_args['executor_memory'] = '1g'

        if 'spark_dependencies_libraries' not in spark_kubernetes_job_args:
            spark_kubernetes_job_args['spark_dependencies_libraries'] = ""

        if "pyspark_job_main_file_s3_path" not in spark_kubernetes_job_args:
            spark_kubernetes_job_args["pyspark_job_main_file_s3_path"] = Constants.DEFAULT_PYSPARK_JOB_MAIN_FILE_S3_PATH

        return spark_kubernetes_job_args

    @staticmethod
    def update_default_values_spark_job_args(spark_job_args):
        if "python_dependencies_base_paths" not in spark_job_args:
            spark_job_args["python_dependencies_base_paths"] = Constants.DEFAULT_PYSPARK_DEPENDENCIES_LOCAL_PATH

        return spark_job_args
     
    @staticmethod
    def build_k8s_pyspark_configuration(spark_app_name, spark_kubernetes_job_args, spark_job_args, airflow_var_globals,
                                        airflow_var_dag_details, job_arguments=[]):
        import json

        # Update default values for Spark job submission on Kubernetes
        spark_kubernetes_job_args = KubernetesSparkSetup.\
            update_default_values_spark_kubernetes_job_args(spark_kubernetes_job_args)

        # Update default values for Spark job Arguments
        spark_job_args = KubernetesSparkSetup.\
            update_default_values_spark_job_args(spark_job_args)

        spark_language = spark_kubernetes_job_args['spark_language'].lower()

        cluster_details_spark_args = KubernetesSparkSetup.create_cluster_details_spark_args(airflow_var_globals,
                                                                                            airflow_var_dag_details)
        hadoop_custom_arguments = {
            "spark_job_args": spark_job_args, "cluster_details_spark_args": cluster_details_spark_args
        }
        # TODO: below is added to make the catalog and it's bucket dynamic
        catalog = cluster_details_spark_args["catalog"] if cluster_details_spark_args["catalog"] else None
        catalog_minio_bucket = cluster_details_spark_args["catalog_minio_bucket"] if cluster_details_spark_args["catalog_minio_bucket"] else None

        hadoop_custom_arguments["spark_job_args"]['catalog_minio_bucket'] = catalog_minio_bucket

        k8s_configuration = {
            "apiVersion": "sparkoperator.k8s.io/v1beta2", "kind": "SparkApplication", "metadata": {
                "name": spark_app_name, "namespace": airflow_var_globals["k8s_namespace"],
                "labels": {"app": "spark-jobs"}
            }, "spec": {

                # "deps": {

                # "pyFiles": [
                # "https: "
                # ]
                # },

                "type": "Scala" if spark_language == 'scala' else 'Python',
                 "mode": "cluster",
                "image": airflow_var_globals["spark_image"] if spark_language == 'scala' else airflow_var_globals["pyspark_image"],
                "imagePullPolicy": "IfNotPresent", #make it Always if needed 
                "mainApplicationFile": spark_kubernetes_job_args["pyspark_job_main_file_s3_path"],
                "arguments": job_arguments, "sparkVersion": airflow_var_globals["spark_version"],
                "batchScheduler": "volcano",
                "batchSchedulerOptions": {
                    "priorityClassName": spark_kubernetes_job_args['volcano_job_priority'],
                    # routine for normal , rush for priority jobs
                    # "minMember": 55,
                    "resources": {
                        "cpu": KubernetesSparkSetup.handle_min_resources(spark_kubernetes_job_args)[0],
                        "memory": KubernetesSparkSetup.handle_min_resources(spark_kubernetes_job_args)[1]
                    }
                }, "restartPolicy": {
                    "type": "Never"
                }, "timeToLiveSeconds": airflow_var_globals["k8s_pod_ttl"],

                "volumes": [
                        {
                            "name": airflow_var_globals["volume_details"]["volumes_name"],
                            "persistentVolumeClaim": {
                                "claimName": airflow_var_globals["volume_details"]["volumes_claim_name"]
                                }
                        }
                        ,
                        {
                            "name": airflow_var_globals["volume_details"]["ca_bundle_volume_name"],
                            "configMap": {
                                "name": airflow_var_globals["volume_details"]["ca_bundle_volume_name"],
                                "items": [
                                    {
                                        "key": f"{airflow_var_globals['volume_details']['ca_bundle_volume_name']}.crt",
                                        "path": airflow_var_globals["volume_details"]["ca_bundle_volume_mount_sub_path"]
                                    }
                                ]
                            }
                        },
                        {
                            "name": airflow_var_globals["volume_details"]["key_store_volume_name"],
                            "configMap": {
                                "name": airflow_var_globals["volume_details"]["ca_bundle_volume_name"],
                                "items": [
                                    {
                                        "key":  airflow_var_globals["volume_details"]["key_store_volume_mount_sub_path"],
                                        "path":  airflow_var_globals["volume_details"]["key_store_volume_mount_sub_path"]
                                    }
                                ]
                            }
                        }


                ],
                "driver": {
                    "cores": spark_kubernetes_job_args["driver_cores"],  # "coreLimit": "1200m",
                    "coreLimit": str(spark_kubernetes_job_args["driver_cores"]),
                    "memory": spark_kubernetes_job_args["driver_memory"], "labels": {"version": "3.1.1"},
                    "serviceAccount": airflow_var_globals["k8s_service_account"],

                    "volumeMounts": [{
                        "mountPath": airflow_var_globals["volume_details"]["volume_mounts_mount_path"],
                        "name": airflow_var_globals["volume_details"]["volume_mounts_name"]
                    }
                      ,  

                    {
                        "mountPath": airflow_var_globals["volume_details"]["ca_bundle_volume_mount_path"],
                        "subPath": airflow_var_globals["volume_details"]["ca_bundle_volume_mount_sub_path"],
                        "name": airflow_var_globals["volume_details"]["ca_bundle_volume_name"]
                    }, {
                            "mountPath": airflow_var_globals["volume_details"]["key_store_volume_mount_path"],
                            "subPath": airflow_var_globals["volume_details"]["key_store_volume_mount_sub_path"],
                            "name": airflow_var_globals["volume_details"]["key_store_volume_name"]
                        }
                    ],
                     "envVars": {
                       "JAVA_OPTS": f"$JAVA_OPTS -Djavax.net.ssl.trustStore= {airflow_var_globals['volume_details']['key_store_volume_mount_path']}",
                        "REQUESTS_CA_BUNDLE": airflow_var_globals["volume_details"]["ca_bundle_volume_mount_path"]

                    }
                    

                },

                "executor": {
                    "instances": spark_kubernetes_job_args["executor_instances"],
                    "cores": spark_kubernetes_job_args["executor_cores"],
                    "coreLimit": str(spark_kubernetes_job_args["executor_cores"]),
                    "memory": spark_kubernetes_job_args["executor_memory"], "labels": {"version": "3.1.1"},
                    "volumeMounts": [
                        {
                        "mountPath": airflow_var_globals["volume_details"]["volume_mounts_mount_path"],
                        "name": airflow_var_globals["volume_details"]["volume_mounts_name"]
                    }
                    ,  

                    {
                        "mountPath": airflow_var_globals["volume_details"]["ca_bundle_volume_mount_path"],
                        "subPath": airflow_var_globals["volume_details"]["ca_bundle_volume_mount_sub_path"],
                        "name": airflow_var_globals["volume_details"]["ca_bundle_volume_name"]
                    }, {
                            "mountPath": airflow_var_globals["volume_details"]["key_store_volume_mount_path"],
                            "subPath": airflow_var_globals["volume_details"]["key_store_volume_mount_sub_path"],
                            "name": airflow_var_globals["volume_details"]["key_store_volume_name"]
                        }
                    ],
                     "envVars": {
                       "JAVA_OPTS": f"$JAVA_OPTS -Djavax.net.ssl.trustStore= {airflow_var_globals['volume_details']['key_store_volume_mount_path']}",
                        "REQUESTS_CA_BUNDLE": airflow_var_globals["volume_details"]["ca_bundle_volume_mount_path"]

                    }

                }, "sparkConf": {
                    "spark.hadoop.custom.arguments": json.dumps(hadoop_custom_arguments, default=str),
                    "spark.sql.extensions": "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions",
                    "spark.sql.catalog.spark_catalog": "org.apache.iceberg.spark.SparkSessionCatalog",
                    "spark.sql.catalog.spark_catalog.type": "hive",
                    "spark.sql.catalog.{}".format(catalog): "org.apache.iceberg.spark.SparkSessionCatalog",
                    "spark.sql.catalog.{}.uri".format(catalog): airflow_var_globals["metastores"]["{}".format(catalog)],
                    "spark.sql.iceberg.handle-timestamp-without-timezone": "true",
                     "spark.eventLog.enabled": "true",
                    "spark.history.fs.logDirectory": airflow_var_globals["s3_spark_logging_path"],
                    "spark.eventLog.dir": airflow_var_globals["s3_spark_logging_path"],
                    "spark.hadoop.fs.s3a.endpoint": airflow_var_globals["s3_host"],
                    "spark.hadoop.fs.s3a.access.key": airflow_var_globals["s3_access_key"],
                    "spark.hadoop.fs.s3a.secret.key": airflow_var_globals["s3_secret_access_key"],
                    "spark.hadoop.fs.s3a.connection.ssl.enabled": "true",
                    "spark.hadoop.fs.s3a.path.style.access": "true",
                    "spark.executor.extraClassPath": spark_kubernetes_job_args["spark_dependencies_libraries"],
                    "spark.driver.extraClassPath": spark_kubernetes_job_args["spark_dependencies_libraries"],
                    "spark.sql.parquet.fs.optimized.committer.optimization-enabled": "true",
                    "spark.hadoop.fs.s3a.connection.maximum": "100",
                    "spark.ui.proxyRedirectUri": airflow_var_globals["spark_ui_proxy_redirect_uri"]
                    
                }
            }
        }
        #TODO:
        print(f"This is the catalog result: {catalog}")
     
        return k8s_configuration


class BuildDagTaskGroup:
    @staticmethod
    def get_task_args_details(task_args={}):
        task_args_details = {}
        trigger_rule = task_args.get("trigger_rule", "all_success")
        
        task_args_details['trigger_rule'] = trigger_rule

        return task_args_details
    @staticmethod
    def build_spark_details(dag, task_group_key, task_details_key, airflow_task_details, airflow_var_globals,
                            airflow_var_dag_details, common_arguments):
        # Custom spark operator import
        from common_utils.flows.custom_operator import CustomSparkKubernetesSubmitMonitor
        airflow_tasks_list = []
        spark_kubernetes_args = airflow_task_details[task_group_key][task_details_key].get("spark_kubernetes_args", {})
        spark_job_args = airflow_task_details[task_group_key][task_details_key].get("spark_job_args", {})
        task_args_details = BuildDagTaskGroup.get_task_args_details(airflow_task_details[task_group_key].get("task_args", {}))

        # Adding Common Arguments to Spark Arguments
        for common_args_key in common_arguments.keys():
            if common_args_key not in spark_job_args.keys():
                spark_job_args[common_args_key] = common_arguments[common_args_key]

        # ********* getting meta store details *********************************************

        spark_submit_application_config = KubernetesSparkSetup.build_k8s_pyspark_configuration(
            "{}".format(task_group_key), spark_kubernetes_args, spark_job_args, airflow_var_globals,
            airflow_var_dag_details,
            job_arguments=["{}".format(task_group_key)])
        app_file  = yaml.dump(spark_submit_application_config)
        spark_kubernetes_operator_args = {
            "namespace": airflow_var_globals["k8s_namespace"],
            "kubernetes_conn_id": airflow_var_globals["k8s_connection_id"],
            "application_file": app_file
        }
        spark_kubernetes_sensor_args = {
            "namespace": airflow_var_globals["k8s_namespace"],
            "kubernetes_conn_id": airflow_var_globals["k8s_connection_id"],
            "application_name": task_group_key, "attach_log": True
        }
        spark_job = CustomSparkKubernetesSubmitMonitor(task_id="{}".format(task_group_key),
                                                       spark_kubernetes_operator_args=spark_kubernetes_operator_args,
                                                       spark_kubernetes_sensor_args=spark_kubernetes_sensor_args,
                                                       global_vars=airflow_var_globals,
                                                       dag=dag,
                                                       trigger_rule=task_args_details['trigger_rule']
                                                       )
        airflow_tasks_list.append(spark_job)

        return airflow_tasks_list
    



    @staticmethod
    def build_python_details(dag, task_group_key, task_details_key, airflow_task_details, global_vars,
                             airflow_var_dag_details):

        python_callable_args = airflow_task_details[task_group_key][task_details_key]
        import_statements_list = python_callable_args.get("import_statements_list",
                                                          Constants.DEFAULT_IMPORT_STATEMENTS_LIST)
        python_callable = python_callable_args.get("python_callable", Constants.DEFAULT_PYTHON_CALLABLE)

        common_arguments = {"DIR_AIRFLOW_DAG_ENV": Constants.DIR_AIRFLOW_DAG_ENV}

        import importlib

        for import_statement in import_statements_list:
            try:
                exec(import_statement)
            except Exception as e:
                print(f"Error Executing Import import_statement - {import_statement}: {e}")

        airflow_tasks_list = []

        python_task = PythonOperator(task_id=task_group_key,
                                     python_callable=eval(python_callable),
                                     op_args=[python_callable_args, global_vars, airflow_var_dag_details,
                                              common_arguments],
                                     dag=dag)

        airflow_tasks_list.append(python_task)
        return airflow_tasks_list


class DagCommons:

    @staticmethod
    def format_boolean_value(boolean_value, default_value):
        if boolean_value is not None and isinstance(boolean_value, bool) and boolean_value is False:
            task_status_mail_flag = False
        elif boolean_value is not None and isinstance(boolean_value, bool) and boolean_value is True:
            task_status_mail_flag = True
        else:
            task_status_mail_flag = default_value
        return task_status_mail_flag

    @staticmethod
    def read_airflow_variables(pipeline_zone):
        airflow_var_globals = Variable.get("GLOBALS", deserialize_json=True)

        if pipeline_zone is None or pipeline_zone == "":
            airflow_variable_suffix = ""
        else:
            airflow_variable_suffix = f"_{pipeline_zone.upper()}"

        airflow_var_pipelines = Variable.get(f"AIRFLOW_PIPELINES{airflow_variable_suffix}",
                                             deserialize_json=True)

        dag_default_args = Variable.get(f"AIRFLOW_DAG_DEFAULT_ARGS{airflow_variable_suffix}",
                                        deserialize_json=True)

        return airflow_var_globals, airflow_var_pipelines, dag_default_args

    @staticmethod
    def read_config_from_local(local_workflows_config_path):
        import json
        try:
            with open(local_workflows_config_path, "r") as f:
                configurations = json.loads(f.read())

            return configurations
        except Exception as e:
            raise Exception(
                "Exception occurred while reading Config File: %s, Error:%s " % (local_workflows_config_path, str(e)))

    @staticmethod
    def update_task_retries_and_retry_delay(airflow_var_dag_details, dag_default_args):

        retries_dict = {}
        if "retries" in airflow_var_dag_details and airflow_var_dag_details["retries"] != "" and \
                airflow_var_dag_details["retries"] is not None:

            dag_default_args["retries"] = airflow_var_dag_details["retries"]

        elif "retries" not in dag_default_args:
            dag_default_args["retries"] = 1

        if "retry_delay" in airflow_var_dag_details and airflow_var_dag_details["retry_delay"] != "" and \
                airflow_var_dag_details["retry_delay"] is not None:

            retries_dict["retry_delay"] = timedelta(minutes=airflow_var_dag_details["retry_delay"])

        # retry_delay default value is 5 minutes and if we pass it as variable, then it will be in seconds = 900
        return dag_default_args

    # @staticmethod
    # def update_task_mail_alerts(airflow_var_dag_details, dag_default_args, airflow_var_globals):

    #     task_status_mail_flag = DagCommons.format_boolean_value(airflow_var_dag_details.get("task_status_mail_flag"),
    #                                                             True)

    #     if task_status_mail_flag:

    #         from common_utils.flows.email_alert_notification import EmailAlert
    #         on_failure_callback = EmailAlert.on_failure_callback(dag_default_args.get('email_to'),
    #                                                              airflow_var_globals.get('airflow_url'))
    #         on_retry_callback = EmailAlert.on_retry_callback(dag_default_args.get('email_to'),
    #                                                          airflow_var_globals.get('airflow_url'))
    #         on_success_callback = EmailAlert.on_success_callback(dag_default_args.get('email_to'),
    #                                                              airflow_var_globals.get('airflow_url'))

    #         dag_default_args.update({'on_failure_callback': on_failure_callback})
    #         dag_default_args.update({'on_retry_callback': on_retry_callback})
    #         dag_default_args.update({'on_success_callback': on_success_callback})

    #     return dag_default_args

    # Handle Dag Arguments
    @staticmethod
    def generate_dag_arguments(airflow_dag_details_from_config, airflow_var_dag_details, dag_default_args):
        dag_arguments = {
            "dag_id": airflow_dag_details_from_config["dag_id"],  # "default_args": {'max_active_runs': 1},
            "default_args": dag_default_args,
            "description": airflow_dag_details_from_config.get("dag_description", ""),
            "schedule_interval": airflow_var_dag_details.get("schedule_interval", None),
            "start_date": airflow_var_dag_details["start_date"],
            "catchup": False,
            "tags": airflow_var_dag_details.get("tags", None)
        }
        return dag_arguments

    @staticmethod
    def update_airflow_dag_schedule_details(airflow_var_dag_details):
        schedule_interval = airflow_var_dag_details.get("schedule_interval", None)
        if schedule_interval == "":
            airflow_var_dag_details["schedule_interval"] = None
        else:
            airflow_var_dag_details["schedule_interval"] = schedule_interval

        start_date = airflow_var_dag_details.get("start_date", "")

        if start_date == "" or start_date is None:
            now = datetime.now() - timedelta(days=30)
            airflow_var_dag_details["start_date"] = datetime.strptime(now.strftime("%Y-%m-%d %H:%M:%S"),
                                                                      "%Y-%m-%d %H:%M:%S")
        else:
            airflow_var_dag_details["start_date"] = datetime.strptime(str(start_date), "%Y-%m-%d %H:%M:%S")

        return airflow_var_dag_details

    #  Not using currently , will use after refactoring the code
    @staticmethod
    def read_dag_details(workflows_config_path, airflow_var_pipelines, dag_default_args, airflow_var_globals):
        # Calling common dag module and building the task group

        configs = DagCommons.read_config_from_local(workflows_config_path)

        airflow_dag_details_from_config = dict(configs["aiflow-dag-details"])

        airflow_var_dag_details = airflow_var_pipelines.get(airflow_dag_details_from_config["dag_id"], {})

        airflow_var_dag_details = DagCommons.update_airflow_dag_schedule_details(airflow_var_dag_details)

        # Get airflow DAG Retries
        dag_default_args = DagCommons.update_task_retries_and_retry_delay(airflow_var_dag_details, dag_default_args)
        # TODO: update_task_mail_alerts connected out temporarly 
        # dag_default_args = DagCommons.update_task_mail_alerts(airflow_var_dag_details, dag_default_args,
                                                            #   airflow_var_globals)

        dag_arguments = DagCommons.generate_dag_arguments(airflow_dag_details_from_config, airflow_var_dag_details,
                                                          dag_default_args)

        return configs, airflow_var_dag_details, dag_arguments

    @staticmethod
    def build_task_group(dag, configs, airflow_var_globals, airflow_var_dag_details):
        # ***** *****  Reading Job configuration parameters ***** ***** ***** *****

        airflow_task_details = configs["airflow-task-details"]
        aiflow_task_dependencies_details = configs.get("aiflow-task-dependencies-details", {})
        common_arguments = configs.get("common-arguments", {})

        airflow_tasks_groups_list = []
        for task_group_key in airflow_task_details.keys():

            tasks_list = []

            for task_details_key in airflow_task_details[task_group_key].keys():
                # ########################### Spark tasks ##########################
                if task_details_key == "spark_details":
                    tasks_list = BuildDagTaskGroup.build_spark_details(dag, task_group_key, task_details_key,
                                                                       airflow_task_details, airflow_var_globals,
                                                                       airflow_var_dag_details, common_arguments)

                elif task_details_key == "python_details":
                    tasks_list = BuildDagTaskGroup.build_python_details(dag, task_group_key, task_details_key,
                                                                        airflow_task_details, airflow_var_globals,
                                                                        airflow_var_dag_details)

            if len(tasks_list) > 1:
                with TaskGroup(group_id=task_group_key) as tg:
                    # Building task dependencies inside task group (sequential)
                    for j in range(0, len(tasks_list)):
                        if j != 0:
                            tasks_list[j].set_upstream(tasks_list[j - 1])

                    airflow_tasks_groups_list.append((tg, task_group_key))
            else:
                for task in tasks_list:
                    airflow_tasks_groups_list.append((task, task_group_key))

        DagCommons.build_task_dependencies(dag, airflow_tasks_groups_list, aiflow_task_dependencies_details,
                                           airflow_var_dag_details)

    @staticmethod
    def build_task_dependencies(dag, airflow_tasks_groups_list, aiflow_task_dependencies_details,
                                airflow_var_dag_details):
        all_nodes_list = []
        dependency_tuples_list = []
        added_nodes_dict = {}

        all_nodes_list.extend(airflow_tasks_groups_list)

        dataset_outlet_flag = DagCommons.format_boolean_value(airflow_var_dag_details.get("dataset_outlet_flag"), False)
        end_outlets_kwargs = {"outlets": [Dataset(str(dag.dag_id))] if dataset_outlet_flag else {}}

        if "start" not in dag.tasks:
            task = DummyOperator(task_id="start", dag=dag)
            all_nodes_list.insert(0, (task, "start"))
            added_nodes_dict["start"] = task

        if "end" not in dag.tasks:
            # Data set triggers at end task
            task = DummyOperator(task_id="end", dag=dag, **end_outlets_kwargs)
            all_nodes_list.append((task, "end"))
            added_nodes_dict["end"] = task

        functional_nodes_count = len(airflow_tasks_groups_list)
        functional_nodes_list = airflow_tasks_groups_list

        def build_sequential_dependencies():

            for i in range(0, len(all_nodes_list) - 1):
                current_node = all_nodes_list[i][0]
                next_node = all_nodes_list[i + 1][0]
                dependency_tuples_list.append((current_node, next_node))

        def build_parallel_dependencies(task_auto_dependencies={}):

            max_tasks_per_group = task_auto_dependencies.get("max_tasks_per_group",
                                                             functional_nodes_count)
            trigger_rule = task_auto_dependencies.get("trigger_rule", "all_success")

            # Generating dummy nodes
            group_nodes_dict = {}

            group_no_list = []
            for i in range(0, functional_nodes_count):

                group_no = int(i / max_tasks_per_group)
                if group_no not in group_no_list and group_no < int((functional_nodes_count - 1) / max_tasks_per_group):
                    group_nodes_dict[f"I{group_no + 1}"] = DummyOperator(task_id=f"I{group_no + 1}", dag=dag,
                                                                         trigger_rule=trigger_rule)
                    group_no_list.append(group_no)

            # Building relationship
            for i in range(0, len(functional_nodes_list)):
                current_node = functional_nodes_list[i][0]

                group_no = int(i / max_tasks_per_group)

                if group_no == 0:
                    predecessor_node = added_nodes_dict["start"]
                else:
                    predecessor_node = group_nodes_dict[f"I{group_no}"]

                if group_no < int((functional_nodes_count - 1) / max_tasks_per_group):
                    successor_node = group_nodes_dict[f"I{group_no + 1}"]
                else:
                    successor_node = added_nodes_dict[f"end"]

                dependency_tuples_list.append((predecessor_node, current_node))
                dependency_tuples_list.append((current_node, successor_node))

        def build_parent_child_dependencies():
            config_task_names_list = []

            # for task_name in aiflow_task_parent_child_dependencies.keys():
            #     config_task_names_list.append(task_name)
            #     config_task_names_list.append(aiflow_task_parent_child_dependencies[task_name][0])
            #     config_task_names_list.append(aiflow_task_parent_child_dependencies[task_name][1])

            # config_task_names_list = [*set(config_task_names_list)]

            # TODO
            # for task_name in config_task_names_list:
            #     if task_name not in dag.tasks:
            #         all_nodes_list.append((DummyOperator(task_id=task_name, dag=dag), task_name))

            # for config_current_task_name in aiflow_task_parent_child_dependencies.keys():
            #     current_node = next(node[0] for node in all_nodes_list if node[1] == config_current_task_name)
            #     predecessor_node = next(node[0] for node in all_nodes_list if
            #                             node[1] == aiflow_task_parent_child_dependencies[config_current_task_name][0])
            #     successor_node = next(node[0] for node in all_nodes_list if
            #                           node[1] == aiflow_task_parent_child_dependencies[config_current_task_name][1])

            #     dependency_tuples_list.append((predecessor_node, current_node))
            #     dependency_tuples_list.append((current_node, successor_node))

            for child_task, parent_tasks in aiflow_task_parent_child_dependencies.items():
                child_node = next(node[0] for node in all_nodes_list if node[1] == child_task)

                for parent_task in parent_tasks:
                    parent_node = next(node[0] for node in all_nodes_list if node[1] == parent_task)
                    dependency_tuples_list.append((parent_node, child_node))

        # Build dependencies as per configuration
        if aiflow_task_dependencies_details:
            if "parent-child-relation" in aiflow_task_dependencies_details:
                aiflow_task_parent_child_dependencies = aiflow_task_dependencies_details["parent-child-relation"]
                build_parent_child_dependencies()

            elif "task-auto-dependencies" in aiflow_task_dependencies_details:
                task_auto_dependencies = aiflow_task_dependencies_details["task-auto-dependencies"]
                if "trigger_order" in task_auto_dependencies and \
                        task_auto_dependencies["trigger_order"].lower() == "sequential":
                    build_sequential_dependencies()
                else:
                    build_parallel_dependencies(task_auto_dependencies)
        # Build dependencies between tasks as sequential (if we don't provide any preconfigured)
        else:
            build_parallel_dependencies()

        for predecessor, successor in dependency_tuples_list:
            predecessor >> successor
