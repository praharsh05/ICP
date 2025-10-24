# Architecture
Bronze → Silver → Gold (Iceberg on S3, queried via Trino). Spark builds Silver/Gold. Neo4j for graph ops.
Dedup → Links → Ego3 Cache → (optional) Load to Neo4j.
