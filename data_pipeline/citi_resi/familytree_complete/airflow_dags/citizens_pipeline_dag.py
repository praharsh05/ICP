from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago
from datetime import timedelta

default_args = {
    "owner": "xpin",
    "retries": 2,
    "retry_delay": timedelta(minutes=5)
}

with DAG(
    dag_id="citizens_familytree_pipeline",
    start_date=days_ago(1),
    catchup=False,
    default_args=default_args,
    tags=["family_tree", "citizens", "PoC"]
) as dag:

    dedup = BashOperator(
        task_id="dedup_entities",
        bash_command="spark-submit --master yarn --deploy-mode cluster "
                     "/digixt/spark/jobs/citizens_dedup_entity_builder.py"
    )

    links = BashOperator(
        task_id="build_links",
        bash_command="spark-submit --master yarn --deploy-mode cluster "
                     "/digixt/spark/jobs/citizens_link_builder.py"
    )

    ego_cache = BashOperator(
        task_id="ego3_cache",
        bash_command="spark-submit --master yarn --deploy-mode cluster "
                     "/digixt/spark/jobs/citizens_ego3_cache_builder.py"
    )

    load_neo4j = BashOperator(
        task_id="load_neo4j",
        bash_command="python /digixt/scripts/load_citizens_to_neo4j.py"
    )

    dedup >> links >> ego_cache >> load_neo4j
