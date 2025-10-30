from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago
from datetime import timedelta

default_args = {
    "owner": "dataeng",
    "retries": 2,
    "retry_delay": timedelta(minutes=5)
}

with DAG(
    dag_id="residents_familytree_pipeline",
    start_date=days_ago(1),
    schedule_interval="0 3 * * *",
    catchup=False,
    default_args=default_args,
    tags=["family_tree", "residents", "production"]
) as dag:

    dedup = BashOperator(
        task_id="dedup_entities",
        bash_command="spark-submit --master yarn --deploy-mode cluster "
                     "/digixt/spark/jobs/residents_dedup_entity_builder.py"
    )

    links = BashOperator(
        task_id="build_sponsorship_links",
        bash_command="spark-submit --master yarn --deploy-mode cluster "
                     "/digixt/spark/jobs/residents_link_builder.py"
    )

    ego_cache = BashOperator(
        task_id="ego3_cache",
        bash_command="spark-submit --master yarn --deploy-mode cluster "
                     "/digixt/spark/jobs/residents_ego3_cache_builder.py"
    )

    load_neo4j = BashOperator(
        task_id="load_neo4j",
        bash_command="python /digixt/scripts/load_residents_to_neo4j.py"
    )

    dedup >> links >> ego_cache >> load_neo4j
