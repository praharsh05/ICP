from __future__ import annotations

# from pyspark.sql.functions import 
# from pyspark.sql.functions import to_date, col, to_timestamp, lit, current_timestamp
from pyspark.sql import functions as F
from pyspark.sql.functions import broadcast
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.window import Window
from typing import Union, List, Tuple, Optional
from datetime import datetime, timedelta, date
from typing import List as _List, Optional as _Optional
from typing import Any, Dict, List, Tuple
from pyspark.sql.types import *
import time
# Custom Dependencies
# TODO: this is added to help airflow detect common_utils as module
import sys
sys.path.append("/workflows/family_tree_data_pipeline/")
print("Sys Path:", sys.path)


from common_utils.scripts.common_utilities import CommonLogging, CommonIcebergUtilities
from common_utils.scripts.helper.common_helper_utilities import CommonBasicUtilities, CommonProcessHelperUtils
from common_utils.scripts.data.common_data_utilities import CommonDataUtilities
from common_utils.scripts.batch_calculator_utils import BatchCalculatorUtils

from common_utils.scripts.db_operations.db_operations_factory import DBOperationsFactory
from common_utils.scripts.db_operations.db_operations import BaseDBOperations

# Custom Data Quality Checker
from common_utils.scripts.data_quality import DataQualityChecker
from pyspark.sql.types import StringType, StructType, StructField

from decimal import Decimal

logging = CommonLogging.get_logger()

# ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** ***** *****

MOUNT_BUCKET = '/workflows'

class Constants:
    DEFAULT_RECORDS_PER_BATCH = 1_00_000
    DEFAULT_NUMBER_OF_PARTITIONS = 1
    DEFAULT_IS_COL_FOR_PARTITION_NULL_SUPP=True

    # Mapping of relationship names to graph edge types
    RELATIONSHIP_MAPPING = {
        # Parent-child relationships (directed: child -> parent)
        'FATHER': 'CHILD_OF',
        'MOTHER': 'CHILD_OF',
        'PARENT': 'CHILD_OF',
        'DAD': 'CHILD_OF',
        'MOM': 'CHILD_OF',
        
        # Child relationships (will be inverted to CHILD_OF: parent <- child)
        'SON': 'PARENT_OF',  # Will create: child -[CHILD_OF]-> parent
        'DAUGHTER': 'PARENT_OF',
        'CHILD': 'PARENT_OF',
        
        # Spouse relationships (bidirectional, will be deduplicated)
        'HUSBAND': 'SPOUSE_OF',
        'WIFE': 'SPOUSE_OF',
        'SPOUSE': 'SPOUSE_OF',
        
        # Sibling relationships (bidirectional, will be deduplicated)
        'BROTHER': 'SIBLING_OF',
        'SISTER': 'SIBLING_OF',
        'SIBLING': 'SIBLING_OF',
        
        # Grandparent-grandchild relationships (directed: grandchild -> grandparent)
        'GRANDFATHER': 'GRANDCHILD_OF',
        'GRANDMOTHER': 'GRANDCHILD_OF',
        'GRANDPARENT': 'GRANDCHILD_OF',
        
        # Grandchild relationships (will be inverted to GRANDCHILD_OF)
        'GRANDSON': 'GRANDPARENT_OF',  # Will create: grandchild -[GRANDCHILD_OF]-> grandparent
        'GRANDDAUGHTER': 'GRANDPARENT_OF',
        'GRANDCHILD': 'GRANDPARENT_OF',

        # Step-parent Relationships (directed: step-child -> step-parent)
        'STEPFATHER': 'STEP_CHILD_OF',
        'STEPMOTHER': 'STEP_CHILD_OF',
        'STEPPARENT': 'STEP_CHILD_OF',

        # Step-child Relationships (will be inverted to STEP_CHILD_OF)
        'STEPSON': 'STEP_PARENT_OF',
        'STEPDAUGHTER': 'STEP_PARENT_OF',
        'STEPCHILD': 'STEP_PARENT_OF',

        # compound relationships (with slashes - need special handling)
        # Format: "Daughter / wife daughter" means person's daughter OR wife's daughter
        'DAUGHTER / WIFE DAUGHTER': 'COMPOUND DAUGHTER',
        'DAUGHTER / HUSBAND DAUGHTER': 'COMPOUND DAUGHTER',
        'SON / HUSBAND SON': 'COMPOUND SON',
        'SON / WIFE SON': 'COMPOUND SON',

        # Second spouse relationship for SPON_DRIVED handling as step parent
        'MOTHER / FATHER WIFE': 'STEP_CHILD_OF',
        'FATHER / MOTHER HUSBAND': 'STEP_CHILD_OF',

        # Guardian/Custodian relationship
        'CUSTODIAN HUSBAND': 'GUARDIAN_OF',
        'CUSTODIAN': 'GUARDIAN_OF',
        'GUARDIAN': 'GUARDIAN_OF',
    }


def parse_compound_relationship(relation_col):
    """
    parse compound relationships

    Logic:
    -'DAUGHTER / WIFE DAUGHTER' -> if relation_source = SPONS, its stepdaughter, else daughter
    -'SON / WIFE SON' -> if relation_source = SPONS, its stepson, else son
    -'MOTHER / FATHER WIFE' -> Stepmother
    -'FATHER / MOTHER HUSBAND' -> Stepfather
    """

    return (
        F.when(
            relation_col.contains('DAUGHTER / WIFE DAUGHTER') | relation_col.contains('DAUGHTER / HUSBAND DAUGHTER'),
            F.lit("STEPDAUGHTER")
        )
        .when(
            relation_col.contains('SON / WIFE SON') | relation_col.contains('SON / HUSBAND SON'),
            F.lit("STEPSON")
        )
        .when(
            relation_col.contains('MOTHER / FATHER WIFE'),
            F.lit("STEPMOTHER")
        )
        .when(
            relation_col.contains('FATHER / MOTHER HUSBAND'),
            F.lit("STEPFATHER")
        )
        .otherwise(relation_col)
    )


def preprocess_relationship_names(df):
    """
    Preprocess and normalise relationship names
    handles Null values, case variations, and complex relationships

    Args:
        df: source relationships DataFrame
    
    Returns:
        DataFrame with normalised relationship names
    """
    logging.info("="*80)
    logging.info("Preprocessing relationship names")
    logging.info("="*80)

    # Filter out Null relationships
    df_filtered = df.filter(F.col("relation_nm").isNotNull())
    logging.info("Filtered out relationships with NULL relation_nm")
    
    # Normalize: uppercase and trim whitespaces
    df_normalized = df_filtered.withColumn(
        "relation_nm_normalized",
        F.upper(F.trim(F.col("relation_nm")))
    )

    # Handle compound relationships
    # 'DAUGHTER / WIFE DAUGHTER' -> parse and determine relationship type
    df_normalized = df_normalized.withColumn(
        "relation_nm_normalized",
        F.when(
            F.col("relation_nm_normalized").contains("/"),
            parse_compound_relationship(F.col("relation_nm_normalized"))
        ).otherwise(F.col("relation_nm_normalized"))
    )

    logging.info("Relationship names preprocessed and normalized")

    return df_normalized


def load_person_ids(persons_path, spark_session):
    """Load valid person IDs for validation"""
    logging.info("="*80)
    logging.info(f"Loading person IDs from: {persons_path}")
    logging.info("="*80)
    
    try:
        persons_df = (
            spark_session.read
            .option("header", "true")
            .option("inferSchema", "true")
            .csv(f"{persons_path}/persons")
        )

        valid_person_ids = persons_df.select(F.col("`personId:ID`").alias("spm_person_no")).distinct()
        logging.info("Person IDs loaded from partitioned data")
        
        return valid_person_ids
        
    except Exception as e:
        logging.info("="*80)
        logging.error(f"Failed to load person IDs: {str(e)}")
        logging.info("="*80)
        raise


def map_relationship_types(df, output_path):
    """
    Map relationship names to graph edge types
    
    Args:
        df: Relationships DataFrame
        
    Returns:
        DataFrame with edge_type column
    """
    logging.info("="*80)
    logging.info("Mapping relationship types to graph edges")
    logging.info("="*80)
    
    # Create mapping expression
    mapping_expr = F.create_map(
        [F.lit(x) for pair in Constants.RELATIONSHIP_MAPPING.items() for x in pair]
    )
    
    # Map relationship names (case-insensitive)
    df_mapped = df.withColumn(
        "edge_type",
        mapping_expr[F.upper(F.col("relation_nm_normalized"))]
    )
    
    # Log unmapped relationships — use head(1) to check existence without full scan
    unmapped = df_mapped.filter(F.col("edge_type").isNull())
    has_unmapped = len(unmapped.head(1)) > 0

    if has_unmapped:
        logging.warning("Found unmapped relationship types")
        
        # Show top unmapped types
        unmapped_types = (
            unmapped
            .groupBy("relation_nm", "relation_nm_normalized")
            .count()
            .orderBy(F.desc("count"))
            .limit(20)
        )
        
        logging.warning("Top unmapped relationship types:")
        unmapped_types.show(truncate=False)

        # Write unmapped to file to review
        unmapped_types.write.mode("overwrite").csv(
            f"{output_path}/unmapped_relationships.csv",
            header=True
        )
    
    # Filter to only mapped relationships
    df_mapped = df_mapped.filter(F.col("edge_type").isNotNull())

    # Log mapping statistics
    edge_type_stats = (
        df_mapped
        .groupBy("edge_type")
        .count()
        .orderBy(F.desc("count"))
    )
    logging.info("="*80)
    logging.info("Relationship types distribution:")
    edge_type_stats.show(truncate=False)
    logging.info("="*80)
    
    return df_mapped


def create_child_of_edges(df):
    """
    Create directed CHILD_OF edges (child -> parent)
    
    For PARENT_OF relationships, we need to invert the direction
    
    Args:
        df: Mapped relationships DataFrame
        
    Returns:
        DataFrame with CHILD_OF edges in correct direction
    """
    logging.info("="*80)
    logging.info("Creating CHILD_OF edges")
    logging.info("="*80)

    # Direct CHILD_OF (person_no is child, rltv_person_no is parent)
    child_of_direct = (
        df.filter(F.col("edge_type") == "CHILD_OF")
        .select(
            F.col("person_no").alias("source"),
            F.col("rltv_person_no").alias("target"),
            F.lit("CHILD_OF").alias("type"),
            F.col("relation_source").alias("source_type"),
            F.col("relation_lvl").alias("confidence"),
            F.col("udb_relation_id").alias("lookup_id")
        )
    )
    
    # Inverted PARENT_OF (person_no is parent, rltv_person_no is child)
    # Create: child -[CHILD_OF]-> parent
    parent_of_inverted = (
        df.filter(F.col("edge_type") == "PARENT_OF")
        .select(
            F.col("rltv_person_no").alias("source"),  # Child
            F.col("person_no").alias("target"),        # Parent
            F.lit("CHILD_OF").alias("type"),
            F.col("relation_source").alias("source_type"),
            F.col("relation_lvl").alias("confidence"),
            F.col("udb_relation_id").alias("lookup_id")
        )
    )
    
    # Union both
    child_of_edges = child_of_direct.union(parent_of_inverted)
    
    # Remove duplicates
    child_of_edges = child_of_edges.dropDuplicates(["source", "target"])

    return child_of_edges


def create_spouse_of_edges(df):
    """
    Create bidirectional SPOUSE_OF edges (deduplicated)
    
    For SPOUSE_OF, we only keep one direction (person_no < rltv_person_no)
    to avoid duplicates
    
    Args:
        df: Mapped relationships DataFrame
        
    Returns:
        DataFrame with deduplicated SPOUSE_OF edges
    """
    logging.info("="*80)
    logging.info("Creating SPOUSE_OF edges")
    logging.info("="*80)

    # Extract spouse relationships
    spouse_edges = (
        df.filter(F.col("edge_type") == "SPOUSE_OF")
        .select(
            F.col("person_no").alias("person_1"),
            F.col("rltv_person_no").alias("person_2"),
            F.col("relation_source").alias("source_type"),
            F.col("relation_lvl").alias("confidence"),
            F.col("udb_relation_id").alias("lookup_id")
        )
    )
    
    # Deduplicate by keeping only one direction (alphabetically)
    spouse_edges_dedup = (
        spouse_edges
        .withColumn(
            "source",
            F.when(
                F.col("person_1") < F.col("person_2"),
                F.col("person_1")
            ).otherwise(F.col("person_2"))
        )
        .withColumn(
            "target",
            F.when(
                F.col("person_1") < F.col("person_2"),
                F.col("person_2")
            ).otherwise(F.col("person_1"))
        )
        .withColumn("type", F.lit("SPOUSE_OF"))
        .select("source", "target", "type", "source_type", "confidence", "lookup_id")
        .dropDuplicates(["source", "target"])
    )

    return spouse_edges_dedup


def create_sibling_of_edges(df):
    """
    Create bidirectional SIBLING_OF edges (deduplicated)
    
    Similar to SPOUSE_OF, we only keep one direction (person_no < rltv_person_no)
    to avoid duplicates. This is important for residents who can sponsor siblings
    directly without parent relationships.
    
    Args:
        df: Mapped relationships DataFrame
        
    Returns:
        DataFrame with deduplicated SIBLING_OF edges
    """
    logging.info("="*80)
    logging.info("Creating SIBLING_OF edges")
    logging.info("="*80)

    # Extract sibling relationships
    sibling_edges = (
        df.filter(F.col("edge_type") == "SIBLING_OF")
        .select(
            F.col("person_no").alias("person_1"),
            F.col("rltv_person_no").alias("person_2"),
            F.col("relation_source").alias("source_type"),
            F.col("relation_lvl").alias("confidence"),
            F.col("udb_relation_id").alias("lookup_id")
        )
    )
    
    # Deduplicate by keeping only one direction (alphabetically)
    sibling_edges_dedup = (
        sibling_edges
        .withColumn(
            "source",
            F.when(
                F.col("person_1") < F.col("person_2"),
                F.col("person_1")
            ).otherwise(F.col("person_2"))
        )
        .withColumn(
            "target",
            F.when(
                F.col("person_1") < F.col("person_2"),
                F.col("person_2")
            ).otherwise(F.col("person_1"))
        )
        .withColumn("type", F.lit("SIBLING_OF"))
        .select("source", "target", "type", "source_type", "confidence", "lookup_id")
        .dropDuplicates(["source", "target"])
    )

    return sibling_edges_dedup


def create_grandchild_of_edges(df):
    """
    Create directed GRANDCHILD_OF edges (grandchild -> grandparent)
    
    For GRANDPARENT_OF relationships, we need to invert the direction
    to maintain consistency (like CHILD_OF).
    
    Args:
        df: Mapped relationships DataFrame
        
    Returns:
        DataFrame with GRANDCHILD_OF edges in correct direction
    """
    logging.info("="*80)
    logging.info("Creating GRANDCHILD_OF edges")
    logging.info("="*80)

    # Direct GRANDCHILD_OF (person_no is grandchild, rltv_person_no is grandparent)
    grandchild_of_direct = (
        df.filter(F.col("edge_type") == "GRANDCHILD_OF")
        .select(
            F.col("person_no").alias("source"),
            F.col("rltv_person_no").alias("target"),
            F.lit("GRANDCHILD_OF").alias("type"),
            F.col("relation_source").alias("source_type"),
            F.col("relation_lvl").alias("confidence"),
            F.col("udb_relation_id").alias("lookup_id")
        )
    )
    
    # Inverted GRANDPARENT_OF (person_no is grandparent, rltv_person_no is grandchild)
    # Create: grandchild -[GRANDCHILD_OF]-> grandparent
    grandparent_of_inverted = (
        df.filter(F.col("edge_type") == "GRANDPARENT_OF")
        .select(
            F.col("rltv_person_no").alias("source"),  # Grandchild
            F.col("person_no").alias("target"),        # Grandparent
            F.lit("GRANDCHILD_OF").alias("type"),
            F.col("relation_source").alias("source_type"),
            F.col("relation_lvl").alias("confidence"),
            F.col("udb_relation_id").alias("lookup_id")
        )
    )
    
    # Union both
    grandchild_of_edges = grandchild_of_direct.union(grandparent_of_inverted)
    
    # Remove duplicates
    grandchild_of_edges = grandchild_of_edges.dropDuplicates(["source", "target"])

    return grandchild_of_edges

def create_step_child_of_edges(df):
    """
    Create directed STEP_CHILD_OF edges (step-child->step-parent)
    Smilar to CHILD_OF but for step-relationships

    Args:
        df: Mapped relationships DataFrame
        
    Returns:
        DataFrame with STEP_CHILD_OF edges
    """
    logging.info("="*80)
    logging.info("Creating STEP_CHILD_OF edges")
    logging.info("="*80)

    # Direct STEP_CHILD_OF (person_no is step-child, rltv_person_no is step-parent)
    step_child_of_direct = (
        df.filter(F.col("edge_type") == "STEP_CHILD_OF")
        .select(
            F.col("person_no").alias("source"),
            F.col("rltv_person_no").alias("target"),
            F.lit("STEP_CHILD_OF").alias("type"),
            F.col("relation_source").alias("source_type"),
            F.col("relation_lvl").alias("confidence"),
            F.col("udb_relation_id").alias("lookup_id")
        )
    )
    
    # Inverted STEP_PARENT_OF (person_no is step-parent, rltv_person_no is step-child)
    step_parent_of_inverted = (
        df.filter(F.col("edge_type") == "STEP_PARENT_OF")
        .select(
            F.col("rltv_person_no").alias("source"),  # Step-Child
            F.col("person_no").alias("target"),        # Step-Parent
            F.lit("STEP_CHILD_OF").alias("type"),
            F.col("relation_source").alias("source_type"),
            F.col("relation_lvl").alias("confidence"),
            F.col("udb_relation_id").alias("lookup_id")
        )
    )
    
    # Union both
    step_child_of_edges = step_child_of_direct.union(step_parent_of_inverted)
    
    # Remove duplicates
    step_child_of_edges = step_child_of_edges.dropDuplicates(["source", "target"])

    return step_child_of_edges


def create_guardian_of_edges(df):
    """
    Create directed GUARDIAN_OF edges
    for CUSTODIAN/GUARDIAN relationships

    Args:
        df: Mapped relationships DataFrame
        
    Returns:
        DataFrame with GUARDIAN_OF edges
    """

    logging.info("Creating GUARDIAN_OF edges")
    
    # Direct STEP_CHILD_OF (person_no is step-child, rltv_person_no is step-parent)
    guardian_edges = (
        df.filter(F.col("edge_type") == "GUARDIAN_OF")
        .select(
            F.col("person_no").alias("source"),
            F.col("rltv_person_no").alias("target"),
            F.lit("GUARDIAN_OF").alias("type"),
            F.col("relation_source").alias("source_type"),
            F.col("relation_lvl").alias("confidence"),
            F.col("udb_relation_id").alias("lookup_id")
        )
    )

    return guardian_edges


def create_compound_edges(df):
    """
    Handles compound relationships (COMPOUND_DAUGHTER, COMPOUND_SON)
    These are ambiguous and should be resolved based on context

    For now, we treat them as regular CHILD_OF relationships
    but mark them with special source_type for later review
    
    Args:
        df: Mapped relationships DataFrame
        
    Returns:
        DataFrame with compound edges mapped to CHILD_OF
    """
    logging.info("="*80)
    logging.info("Processing compound relationship edges")
    logging.info("="*80)

    # COMPOUND_DAUGHTER -> PARENT_OF (will be inverted to CHILD_OF)
    compound_daughter = (
        df.filter(F.col("edge_type") == "COMPOUND_DAUGHTER")
        .select(
            F.col("rltv_person_no").alias("source"),
            F.col("person_no").alias("target"),
            F.lit("CHILD_OF").alias("type"),
            F.lit("COMPOUND").alias("source_type"),
            F.col("relation_lvl").alias("confidence"),
            F.col("udb_relation_id").alias("lookup_id")
        )
    )
    
    # COMPOUND_SON -> PARENT_OF (will be inverted to CHILD_OF)
    compound_son = (
        df.filter(F.col("edge_type") == "COMPOUND_SON")
        .select(
            F.col("rltv_person_no").alias("source"),
            F.col("person_no").alias("target"),
            F.lit("CHILD_OF").alias("type"),
            F.lit("COMPOUND").alias("source_type"),
            F.col("relation_lvl").alias("confidence"),
            F.col("udb_relation_id").alias("lookup_id")
        )
    )
    
    # Union both and Remove duplicates
    compound_edges = compound_daughter.union(compound_son).dropDuplicates(["source", "target"])

    return compound_edges


def resolve_directional_duplicates(edges_df):
    """
    Deduplicate edges keeping highest-priority source per (source, target, type).
    Priority: CITF (1) > MAN_DEF (2) > SPONS (3) > SPON_DRIVED (4)

    Args:
        edges_df: Edges DataFrame with potential duplicates from multiple sources

    Returns:
        DataFrame with duplicates resolved by priority
    """
    logging.info("Resolving directional duplicates (preserve edge orientation)")

    edges = edges_df.withColumn(
        "priority",
        F.when(F.col("source_type") == "CITF", F.lit(1))
         .when(F.col("source_type") == "MAN_DEF", F.lit(2))
         .when(F.col("source_type") == "SPONS", F.lit(3))
         .when(F.col("source_type") == "SPON_DRIVED", F.lit(4))
         .otherwise(F.lit(99))
    )

    w = Window.partitionBy("source", "target", "type") \
              .orderBy(F.col("priority").asc(), F.col("confidence").desc(), F.col("lookup_id").asc())

    deduped = (
        edges
        .withColumn("rk", F.row_number().over(w))
        .filter(F.col("rk") == 1)
        .drop("priority", "rk")
    )

    return deduped


def validate_edges(edges_df, valid_person_ids):
    """
    Validate edges against person nodes.
    Uses broadcast joins with marker columns for efficient single-pass diagnostics.
    1 Spark action instead of 4 — and still logs invalid source/target counts.

    Args:
        edges_df: Edges DataFrame
        valid_person_ids: DataFrame with valid person IDs (should be cached + broadcast)

    Returns:
        Cleaned edges DataFrame (only edges where both source and target exist)
    """
    logging.info("Validating edges against person nodes")

    # Create broadcast lookups with unique marker columns to avoid ambiguity
    valid_src = (
        broadcast(valid_person_ids)
        .withColumnRenamed("spm_person_no", "source")
        .withColumn("_src_valid", F.lit(True))
    )

    valid_tgt = (
        broadcast(valid_person_ids)
        .withColumnRenamed("spm_person_no", "target")
        .withColumn("_tgt_valid", F.lit(True))
    )

    # Left joins — markers will be null where no match exists
    # on="source" / on="target" syntax deduplicates the join key (no column ambiguity)
    tagged = (
        edges_df
        .join(valid_src, on="source", how="left")
        .join(valid_tgt, on="target", how="left")
    )

    # Single aggregation for all diagnostics (1 Spark action instead of 4)
    stats = tagged.select(
        F.count("*").alias("total"),
        F.sum(F.when(F.col("_src_valid").isNull(), 1).otherwise(0)).alias("invalid_src"),
        F.sum(F.when(F.col("_tgt_valid").isNull(), 1).otherwise(0)).alias("invalid_tgt")
    ).first()

    if stats["invalid_src"] > 0:
        logging.warning(f"Found {stats['invalid_src']:,} edges with invalid source person_no")
    if stats["invalid_tgt"] > 0:
        logging.warning(f"Found {stats['invalid_tgt']:,} edges with invalid target person_no")

    # Filter to valid only (lazy transform, no extra action)
    valid_edges = (
        tagged
        .filter(F.col("_src_valid").isNotNull() & F.col("_tgt_valid").isNotNull())
        .drop("_src_valid", "_tgt_valid")
    )

    valid_count = stats["total"] - stats["invalid_src"] - stats["invalid_tgt"]
    logging.info(f"Valid edges: {valid_count:,}")

    return valid_edges


def write_statistics(spark_session, output_path, child_of_df, spouse_of_df, sibling_of_df, grandchild_of_df, stepchild_of_df, guardian_of_df):
    """Write edge statistics — single groupBy on union instead of 12+ separate .count() calls"""
    all_edges = (
        child_of_df
        .union(spouse_of_df)
        .union(sibling_of_df)
        .union(grandchild_of_df)
        .union(stepchild_of_df)
        .union(guardian_of_df)
    )

    stats_df = (
        all_edges
        .groupBy("type")
        .count()
        .orderBy("type")
    )

    stats_path = f"{output_path}/statistics/edge_stats.csv"
    (
        stats_df
        .coalesce(1)
        .write
        .mode("overwrite")
        .option("header", "true")
        .csv(stats_path)
    )

    logging.info("="*80)
    logging.info("Edge statistics:")
    stats_df.show()
    logging.info("="*80)


def write_output(spark_session, output_path, child_of_df, spouse_of_df, sibling_of_df, grandchild_of_df, stepchild_of_df, guardian_of_df, compound_df):
    """
    Write edges to CSV files
    
    Args:
        child_of_df: CHILD_OF edges DataFrame
        spouse_of_df: SPOUSE_OF edges DataFrame
        sibling_of_df: SIBLING_OF edges DataFrame
        grandchild_of_df: GRANDCHILD_OF edges DataFrame
        stepchild_of_df: STEP_CHILD_OF edges DataFrame
        guardian_of_df: GUARDIAN_OF edges DataFrame
        compound_df: Compound relationship edges (CHILD_OF) DataFrame
    """
    logging.info("="*80)
    logging.info(f"Writing edges to: {output_path}")
    logging.info("="*80)
    
    def _neo4j_edge_df(edge_df):
        """Rename edge columns to neo4j-admin import format"""
        return edge_df.select(
            F.col("source").alias(":START_ID"),
            F.col("target").alias(":END_ID"),
            F.col("type").alias(":TYPE"),
            "source_type",
            "confidence",
            "lookup_id"
        )

    def _write_edge_csv(edge_df, path, num_partitions=2):
        """Write edge DataFrame to CSV with neo4j-admin headers"""
        (
            _neo4j_edge_df(edge_df)
            .repartition(num_partitions)
            .write
            .mode("overwrite")
            .option("header", "true")
            .option("quote", '"')
            .option("escape", '"')
            .csv(path)
        )

    try:
        # Write CHILD_OF edges (including compound)
        all_child_of = child_of_df.union(compound_df)
        child_of_path = f"{output_path}/edges/child_of"
        _write_edge_csv(all_child_of, child_of_path, num_partitions=4)
        logging.info(f"CHILD_OF edges written to: {child_of_path}")

        # Write SPOUSE_OF edges
        spouse_of_path = f"{output_path}/edges/spouse_of"
        _write_edge_csv(spouse_of_df, spouse_of_path, num_partitions=2)
        logging.info(f"SPOUSE_OF edges written to: {spouse_of_path}")

        # Write SIBLING_OF edges
        sibling_of_path = f"{output_path}/edges/sibling_of"
        _write_edge_csv(sibling_of_df, sibling_of_path, num_partitions=2)
        logging.info(f"SIBLING_OF edges written to: {sibling_of_path}")

        # Write GRANDCHILD_OF edges
        grandchild_of_path = f"{output_path}/edges/grandchild_of"
        _write_edge_csv(grandchild_of_df, grandchild_of_path, num_partitions=2)
        logging.info(f"GRANDCHILD_OF edges written to: {grandchild_of_path}")

        # Write STEP_CHILD_OF edges
        step_child_of_path = f"{output_path}/edges/step_child_of"
        _write_edge_csv(stepchild_of_df, step_child_of_path, num_partitions=2)
        logging.info(f"STEP_CHILD_OF edges written to: {step_child_of_path}")

        # Write GUARDIAN_OF edges
        guardian_of_path = f"{output_path}/edges/guardian_of"
        _write_edge_csv(guardian_of_df, guardian_of_path, num_partitions=2)
        logging.info(f"GUARDIAN_OF edges written to: {guardian_of_path}")

        # Write statistics (single groupBy on union — 1 action instead of 12+)
        write_statistics(spark_session, output_path, all_child_of, spouse_of_df, sibling_of_df, grandchild_of_df, stepchild_of_df, guardian_of_df)
        
    except Exception as e:
        logging.info("="*80)
        logging.error(f"Failed to write edges: {str(e)}")
        logging.info("="*80)
        raise



def run(df, persons_path, csv_output_path, spark_session):
    """Execute the complete transformation pipeline"""
    logging.info("="*80)
    logging.info("Starting Relationship Transformation")
    logging.info("="*80)
    
    start_time = datetime.now()
    
    try:
        # Step 1: Read source relationships
        # relationships_df = read_source_relationships(spark_session, source_path)
        
        # Step 2: Preprocess relationship names
        processed_relationships_df = preprocess_relationship_names(df)

        # Step 3: Load valid person IDs — cache since used in 7 validate_edges calls
        person_ids = load_person_ids(persons_path, spark_session)
        person_ids.cache()

        # Step 4: Map relationship types — cache since scanned 7+ times (once per edge type)
        mapped_df = map_relationship_types(processed_relationships_df, csv_output_path)
        mapped_df.cache()
        
        # Step 5: Create all edge types
        child_of_edges = create_child_of_edges(mapped_df)
        spouse_of_edges = create_spouse_of_edges(mapped_df)
        sibling_of_edges = create_sibling_of_edges(mapped_df)
        grandchild_of_edges = create_grandchild_of_edges(mapped_df)
        step_child_of_edges = create_step_child_of_edges(mapped_df)
        guardian_of_edges = create_guardian_of_edges(mapped_df)
        compound_edges = create_compound_edges(mapped_df)

        # Step 6: Resolve directional duplicates (priority-based dedup)
        child_of_edges = resolve_directional_duplicates(child_of_edges)
        grandchild_of_edges = resolve_directional_duplicates(grandchild_of_edges)
        step_child_of_edges = resolve_directional_duplicates(step_child_of_edges)

        # Step 7: Validate edges
        child_of_edges = validate_edges(child_of_edges, person_ids)
        spouse_of_edges = validate_edges(spouse_of_edges, person_ids)
        sibling_of_edges = validate_edges(sibling_of_edges, person_ids)
        grandchild_of_edges = validate_edges(grandchild_of_edges, person_ids)
        step_child_of_edges = validate_edges(step_child_of_edges, person_ids)
        guardian_of_edges = validate_edges(guardian_of_edges, person_ids)
        compound_edges = validate_edges(compound_edges, person_ids)

        # Step 8: Write output
        write_output(spark_session, csv_output_path, child_of_edges, spouse_of_edges, sibling_of_edges, grandchild_of_edges, step_child_of_edges, guardian_of_edges, compound_edges)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logging.info("="*80)
        logging.info(f"Relationship Transformation completed in {duration:.2f} seconds")
        logging.info("="*80)
        
        return child_of_edges, spouse_of_edges, sibling_of_edges, grandchild_of_edges, step_child_of_edges, guardian_of_edges, compound_edges
        
    except Exception as e:
        logging.info("="*80)
        logging.error(f"Transformation failed: {str(e)}", exc_info=True)
        logging.info("="*80)
        raise


def main(spark_session):
    try:
       
        source_path = str(spark_job_args.get("source_path"))
        logging.info("="*80)
        logging.info("The parquet files path is --> {}".format(source_path))
        logging.info("="*80)


        persons_path = str(spark_job_args.get("persons_path"))
        logging.info("="*80)
        logging.info("The persons files path is --> {}".format(persons_path))
        logging.info("="*80)


        csv_output_path = str(spark_job_args.get("output_path"))
        logging.info("="*80)
        logging.info("The CSV output path for Neo4j is --> {}".format(csv_output_path))
        logging.info("="*80)

        df = spark.read.parquet(source_path)

        child_of_edges, spouse_of_edges, sibling_of_edges, grandchild_of_edges, step_child_of_edges, guardian_of_edges, compound_edges = run(df, persons_path, csv_output_path, spark_session)
        
        # time.sleep(120)
    except Exception as ex:
        logging.info("="*80)
        logging.error(ex)
        logging.info("="*80)
        sc.stop()
        raise Exception('! Something went wrong with this job')

    finally:
        logging.info('Stopping...')
        sc.stop()


if __name__ == '__main__':
    # Provide Spark Session additional config options as dictionary
    spark_options = {
        "spark.sql.shuffle.partitions": "80",                       # 2x core count (40 cores)
        "spark.sql.adaptive.enabled": "true",                        # enable AQE
        "spark.sql.adaptive.coalescePartitions.enabled": "true",     # auto-coalesce small partitions
        "spark.sql.autoBroadcastJoinThreshold": "104857600",         # 100MB (up from 10MB default)
        "spark.sql.catalog.my_catalog.write.distribution-mode": "hash",
        "write.target-file-size-bytes": "134217728",
        "spark.sql.iceberg.fanout-enabled": "true",
    }
    spark, sc, spark_app_name, spark_job_args, cluster_details_spark_args, minio_s3_credentials,\
    credentials  = CommonProcessHelperUtils.\
                                            initialize_read_arguments(spark_options=spark_options, mount_bucket_name=MOUNT_BUCKET)
    logging.info(f"spark_job_args: {spark_job_args}")

    main(spark)
    exit()