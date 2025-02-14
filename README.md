**Author(s)** 
- Hemanth Bommireddy
- MerhawiKiflemariam

Common DAG Module:
-----------------
**aiflow-task-dependencies-details**

1. By default, if we don't provide , it will keep all the tasks run in Parallel.
2. Airflow task Dependencies, Provide as parent-child relationship for every node.
             "aiflow-task-dependencies-details": {
                                  "parent-child-relation":{
                                       "task1": ["predecessor", "successor"],
                                      "task2": ["predecessor", "successor"],
                              } }

3. Airflow task dependencies - Provide Task dependencies to run keep it as sequential.  
                     "aiflow-task-dependencies-details": {
                                 "task-auto-dependencies":{"trigger_order": "sequential"}
                              } 
4. Airflow task dependencies - Provide Task dependencies to run keep it as Parallel with config as number per each group.  
   a. trigger_rule is "all_done" means id all predecessors is just completed , then successor will trigger irrespective of success or failure.
                        "aiflow-task-dependencies-details": {
                                    "task-auto-dependencies":{"trigger_order": "parallel", "max_tasks_per_group": 3, "trigger_rule":  "all_done"}
                                 }
                              


Spark Jobs:
-----------
1. "spark_kubernetes_args"  - Config values to submit spark jobs in Kubernetes. If we dont' provide , it will take default values.
 
   * Default values for spark drive and executor resources.
   * Default values for Kubernetes scheduler options.
   * Default Spark job main script.
   
2. "spark_job_args" - Spark job arguments.
   * "python_dependencies_base_paths" - Default python utils path will provide to spark job as dependency if we don't provide.
   * "project_dir_name" - The must be the project directory name. This is mandatory to package the project and add to spark PyFile so that it will ship the entire project to every 
   executor.
   
  *    
    
Usage of the Airflow Pipelines:
-------------------------------

1.  Config Json file (Directory: <project_name>\config\)
  a. Currently, pipelines are executing all sql files through Trino and Using "python details". 
  b. Provide airflow task name and target_table name for python operator. It will find the transform.sql path based on directory structure.
  c. Provide "aiflow-task-dependencies-details" accordingly. if not provided, it will keep all tasks as default configured.

2. Dag file/ flows file (Directory: <project_name>\flows\)
   a. create a new dag file , make sure config file name and dag file name should be same except extension.
            
           config file: aspect_pipeline.json
           dag file   : aspect_pipeline.py
   b. Follow the existing directory structure for to keep <project_name>.sql files.
      
          <project_name>/scripts/sql/<project_name>.sql
          <project_name>/scripts/sql/<project_name>.sql


Aiflow task retries:
--------------------

1. Provide retries and retry_delay at dag level as below , retry_delay in seconds. Default from Airflow is 300 seconds.
        "pyspark_template": {
        "start_date": "2023-07-25 00:00:00", 
        "schedule_interval": "30 4 * * *", 
        "tags":["pyspark_template", "template"], 
        "retries": 2, 
        "retry_delay": 900 
    }
2. If we don't provide them at dag level as in above step-1, it will consider from "AIRFLOW_DAG_DEFAULT_ARGS"
       {
        "max_active_runs": 1,
         "retries": 1,
        }
3. If values are not available in above both steps, kept default values.
    "retries": 1
    "retry_delay": it takes airflow default value

4. If start_date is not provided in the dag level, it will take a default value 30 days back from the current time, when the job is runing.
   

Airflow Dataset Trigger 
-----------------------

1. Parent DAG - Add a flag in airflow variable (DAG level) to track dataset outlet.
      "parent-dag-name": {
           "start_date": "2023-07-01 00:00:00",
           "schedule_interval": "00 02 * * *",
           "dataset_outlet_flag": true,
           "tags": []
       }
      
2. Child DAG - Update DAG schedule from Schedule interval to Schedule_dataset.

    "child-dag-name": {
          "start_date": "2023-10-16 00:00:00",
          "schedule_dataset": ["parent-dag-name"],
          "tags": []
       }



Database Details
----------------
```
"db_details": {
    "db_properties" : {
        "url": "jdbc:postgresql://<hostname>:<port>/<db_name",
        "dbtype": "postgres",
        "user": "<username>",
        "password": "<password>"
    },
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


**Key Parameters:**
   - **db_properties**: A dictionary that includes the necessary properties to connect to the database, including url (JDBC connection string), dbtype (type of database), user (username), and password (password).
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

**Partitioning Strategy and Batch Processing**
-------------------------------------------------
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

**Reference**
------------------
https://luminousmen.com/post/spark-tips-optimizing-jdbc-data-source-reads
