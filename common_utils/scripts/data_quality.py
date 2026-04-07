"""
Data Quality Utilities
Validation and quality checks for family graph ETL
"""
from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from typing import Dict, List, Tuple
from common_utils.scripts.common_utilities import CommonLogging

logger = CommonLogging.get_logger()


class DataQualityChecker:
    """Performs data quality checks and generates reports"""
    
    def __init__(self, spark_session):
        self.spark = spark_session
    
    def check_null_values(self, df: DataFrame, critical_columns: List[str]) -> Dict:
        """
        Check for null values in critical columns.
        Uses single-pass aggregation instead of per-column .count() calls.

        Args:
            df: Input DataFrame
            critical_columns: List of columns that shouldn't have nulls

        Returns:
            Dictionary with null counts per column
        """
        logger.info("Checking null values in critical columns")

        # Build all aggregation expressions for a single-pass evaluation
        agg_exprs = [F.count("*").alias("total")]
        valid_columns = [col for col in critical_columns if col in df.columns]
        for col_name in valid_columns:
            agg_exprs.append(
                F.sum(F.when(F.col(col_name).isNull(), 1).otherwise(0)).alias(f"null_{col_name}")
            )

        # Single Spark action instead of 1 + N
        result = df.select(*agg_exprs).first()
        total_rows = result["total"]

        null_counts = {}
        for col_name in valid_columns:
            null_count = result[f"null_{col_name}"]
            null_pct = (null_count / total_rows * 100) if total_rows > 0 else 0
            null_counts[col_name] = {
                'count': null_count,
                'percentage': round(null_pct, 2)
            }

            if null_count > 0:
                logger.warning(
                    f"Column '{col_name}' has {null_count} null values ({null_pct:.2f}%)"
                )

        return null_counts
    
    def check_duplicates(
        self, 
        df: DataFrame, 
        key_columns: List[str]
    ) -> Tuple[int, DataFrame]:
        """
        Check for duplicate records
        
        Args:
            df: Input DataFrame
            key_columns: Columns that define uniqueness
            
        Returns:
            Tuple of (duplicate_count, duplicate_records_df)
        """
        logger.info(f"Checking duplicates on columns: {key_columns}")
        
        # Find duplicates
        duplicates = (
            df.groupBy(key_columns)
            .count()
            .filter(F.col("count") > 1)
            .orderBy(F.desc("count"))
        )
        
        dup_count = duplicates.count()
        
        if dup_count > 0:
            logger.warning(f"Found {dup_count} duplicate groups")
        else:
            logger.info("No duplicates found")
        
        return dup_count, duplicates
    
    def check_orphaned_relationships(
        self,
        persons_df: DataFrame,
        relationships_df: DataFrame
    ) -> Dict:
        """
        Check for relationships pointing to non-existent persons
        
        Args:
            persons_df: DataFrame with person nodes
            relationships_df: DataFrame with relationship edges
            
        Returns:
            Dictionary with orphaned relationship counts
        """
        logger.info("Checking for orphaned relationships")
        
        # Get all person IDs
        person_ids = persons_df.select("person_no").distinct()
        
        # Check source persons
        orphaned_sources = (
            relationships_df
            .select("person_no")
            .distinct()
            .join(person_ids, on="person_no", how="left_anti")
        )
        
        orphaned_source_count = orphaned_sources.count()
        
        # Check target persons
        orphaned_targets = (
            relationships_df
            .select("rltv_person_no")
            .distinct()
            .join(
                person_ids.withColumnRenamed("person_no", "rltv_person_no"),
                on="rltv_person_no",
                how="left_anti"
            )
        )
        
        orphaned_target_count = orphaned_targets.count()
        
        if orphaned_source_count > 0:
            logger.warning(
                f"Found {orphaned_source_count} relationships with non-existent source persons"
            )
        
        if orphaned_target_count > 0:
            logger.warning(
                f"Found {orphaned_target_count} relationships with non-existent target persons"
            )
        
        return {
            'orphaned_sources': orphaned_source_count,
            'orphaned_targets': orphaned_target_count,
            'source_ids': orphaned_sources,
            'target_ids': orphaned_targets
        }
    
    def validate_relationships(self, df: DataFrame) -> Dict:
        """
        Validate relationship data quality
        
        Args:
            df: Relationships DataFrame
            
        Returns:
            Dictionary with validation results
        """
        logger.info("Validating relationship data")
        
        results = {}
        
        # Check self-loops (person related to themselves)
        self_loops = df.filter(F.col("person_no") == F.col("rltv_person_no"))
        self_loop_count = self_loops.count()
        results['self_loops'] = self_loop_count
        
        if self_loop_count > 0:
            logger.warning(f"Found {self_loop_count} self-loop relationships")
        
        # Check invalid confidence levels
        invalid_confidence = df.filter(
            (F.col("relation_lvl").isNull()) | 
            (F.col("relation_lvl") < 0)
        )
        invalid_conf_count = invalid_confidence.count()
        results['invalid_confidence'] = invalid_conf_count
        
        if invalid_conf_count > 0:
            logger.warning(f"Found {invalid_conf_count} invalid confidence levels")
        
        # Check for missing relationship names
        missing_rel_names = df.filter(
            F.col("relation_nm").isNull() | 
            (F.trim(F.col("relation_nm")) == "")
        )
        missing_name_count = missing_rel_names.count()
        results['missing_rel_names'] = missing_name_count
        
        if missing_name_count > 0:
            logger.warning(f"Found {missing_name_count} relationships with missing names")
        
        return results
    
    def generate_summary_stats(self, df: DataFrame, name: str) -> Dict:
        """
        Generate summary statistics for a DataFrame
        
        Args:
            df: Input DataFrame
            name: Dataset name for logging
            
        Returns:
            Dictionary with summary statistics
        """
        logger.info(f"Generating summary statistics for {name}")
        
        total_rows = df.count()
        stats = {
            'name': name,
            'total_rows': total_rows,
            'total_columns': len(df.columns),
            'columns': df.columns
        }

        logger.info(f"{name} statistics: {stats['total_rows']} rows, {stats['total_columns']} columns")
        
        return stats
    
    def check_person_attributes(self, df: DataFrame) -> Dict:
        """
        Validate person attribute data quality.
        Uses single-pass aggregation instead of separate .count() calls.

        Args:
            df: Persons DataFrame

        Returns:
            Dictionary with validation results
        """
        logger.info("Validating person attributes")

        # Build aggregation expressions for single-pass evaluation
        agg_exprs = []
        has_gender = 'spm_gender' in df.columns
        has_name = 'Person_nm' in df.columns

        if has_gender:
            agg_exprs.append(
                F.sum(F.when(~F.col("spm_gender").isin(['M', 'F']), 1).otherwise(0)).alias("invalid_genders")
            )
        if has_name:
            agg_exprs.append(
                F.sum(F.when(
                    F.col("Person_nm").isNull() | (F.trim(F.col("Person_nm")) == ""), 1
                ).otherwise(0)).alias("empty_names")
            )

        results = {}
        if agg_exprs:
            row = df.select(*agg_exprs).first()

            if has_gender:
                results['invalid_genders'] = row["invalid_genders"]
                if results['invalid_genders'] > 0:
                    logger.warning(
                        f"Found {results['invalid_genders']} persons with invalid gender values"
                    )

            if has_name:
                results['empty_names'] = row["empty_names"]
                if results['empty_names'] > 0:
                    logger.warning(f"Found {results['empty_names']} persons with empty names")

        return results
    
    def generate_quality_report(
        self,
        persons_df: DataFrame,
        relationships_df: DataFrame,
        output_path: str
    ):
        """
        Generate comprehensive data quality report
        
        Args:
            persons_df: Persons DataFrame
            relationships_df: Relationships DataFrame
            output_path: Path to save the report
        """
        logger.info("Generating comprehensive data quality report")
        
        report = {
            'timestamp': F.current_timestamp(),
            'persons': {},
            'relationships': {},
            'cross_validation': {}
        }
        
        # Persons checks
        report['persons']['summary'] = self.generate_summary_stats(persons_df, "Persons")
        report['persons']['null_checks'] = self.check_null_values(
            persons_df, 
            ['person_no', 'Person_nm', 'spm_gender']
        )
        report['persons']['duplicates'] = self.check_duplicates(
            persons_df, 
            ['person_no']
        )[0]
        report['persons']['attribute_validation'] = self.check_person_attributes(persons_df)
        
        # Relationships checks
        report['relationships']['summary'] = self.generate_summary_stats(
            relationships_df, 
            "Relationships"
        )
        report['relationships']['null_checks'] = self.check_null_values(
            relationships_df,
            ['person_no', 'rltv_person_no', 'relation_nm']
        )
        report['relationships']['validation'] = self.validate_relationships(relationships_df)
        
        # Cross-validation
        report['cross_validation']['orphaned'] = self.check_orphaned_relationships(
            persons_df,
            relationships_df
        )
        
        # Save report as JSON
        import json
        report_json = json.dumps(report, default=str, indent=2)
        
        logger.info(f"Data quality report generated: {output_path}")
        
        return report
