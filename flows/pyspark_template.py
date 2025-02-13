import os
from airflow import DAG
# TODO: this is added to help airflow detect common_utils as module
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__) + '/../'))
print("path : {}".format(os.path.dirname(__file__) + '/../'))

from common_utils.flows import common_dag_module


# **************************  basic details  **************************************
local_workflows_config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                           'config',
                                           os.path.basename(os.path.abspath(__file__)).replace(".py", ".json"))

pipeline_zone = ""
# **********************************************************************************


airflow_var_globals, airflow_var_pipelines, dag_default_args = \
    common_dag_module.DagCommons.read_airflow_variables(pipeline_zone)


configs, airflow_var_dag_details, dag_arguments = \
    common_dag_module.DagCommons.read_dag_details(local_workflows_config_path,
                                                  airflow_var_pipelines, dag_default_args, airflow_var_globals)

# DAG building task groups
with DAG(**dag_arguments) as dag:
    common_dag_module.DagCommons.build_task_group(dag, configs, airflow_var_globals, airflow_var_dag_details)