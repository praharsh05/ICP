
# Pyspark Data Migration Generic Framework

## Table Contents
## Table of Contents
1. [Author(s)](#authors)
2. [Framework Overview](#framework-overview)
3. [Configuration Description](#configuration-description)
   1. [DAG Details](#1-dag-details)
   2. [Airflow Task Dependencies](#2-airflow-task-dependencies)
   3. [Spark Jobs](#3-spark-jobs)
   4. [Airflow Task Args](#4-airflow-task-args)
   5. [Database Details](#5-database-details)
4. [Usage of the Framework](#usage-of-the-framework)
5. [airflow task retries](#airflow-task-retries)
6. [Acknowledgmentss](#acknowledgments)
7. [Reference](#reference)


## Author(s)
- Merhawi Kiflemariam

## Framework Overview
This framework is a scalable, configurable, and automated ETL framework designed for running PySpark jobs on Kubernetes, orchestrated by Apache Airflow. It enables seamless data migration from databases (PostgreSQL, Oracle) to Iceberg tables, ensuring optimal performance through parallel execution, batch processing, and partitioning strategies.

The system provides a template-driven approach, allowing users to define DAGs, configure Spark job parameters, and manage data ingestion with minimal effort. The framework is designed to handle large-scale data processing efficiently while preventing memory issues (OOM) by leveraging dynamic partitioning and batching techniques.

With Airflow DAGs managing execution flow and Kubernetes handling Spark workloads, this framework ensures high availability, fault tolerance, and distributed processing for enterprise-scale ETL workflows. 🚀


## Configuration Description

### 1. DAG Details
- DAG ID: id of the airflow dag like `pyspark_template`
- Description: Description of the project (Optional)

### 2. Airflow Task Dependencies: 
#### Execution Modes: **airflow-task-dependencies-details**
By default, if not provide , it will keep all the tasks run in `Parallel`.

##### A. Sequential Execution
For sequential execution, define:

```
"airflow-task-dependencies-details": {
    "task-auto-dependencies": {
        "trigger_order": "sequential"
    }
}
```
##### B. Parent-Child Relationship

Airflow task Dependencies, Provide as parent-child relationship for every node. Below is just one example of parent-child-relation, but it can be configured in multiple ways.

```
"airflow-task-dependencies-details": {
                                  "parent-child-relation":{
                                    "task1": ["start"],
                                    "task2": ["start"],
                                    "task3": ["task1", "task2"],
                                    "end": ["task3"],
                              } }

```
##### C. Grouping Parallel tasks
Provide Task dependencies to run keep it as `Parallel` with config as number per each group.

```
    "airflow-task-dependencies-details": {
            "task-auto-dependencies":{"trigger_order": "parallel", "max_tasks_per_group": 3}
        }
```



### 3. Spark Jobs

A. `spark_kubernetes_args`  - Config values to submit spark jobs in Kubernetes. If not provided , it will take default values.
 
   * Default values for spark drive and executor resources.
   * Default values for Kubernetes scheduler options.
   * Default Spark job main script.*
   
B. `spark_job_args` - Spark job arguments.
- **project_dir_name**: The must be the project directory name. This is mandatory to package the project and add to spark PyFile so that it will ship the entire project to every executor.
- **output_warehouse_fq_table**: The output table name must be in <catalog>.<schema>.<table> format
- **output_wh_table_load_strategy**: The table load strategy, supported strategies are `Append`, `merge_upsert`,`merge_insert`  and `insert_overwrite`. But as of know, only `append` is rigourosly tested. Default value is `append`.
- **operation_type**: `migration` (optional, default value is `default`).
    - If `migration` is provided, it will migrate data based on db details to destination.
    - If not provided or the value is other than `migration`, it will use default spark data ingestion (it will ingest dummy data)
-  **location**: Location of the iceberg table if new table is needed to create automaticly.
    - Default location:  `s3a://{catalog_minio_bucket}/{table_schema}/{table}`
- **auto_table_creation**: Whethere to create table automatcily if not exist, default is False.
- **python_dependencies_base_paths**: Default python utils path will provide to spark job as dependency if not provided.
`

### 4. Airflow Task Args

Any task argument will be provided under the `task_args` object.
```
"task_args":{
          "trigger_rule":"all_success"
        }
```
#### A. Airflow Trigger Rule (Optional):
> Trigger rules are used to determine when a task should run in relation to the previous task. By default, Airflow runs a task when all directly upstream tasks are successful. However, you can change this behavior using the trigger_rule parameter in the task definition.
> ##### Available trigger rules in Airflow
> The following trigger rules are available:
> - **all_success**: (default) The task runs only when all upstream tasks have succeeded.
>- **all_failed**: The task runs only when all upstream tasks are in a failed or upstream_failed state.
> - **all_done**: The task runs once all upstream tasks are done with their execution.
> - **all_skipped**: The task runs only when all upstream tasks have been skipped.
> - **one_failed**: The task runs when at least one upstream task has failed.
> - one_success: The task runs when at least one upstream task has succeeded.
> **one_done**: The task runs when at least one upstream task has either succeeded or failed.
> - **none_failed**: The task runs only when all upstream tasks have succeeded or been skipped.
> - **none_failed_min_one_success**: The task runs only when all upstream tasks have not failed or upstream_failed, and at least one upstream task has succeeded.
> - **none_skipped**: The task runs only when no upstream task is in a skipped state.
> - **always**: The task runs at any time.


### 5. Database Details

```
"db_details": {
    "url": "jdbc:postgresql://<hostname>:<port>/<db_name",
    "dbtype": "postgres",
    "user": "<username>",
    "password": "<password>",
    "db_table": "<table_name>",
    "partitioning_column": "id",
    "lower_bound": 0,
    "upper_bound": 3000000,
    "num_partitions": 4,
    "selected_columns": ["emp_id", "date", "status"],
    "is_col_for_partition_null_supp": false,
    "records_per_batch": 100000
}

```

#### Key Parameters
   - **url**: JDBC connection string.
   - **dbtype**: type of database.
   - **user**: username.
   - **password**: password.
   - **db_table**: The name of the table in the database that you want to migrate.
   - **partitioning_column**: The column used for partitioning the data during the migration (must be a column with numerical, date or timestamp values).
   - **lower_bound**: The minimum value in the partitioning column to start from. Supported datatypes are int,float,date,timesamp, default is int.
   - **upper_bound**: The maximum value in the partitioning column to end at. Supported datatypes are int,float,date,timesamp, default is int.
   - **num_partitions**: The number of partitions to divide the dataset into.
   - **selected_columns**: A list of the columns that need to be selected during the migration.
   - **is_col_for_partition_null_supp**: A boolean flag that determines whether null values in the partitioning column should be included. If set to true, records with null values in the partitioning column will also be loaded.
   - **records_per_batch**: The number of records to be included in each batch when reading data.

**Oracle DB:**

If the database is oracle, please use the below format or value
- **url**: jdbc:oracle:thin:@<hostname>:<port>/<dbname>
- **dbtype**: oracle

**MS SQL Server DB:**
If the database is mssql, please use the below format or value
- **url**: jdbc:sqlserver://<hostname>:<port>;databaseName=<dbname>
- **dbtype**: mssql

**Default Constants:**
Some of the parameters have default values that can be overridden by providing them in the configuration. These default values are specified in the **Constants** class:
```
class Constants:
    DEFAULT_RECORDS_PER_BATCH = 100000
    DEFAULT_NUMBER_OF_PARTITIONS = 1
    DEFAULT_LOWER_BOUND = 0
    DEFAULT_UPPER_BOUND = DEFAULT_RECORDS_PER_BATCH
    DEFAULT_IS_COL_FOR_PARTITION_NULL_SUPP = False
```

#### Partitioning Strategy and Batch Processing
**1. Why Partitioning**
>Spark JDBC reader is capable of reading data in parallel by splitting it into several partitions. There are four options provided by DataFrameReader:

> - **partitionColumn** is the name of the column used for partitioning. An important condition is that the column must be numeric (integer or decimal), date or timestamp type. If the partitionColumn parameter is not specified, Spark will use a single executor and create one non-empty partition. Reading data will not be distributed or parallelized.
> - **numPartitions** is the maximum number of partitions that can be used for simultaneous table reading and writing.
> - **lowerBound** and **upperBound** boundaries are used to define the partition width. These boundaries determines how many rows from a given range of partition column values can be within a single partition.

Partitioning improves performance by allowing Spark to distribute data processing across multiple executors, enabling parallel execution and reducing overall runtime. However, partitioning alone may not be sufficient for handling large datasets efficiently.


**2. Big Data Source Problem**

Although partitioning distributes the load across executors, it can still lead to ```Out of Memory (OOM)``` issues when handling extremely large tables. If the dataset is too large for the available memory, partitioning alone is not enough. This is where batching comes into play.


**3. What is Batching?**

Batching allows data to be read in multiple smaller batches instead of processing everything at once.

**4. Why is Batch Processing Important?**
- ✅ **Minimizes memory consumption** – Large tables may not fit into memory at once. Reading in smaller batches avoids memory overflow.
- ✅ **Improves performance** – Distributes workload efficiently across executors by processing smaller chunks.
- ✅ **Reduces I/O overhead** – Helps optimize disk read/write operations and network bandwidth usage.

**5. How Batching Works?**
- The full data range is split into N batches using a fixed records_per_batch size.
- The last batch may contain slightly more or fewer records than the defined batch size, depending on total row count.
- Each batch is further ```partitioned and distributed across executors```, ensuring parallel execution within each batch.
- This two-layered optimization (**batching + partitioning**) ensures efficient and scalable data processing, even when working with massive datasets.


**Example**
Assuming we have a table ```my_table``` with a numeric column ``id`` used for partitioning, and user provides the following configurations:

Configuration:
- records per batch: 200_000
- Partition Column: id
- Num of Partitions: 2
- Lower Bound: 0
- Upper Bound: 1_000_000

**Batch Calculation:**
Number of batches = Upper Bound / Records per batch = 1,000,000 / 200,000 = 5

List of Batches = `[(0,200_000 - 1), (200_000,400_000 - 1), (400_000,600_000 - 1), (600_000,800_000 - 1), (800_000, 1_000_000)]`

Each batch will execute against the database one by one. However, since partitioning is enabled, each batch will be divided into` Num of Partitions`, which will run in parallel.
**Batch Execution:**
**1st Batch (id range: 0 - 199,999):**
- **Partition 1:** `SELECT * FROM my_table WHERE id >= 0 AND id <= 99_999;` -> Executor 1
- **Parition 2:** `SELECT * FROM my_table WHERE id >= 100_000 AND id <= 199_999;` -> Executor 2

**2nd Batch:**
- **Parition 1:** `SELECT * FROM my_table WHERE id >= 200_000 AND id <= 299_999;`
- **Parition 2:** `SELECT * FROM my_table WHERE id >= 300_000 AND id <= 399_999;`
....

**5th Batch:**
- **Parition 1:** `SELECT * FROM my_table WHERE id >= 800_000 AND id <= 899_999;`
- **Parition 2:** `SELECT * FROM my_table WHERE id >= 900_000 AND id <= 1_000_000;`

**Note:**

- **If `partitioning_column` is not provided or None/empty, no batching or partitioning will happen.**
- **No record below `lower_bound` and beyond `upper_bound` will be selected. If user want to include null values for the `partitioning_column`, `is_col_for_partition_null_supp` must be set to ``True``**

## Usage of the Framework:

1.  Config json file (Directory <project_name>\config)
  a. Make sure all the above mandatory [configs](#configuration-description) are provided. And add the `dag_id` value to the `AIRFLOW_PIPELINES` of airflow environment variable - add at least the below to `AIRFLOW_PIPELINES`:
    "<dag_id>": {
       "catalog": <catalog_name>
    }
2. Dag flows file (Directory: <project_name>\flows\)
   a.  make sure config file name and dag file name should be same except extension.
            
           config file: aspect_pipeline.json
           dag file   : aspect_pipeline.py
3. Script file (Directory: <project_name>\scripts\)
    a. Put the script (spark code) file under this folder, and make sure the `pyspark_job_main_file_s3_path` variable in the config file is updated accordingly.
    ```
    pyspark_job_main_file_s3_path": "s3a://workflows/<project_name>/scripts/<script_file>.py",
    ```
4. Upload the entire project on minio under `/workflows`. 
5. Go to the airflow and search the dag using `dag_id` provided in the config - it might take 1-3 minutes to appear on airflow.
6. Start the dag - If everything configured well and the `operation_type` is not `migration`, at least it should create new table (if not exist) and ingest the dammy data.

7. In all cases - `migration` or `default`(ingesting dummy data), if the provided table is not availabe in the catalog and `auto_table_creation` is `True`, the framework will create table based on the dataframe columns and respective datatypes.

8. If table exist, the framework will get the table description and cast the dataframe datatype against corrosponding columns from the table.

9. If any issue faced for the `migration`, try to debug as per the airflow log. **Remember this framework is generic, you can customize the script file as per your need.**


## airflow task retries:

1. Provide retries and retry_delay at dag level (to `AIRFLOW_PIPELINES`) as below , retry_delay in seconds. Default from Airflow is 300 seconds.
        "<dag_id>": {
        "start_date": "2023-07-25 00:00:00", 
        "schedule_interval": "30 4 * * *", 
        "tags":["<dag_id>", "..."], 
        "retries": 2, 
        "retry_delay": 900 
    }
2. If not provided them at dag level as in above step-1, it will consider from `AIRFLOW_DAG_DEFAULT_ARGS`
       {
        "max_active_runs": 1,
         "retries": 1,
        }
3. If values are not available in above both steps, kept default values.
    "retries": 1
    "retry_delay": it takes airflow default value

4. If start_date is not provided in the dag level, it will take a default value 30 days back from the current time, when the job is runing.
   

## Acknowledgments
- Special thanks to Hemanth Bommireddy for the original framework, which served as the foundation for this project.

## Reference:

https://luminousmen.com/post/spark-tips-optimizing-jdbc-data-source-reads

https://www.astronomer.io/docs/learn/airflow-trigger-rules/
