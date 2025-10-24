from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago
from airflow.models import Variable # module to import the variables

default_args = {"owner":"ds","retries":0}

with DAG(
    dag_id="familytree_pipeline",
    start_date=days_ago(1),
    schedule_interval=None,
    catchup=False,
    default_args=default_args
) as dag:

    dedup = BashOperator(
        task_id="dedup_entities",
        bash_command="spark-submit /digixt/spark/jobs/dedup_entity_builder.py"
    )

    links = BashOperator(
        task_id="build_links",
        bash_command="spark-submit /digixt/spark/jobs/parent_spouse_link_builder.py"
    )

    ego = BashOperator(
        task_id="ego3_cache",
        bash_command="spark-submit /digixt/spark/jobs/ego3_cache_builder.py --person_ids_path s3://digixt-lake/tmp/changed_person_ids.txt --lang en --depth 3"
    )

    dedup >> links >> ego
