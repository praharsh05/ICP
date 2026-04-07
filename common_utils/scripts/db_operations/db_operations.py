
from abc import ABC, abstractmethod
from pyspark.sql import SparkSession
from pyspark.sql.dataframe import DataFrame
from typing import Union

from common_utils.scripts.helper.common_helper_utilities import CommonBasicUtilities
from common_utils.scripts.common_utilities import CommonLogging

logging = CommonLogging.get_logger()

class  BasicDBOperationsUtils:
    @staticmethod
    def build_select_query(table_name: str= None, column_names: str = "*", where_clause: str = "", orderby_clause: str = "", 
                limit: int = None, offset: int = None, column_for_partitioning: str = None) -> str:
         
        CommonBasicUtilities.check_not_empty(table_name, "Table name cannot be null or empty!")
        
        # Initialize the query string
        query = "SELECT "
        
        # Select the columns
        if CommonBasicUtilities.isEmpty(column_names) or column_names.strip() == "*":
            query += "*"
        else:
            query += column_names
        
        # Start the basic FROM clause
        query += f" FROM {table_name}"

        # Handle WHERE clause and partitioning column
        isAndNeeded = not CommonBasicUtilities.isEmpty(column_for_partitioning) and not CommonBasicUtilities.isEmpty(where_clause)
        
        if not CommonBasicUtilities.isEmpty(where_clause):
            query += f" WHERE {where_clause}"
        elif not CommonBasicUtilities.isEmpty(column_for_partitioning):
            query += " WHERE"

        if isAndNeeded:
            query += " AND"
        
        # Add partitioning and pagination logic only if offset is not None
        if not CommonBasicUtilities.isEmpty(column_for_partitioning):
            if offset is not None:
                query += f" {column_for_partitioning} >= {offset}"
            if limit is not None:
                if offset is not None:
                    query += f" AND {column_for_partitioning} < {offset + limit}"
                else:
                    query += f" {column_for_partitioning} < {limit}"

        # If there is no partitioning column and ORDER BY clause is provided, add the ORDER BY
        if CommonBasicUtilities.isEmpty(column_for_partitioning) and not CommonBasicUtilities.isEmpty(orderby_clause):
            query += f" ORDER BY {orderby_clause}"

        return query

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

    def build_select_query(self, table_name: str= None, column_names: str = "*", where_clause: str = "", orderby_clause: str = "",
                 limit: int = None, offset: int = None, column_for_partitioning: str = None) -> str:
        
        query =  BasicDBOperationsUtils.build_select_query(table_name=table_name,  column_names=column_names, where_clause=where_clause,
                                                        orderby_clause=orderby_clause, limit=limit, offset=offset,
                                                          column_for_partitioning=column_for_partitioning)
        
        if CommonBasicUtilities.isEmpty(column_for_partitioning):
            if limit is not None:
                query += f" LIMIT {limit}"
            if offset is not None and offset > 0:
                query += f" OFFSET {offset}"

        return query
      
        
    def read_data(self, table_name: str= None, column_names: str = "*", where_clause: str = "", orderby_clause: str = "",
                  limit: int = None, offset: int = None, column_for_partitioning: str = None,
                  query: str = None, lower_bound: Union[str, int] = None,
                  upper_bound: Union[str, int] = None, num_partitions: int = None, predicates = None
                  ) -> DataFrame:
        """
        """
        if query:
            # Use the provided query directly
            return self._read_data(query=query,num_partitions=num_partitions,column=column_for_partitioning,lower_bound=lower_bound,upper_bound=upper_bound)

        elif not CommonBasicUtilities.isEmpty(column_for_partitioning)\
            and ((lower_bound is not None and upper_bound is not None and num_partitions is not None) or predicates is not None):
            # Handle partitioning logic
            return self._read_data(table_name=table_name, column=column_for_partitioning, lower_bound=lower_bound, 
                                    upper_bound=upper_bound, num_partitions=num_partitions, column_names=column_names
                                    ,orderby_clause=orderby_clause, predicates = predicates
                                    )
        
        elif lower_bound is not None and upper_bound is not None:
            # Handle partitioning logic
            return self._read_data(table_name=table_name,  lower_bound=lower_bound, 
                                    upper_bound=upper_bound, column_names=column_names
                                    )
        else:
            # Default to pagination logic
            query = self.build_select_query(table_name, column_names, where_clause, orderby_clause,
                                     limit, offset, column_for_partitioning)
            return self._read_data(query=query)


    def _read_data(self, query: str = None, table_name: str = None, column: str = None,
                   lower_bound: Union[str, int] = None, upper_bound: Union[str, int] = None,
                   num_partitions: int = None, column_names: str=None, predicates = None,
                   orderby_clause="") -> DataFrame:
        """
        Reads data from the database using either a custom query or partitioning parameters.
        """
        logging.info("before applying the conditions the options are: numPartitions -> {} , lower_bound -> {} m upper_bound -> {} and column_for_partitioning -> {}".format(num_partitions,lower_bound,upper_bound,column))
        logging.info("Before applying the conditions Query -> {}".format(query))
        print(f"predicates->{predicates}")
        if query and num_partitions is not None and lower_bound is not None and upper_bound is not None and column is not None:
            # If query is provided, use it directly
            logging.info("Query -> {}".format(query))
            logging.info("Q1 options are: numPartitions -> {} , lower_bound -> {} upper_bound -> {} and column_for_partitioning -> {} and fetchsize --> 40000".format(num_partitions,lower_bound,upper_bound,column))

            df = self._spark.read.format("jdbc") \
                .option("url", self._db_properties["url"]) \
                .option("dbtable", f"({query})  subquery") \
                .option("numPartitions", num_partitions) \
                .option("partitionColumn", column) \
                .option("lowerBound", lower_bound) \
                .option("upperBound", upper_bound) \
                .option("fetchsize", 40000) \
                .option("user", self._db_properties["user"]) \
                .option("password", self._db_properties["password"]) \
                .option("sessionInitStatement","ALTER SESSION SET NLS_DATE_FORMAT='YYYY-MM-DD HH24:MI:SS' NLS_TIMESTAMP_FORMAT='YYYY-MM-DD HH24:MI:SS' NLS_TIMESTAMP_TZ_FORMAT='YYYY-MM-DD HH24:MI:SS TZH:TZM'")\
                .option("driver", self.get_driver()) \
                .load()
        elif query:
            # If query is provided, use it directly
            logging.info("Query -> {}".format(query))
            logging.info("numPartitions -> {}".format(num_partitions))
            df = self._spark.read.format("jdbc") \
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
            
            # Determine if quotes are needed (for date values)
            def format_value(value):
                return f"'{value}'" if isinstance(value, str) else str(value)
            
            query = f"(SELECT {column_names} FROM {table_name} WHERE {column} >= {lower_bound} AND {column} <= {upper_bound}) query"
            
            logging.info("Query -> {}".format(query))

            df = self._spark.read.format("jdbc") \
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

        elif table_name and column and predicates is not None:
            query = f"""(SELECT {column_names} FROM {table_name} ) query"""

            logging.info("Query -> {}".format(query))
            logging.info("Filters -> {}".format(predicates))

            df = self._spark.read.jdbc(
                url=self._db_properties["url"],
                table=query,
                predicates=predicates,
                properties=self._db_properties
            )

        elif  table_name and lower_bound is not None and upper_bound is not None:
            basic_query = f"select {column_names} from {table_name}"

            query = f"""( SELECT * FROM ( SELECT a.*, ROWNUM rnum_temp__ FROM ( {basic_query} ) a
                                        WHERE ROWNUM <= {upper_bound}
                                    ) WHERE rnum_temp__ >= {lower_bound}
                    ) query
                    """
            logging.info("Query -> {}".format(query))

            df = self._spark.read.format("jdbc") \
            .option("url", self._db_properties["url"]) \
            .option("dbtable", query) \
            .option("user", self._db_properties["user"]) \
            .option("password", self._db_properties["password"]) \
            .option("driver", self.get_driver()) \
            .load()
        else:
            raise ValueError("Invalid parameters. Provide either a query or table name with partitioning details.")
        
        # Drop rnum_temp__ or RNUM_TEMP__ if they exist
        if 'rnum_temp__' in df.columns:
            df = df.drop("rnum_temp__")

        elif 'RNUM_TEMP__' in df.columns:
            df = df.drop("RNUM_TEMP__")

        return df

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
    def build_select_query(self, table_name: str= None, column_names: str = "*", where_clause: str = "", orderby_clause: str = "", 
                limit: int = None, offset: int = None, column_for_partitioning: str = None) -> str:
        """ SELECT * FROM (
                 SELECT a.*, ROWNUM rnum_temp__ FROM (
                     SELECT * FROM employees [WHERE whereclause | range using column_for_partitioning] ORDER BY employee_id
                 ) a WHERE ROWNUM <= 20
             ) WHERE rnum_temp__ > 10;
             if column_for_partitioning is empty or null and limit or offset are not none, use the ROWNUM using nestead query
             otherwise use range_query ... column_for_partitioning >= .. and column_for_partitioning < ..
             select [*] from table_name where column_for_partitioning >= offset and column_for_partitioning < (offset + limit) ...
        """

        query =  BasicDBOperationsUtils.build_select_query(table_name=table_name,  column_names=column_names, where_clause=where_clause,
                                                        orderby_clause=orderby_clause, limit=limit, offset=offset,
                                                          column_for_partitioning=column_for_partitioning)

         # Determine if a nested query is needed (only when limit or offset are provided)
        is_nested_select = (limit is not None or offset is not None) and CommonBasicUtilities.isEmpty(column_for_partitioning)

        # If limit or offset is provided, use a nested query for pagination
        if is_nested_select:
            query = f"SELECT * FROM ( SELECT a.*, ROWNUM rnum_temp__ FROM ( {query} ) a"
            if limit is not None:
                query += f" WHERE ROWNUM <= {limit + (offset if offset is not None else 0)}"
            query += f" ) WHERE rnum_temp__ > {offset if offset is not None else 0}"

        return query
    
    def build_select_query_old(self, table_name: str= None, column_names: str = "*", where_clause: str = "", orderby_clause: str = "", 
                limit: int = None, offset: int = None, column_for_partitioning: str = None) -> str:
        
        """ SELECT * FROM (
                 SELECT a.*, ROWNUM rnum_temp__ FROM (
                     SELECT * FROM employees [WHERE whereclause | range using column_for_partitioning] ORDER BY employee_id
                 ) a WHERE ROWNUM <= 20
             ) WHERE rnum_temp__ > 10;
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
            query += " FROM ( SELECT a.*, ROWNUM rnum_temp__ FROM ( "
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
            query +=f" ) WHERE rnum_temp__ > {offset}"
       
        return query

class MSSqlServerDBOperations(BaseDBOperations):
    DRIVER_CONSTANT = "com.microsoft.sqlserver.jdbc.SQLServerDriver"

    def __init__(self, db_properties: dict, spark: SparkSession):
        super().__init__(db_properties, spark)

    def get_driver(self) -> str:
        return self.DRIVER_CONSTANT
    
    def build_select_query(self, table_name: str= None, column_names: str = "*", where_clause: str = "", orderby_clause: str = "", 
                limit: int = None, offset: int = None, column_for_partitioning: str = None) -> str:
        
        query =  BasicDBOperationsUtils.build_select_query(table_name=table_name,  column_names=column_names,
                                                        where_clause=where_clause,orderby_clause=orderby_clause,
                                                        limit=limit, offset=offset,column_for_partitioning=column_for_partitioning)
         
        # If limit or offset is provided, use a nested query for pagination
        if CommonBasicUtilities.isEmpty(column_for_partitioning):
            if offset is not None and offset > 0:
                query += f" OFFSET {offset} ROWS"
            if limit is not None:
                query += f" FETCH NEXT {limit} ROWS ONLY"

        return query