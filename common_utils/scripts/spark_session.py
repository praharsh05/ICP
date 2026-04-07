"""
Spark Session Utility
Provides reusable Spark session configuration for ETL jobs
"""
from pyspark.sql import SparkSession
from pyspark.conf import SparkConf
import os
import logging

logger = logging.getLogger(__name__)


class SparkSessionManager:
    """Manages Spark session lifecycle with optimized configurations"""
    
    _instance = None
    
    def __init__(self):
        self.spark = None
    
    @classmethod
    def get_instance(cls):
        """Singleton pattern for Spark session"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def create_session(
        self,
        app_name: str,
        iceberg_enabled: bool = True,
        warehouse_path: str = None,
        additional_configs: dict = None
    ) -> SparkSession:
        """
        Create optimized Spark session for family graph ETL
        
        Args:
            app_name: Spark application name
            iceberg_enabled: Enable Iceberg catalog
            warehouse_path: Path to warehouse (MinIO/S3)
            additional_configs: Additional Spark configurations
            
        Returns:
            Configured SparkSession
        """
        if self.spark:
            logger.info("Reusing existing Spark session")
            return self.spark
        
        logger.info(f"Creating new Spark session: {app_name}")
        
        # Base configurations
        conf = SparkConf()
        
        # Application settings
        conf.set("spark.app.name", app_name)
        conf.set("spark.master", os.getenv("SPARK_MASTER", "local[*]"))
        
        # Memory and performance tuning
        conf.set("spark.driver.memory", os.getenv("SPARK_DRIVER_MEMORY", "4g"))
        conf.set("spark.executor.memory", os.getenv("SPARK_EXECUTOR_MEMORY", "4g"))
        conf.set("spark.executor.cores", os.getenv("SPARK_EXECUTOR_CORES", "2"))
        conf.set("spark.sql.shuffle.partitions", os.getenv("SPARK_SHUFFLE_PARTITIONS", "200"))
        
        # Adaptive query execution
        conf.set("spark.sql.adaptive.enabled", "true")
        conf.set("spark.sql.adaptive.coalescePartitions.enabled", "true")
        
        # Iceberg configurations
        if iceberg_enabled:
            conf.set("spark.sql.extensions", 
                    "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
            conf.set("spark.sql.catalog.spark_catalog", 
                    "org.apache.iceberg.spark.SparkSessionCatalog")
            conf.set("spark.sql.catalog.spark_catalog.type", "hive")
            
            # Iceberg catalog for digiXT
            conf.set("spark.sql.catalog.iceberg", 
                    "org.apache.iceberg.spark.SparkCatalog")
            conf.set("spark.sql.catalog.iceberg.type", "hadoop")
            
            if warehouse_path:
                conf.set("spark.sql.catalog.iceberg.warehouse", warehouse_path)
        
        # MinIO/S3 configurations
        minio_endpoint = os.getenv("MINIO_ENDPOINT")
        if minio_endpoint:
            conf.set("spark.hadoop.fs.s3a.endpoint", minio_endpoint)
            conf.set("spark.hadoop.fs.s3a.access.key", os.getenv("MINIO_ACCESS_KEY", ""))
            conf.set("spark.hadoop.fs.s3a.secret.key", os.getenv("MINIO_SECRET_KEY", ""))
            conf.set("spark.hadoop.fs.s3a.path.style.access", "true")
            conf.set("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
            conf.set("spark.hadoop.fs.s3a.connection.ssl.enabled", "false")
        
        # Additional custom configurations
        if additional_configs:
            for key, value in additional_configs.items():
                conf.set(key, str(value))
        
        # Create Spark session
        builder = SparkSession.builder.config(conf=conf)
        
        # Enable Hive support if needed
        if os.getenv("SPARK_ENABLE_HIVE", "true").lower() == "true":
            builder = builder.enableHiveSupport()
        
        self.spark = builder.getOrCreate()
        
        # Set log level
        log_level = os.getenv("SPARK_LOG_LEVEL", "WARN")
        self.spark.sparkContext.setLogLevel(log_level)
        
        logger.info(f"Spark session created successfully: {self.spark.version}")
        logger.info(f"Spark UI available at: {self.spark.sparkContext.uiWebUrl}")
        
        return self.spark
    
    def stop_session(self):
        """Stop Spark session"""
        if self.spark:
            logger.info("Stopping Spark session")
            self.spark.stop()
            self.spark = None
    
    def get_spark(self) -> SparkSession:
        """Get current Spark session"""
        if not self.spark:
            raise RuntimeError("Spark session not initialized. Call create_session() first.")
        return self.spark


def get_spark_session(app_name: str, **kwargs) -> SparkSession:
    """
    Convenience function to get Spark session
    
    Args:
        app_name: Application name
        **kwargs: Additional arguments for create_session
        
    Returns:
        SparkSession
    """
    manager = SparkSessionManager.get_instance()
    return manager.create_session(app_name, **kwargs)


def stop_spark_session():
    """Convenience function to stop Spark session"""
    manager = SparkSessionManager.get_instance()
    manager.stop_session()
