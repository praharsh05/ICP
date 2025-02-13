
from abc import ABC, abstractmethod
from pyspark.sql import SparkSession
from pyspark.sql.dataframe import DataFrame
from typing import Union

from common_utils.scripts.helper.common_helper_utilities import CommonBasicUtilities
from common_utils.scripts.common_utilities import CommonLogging

logging = CommonLogging.get_logger()
class BaseDBOperations(ABC):
    

    def __init__(self, db_properties: dict,  spark: SparkSession):
        self._db_properties = db_properties
        self._spark = spark
        self.validate_db_properties()

    @abstractmethod
    def get_driver(self) -> str:
        pass

    def validate_db_properties(self):
        required_keys = ["url", "user", "password"]
        for key in required_keys:
            CommonBasicUtilities.check_not_empty(self._db_properties.get(key), f"{key} is required in db_properties")

    def build_select_query(self, table_name: str, column_names: str = "*", where_clause: str = "", orderby_clause: str = "",
                 limit: int = None, offset: int = 0, column_for_partitioning: str = None) -> str:
        
        CommonBasicUtilities.check_not_empty(table_name, "Table name cannot be null or empty")
        offset = offset if not None else 0

        query = f"SELECT "
        if (CommonBasicUtilities.isEmpty(column_names) or column_names.strip() == "*"):
            query +="*"
        else:
            query += column_names
        query += f" FROM {table_name}"
        isAndNeeded = True if not CommonBasicUtilities.isEmpty(column_for_partitioning) and not CommonBasicUtilities.isEmpty(where_clause) else False
        if not CommonBasicUtilities.isEmpty(where_clause):
            query += f" WHERE {where_clause}"
        elif not CommonBasicUtilities.isEmpty(column_for_partitioning):
             query += f" WHERE"
        if isAndNeeded:
             query += " AND"
        if not CommonBasicUtilities.isEmpty(column_for_partitioning):
            query += f" {column_for_partitioning} >=  {offset}"
            if limit is not None:
                query += f" {column_for_partitioning} < {offset + limit}"

        if CommonBasicUtilities.isEmpty(column_for_partitioning) and not CommonBasicUtilities.isEmpty(orderby_clause) :
            query += f" ORDER BY {orderby_clause}"
        
        if CommonBasicUtilities.isEmpty(column_for_partitioning):
            if limit is not None:
                query += f" LIMIT {limit}"
            if offset > 0:
                query += f" OFFSET {offset}"

        return query
      
        
    def read_data(self, table_name: str, column_names: str = "*", where_clause: str = "", orderby_clause: str = "",
                  limit: int = None, offset: int = None, column_for_partitioning: str = None,
                  query: str = None, lower_bound: Union[str, int] = None,
                  upper_bound: Union[str, int] = None, num_partitions: int = None) -> DataFrame:
        """
        """
        if query:
            # Use the provided query directly
            return self._read_data(query)
        elif not CommonBasicUtilities.isEmpty(column_for_partitioning) and lower_bound is not None and upper_bound is not None and num_partitions is not None:
            # Handle partitioning logic
            return self._read_data(table_name=table_name, column=column_for_partitioning, lower_bound=lower_bound, 
                                    upper_bound=upper_bound, num_partitions=num_partitions, column_names=column_names)
        else:
            # Default to pagination logic
            query = self.build_select_query(table_name, column_names, where_clause, orderby_clause,
                                     limit, offset, column_for_partitioning)
            return self._read_data(query=query)


    def _read_data(self, query: str = None, table_name: str = None, column: str = None,
                   lower_bound: Union[str, int] = None, upper_bound: Union[str, int] = None,
                   num_partitions: int = None, column_names: str=None) -> DataFrame:
        """
        Reads data from the database using either a custom query or partitioning parameters.
        """
        if query:
            # If query is provided, use it directly
            logging.info("Query -> {}".format(query))
            return self._spark.read.format("jdbc") \
                .option("url", self._db_properties["url"]) \
                .option("dbtable", f"({query})  subquery") \
                .option("user", self._db_properties["user"]) \
                .option("password", self._db_properties["password"]) \
                .option("driver", self.get_driver()) \
                .load()
        elif table_name and column and lower_bound is not None and upper_bound is not None and num_partitions is not None:
            # If table name and partitioning parameters are provided, use them
            if CommonBasicUtilities.isEmpty(column_names):
                column_names = "*"
            query  = f"(select {column_names} from {table_name} where {column} >= {lower_bound} and {column} <= {upper_bound}) query"
            logging.info("Query -> {}".format(query))
            return self._spark.read.format("jdbc") \
                .option("url", self._db_properties["url"]) \
                .option("dbtable", query) \
                .option("partitionColumn", column) \
                .option("lowerBound", lower_bound) \
                .option("upperBound", upper_bound) \
                .option("numPartitions", num_partitions) \
                .option("user", self._db_properties["user"]) \
                .option("password", self._db_properties["password"]) \
                .option("driver", self.get_driver()) \
                .load()
        else:
            raise ValueError("Invalid parameters. Provide either a query or table name with partitioning details.")

    def write_data(self, df: DataFrame, table_name: str, mode: str = "error") -> None:

        df.write.format("jdbc") \
            .option("url", self._db_properties["url"]) \
            .option("dbtable", table_name) \
            .option("user", self._db_properties["user"]) \
            .option("password", self._db_properties["password"]) \
            .option("driver", self.get_driver()) \
            .mode(f"{mode}") \
            .save()

class PostgreSqlDBOperations(BaseDBOperations):
    DRIVER_CONSTANT = "org.postgresql.Driver"

    def __init__(self, db_properties: dict, spark: SparkSession):
        super().__init__(db_properties, spark)
   
    def get_driver(self) -> str:
        return self.DRIVER_CONSTANT

class OracleDBOperations(BaseDBOperations):
    DRIVER_CONSTANT = "oracle.jdbc.OracleDriver"

    def __init__(self, db_properties: dict, spark: SparkSession):
        super().__init__(db_properties, spark)

    def get_driver(self) -> str:
        return self.DRIVER_CONSTANT
    # override method
    def build_select_query(self, table_name: str, column_names: str = "*", where_clause: str = "", orderby_clause: str = "", 
                limit: int = None, offset: int = 0, column_for_partitioning: str = None) -> str:
        
        """ SELECT * FROM (
                 SELECT a.*, ROWNUM rnum FROM (
                     SELECT * FROM employees [WHERE whereclause | range using column_for_partitioning] ORDER BY employee_id
                 ) a WHERE ROWNUM <= 20
             ) WHERE rnum > 10;
             if column_for_partitioning is empty or null and limit or offset are not none, use the ROWNUM using nestead query
             otherwise use range_query ... column_for_partitioning >= .. and column_for_partitioning < ..
             select [*] from table_name where column_for_partitioning >= offset and column_for_partitioning < (offset + limit) ...
        """
        CommonBasicUtilities.check_not_empty(table_name, "Table name cannot be null or empty!")
        is_nested_select = True if CommonBasicUtilities.isEmpty(column_for_partitioning) and (limit is not None or offset is not None)  else False
        offset = offset if not None else 0
        query = ""
        if is_nested_select:
            query = "SELECT "
            if CommonBasicUtilities.isEmpty(column_names) or column_names.strip() == "*":
                query += "*"
            else:
                query  += column_names
            query += " FROM ( SELECT a.*, ROWNUM rnum FROM ( "
        query += "SELECT "
        if CommonBasicUtilities.isEmpty(column_names) or column_names.strip() == "*":
            query += "*"
        else:
            query  += column_names
        query += f" FROM {table_name}"

        isAndNeeded = True if not CommonBasicUtilities.isEmpty(column_for_partitioning) and not CommonBasicUtilities.isEmpty(where_clause) else False
        if not CommonBasicUtilities.isEmpty(where_clause):
            query += f" WHERE {where_clause}"
        elif not CommonBasicUtilities.isEmpty(column_for_partitioning):
             query += f" WHERE"
        if isAndNeeded:
             query += " AND"
        if not CommonBasicUtilities.isEmpty(column_for_partitioning):
            query += f" {column_for_partitioning} >=  {offset}"
            if limit is not None:
                query += f" {column_for_partitioning} < {offset + limit}"

        if CommonBasicUtilities.isEmpty(column_for_partitioning) and not CommonBasicUtilities.isEmpty(orderby_clause) :
            query += f" ORDER BY {orderby_clause}" # if column_for_partitioning is applied, there is no need for order by

        if is_nested_select:
            query += f" ) a"
            if limit is not None:
                query += f" WHERE ROWNUM <= {limit + offset}"
            query +=f" ) WHERE rnum > {offset}"
       
        return query
