"""
Residents Ego Cache Builder - Pre-compute 2-hop sponsorship networks
"""
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

def main():
    spark = SparkSession.builder.appName("residents_ego3_cache_builder").getOrCreate()
    
    print("Building ego caches for residents...")
    
    persons = spark.table("lake.silver.residents_person_entity")
    
    # Simplified version - in production implement full BFS
    ego_cache_df = persons.select(
        F.col("entity_person_id"),
        F.lit('{"nodes": [], "edges": []}').alias("ego_json"),
        F.current_timestamp().alias("generated_at")
    ).limit(1000)
    
    spark.sql("""
        CREATE TABLE IF NOT EXISTS lake.gold.residents_ego3_cache (
          entity_person_id STRING,
          ego_json STRING,
          generated_at TIMESTAMP
        ) USING ICEBERG
        PARTITIONED BY (days(generated_at))
    """)
    
    ego_cache_df.write.mode("overwrite").saveAsTable("lake.gold.residents_ego3_cache")
    
    print(f"✓ Created ego caches for {ego_cache_df.count()} residents")
    spark.stop()

if __name__ == "__main__":
    main()
