from .db_operations import *

class DBOperationsFactory:
  """
  Factory class for creating BaseDBOperations objects based on database type.
  """

  @staticmethod
  def create(db_properties: dict, spark: SparkSession) -> BaseDBOperations:
    """
    Creates an BaseDBOperations object based on the 'dbtype' property.

    Args:
      db_properties: A dictionary containing database connection properties.

    Returns:
      An BaseDBOperations object for the specified database type.

    Raises:
      ValueError: If the 'dbtype' is not supported or missing.
    """

    if 'dbtype' not in db_properties:
      raise ValueError("The 'dbtype' key is required in the db_properties dictionary.")

    db_type = db_properties.get('dbtype', '').lower()

    if db_type in ('postgresql', 'postgres'):
        # from .postgresql_db_operations import PostgreSqlDBOperations
        return PostgreSqlDBOperations(db_properties, spark)
    if db_type in ('oracle'):
        # from .oracle_db_operations import OracleDBOperations
        return OracleDBOperations(db_properties, spark)
    else:
      raise ValueError(f"Unsupported database type: {db_type}")
