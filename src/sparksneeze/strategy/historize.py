"""Historize strategy implementation."""

from typing import List, Union, TYPE_CHECKING, Optional
from datetime import datetime
from .base import BaseStrategy, SparkSneezeResult

if TYPE_CHECKING:
    from pyspark.sql import DataFrame
    from ..data_sources import DataSource
    from ..data_targets import DataTarget
    from ..metadata import MetadataConfig


class Historize(BaseStrategy):
    """Load data from the source entity into the target entity by using one or more keys and add validity time tracking attributes.

    The metadata columns to store a valid from date, a valid to date and active attribute will be added to the target entity,
    regardless of the auto_expand parameter.
    """

    def __init__(
        self,
        key: Union[str, List[str]],
        auto_expand: bool = True,
        auto_shrink: bool = False,
        valid_from: Optional[datetime] = None,
        valid_to: Optional[datetime] = None,
        metadata_config: Optional["MetadataConfig"] = None,
    ) -> None:
        super().__init__(metadata_config)
        self._init_schema_evolution(auto_expand, auto_shrink)
        self.key: List[str] = key if isinstance(key, list) else [key]
        # Store datetime values for use in strategy execution
        self.valid_from = valid_from
        self.valid_to = valid_to

    def execute(self, source: "DataSource", target: "DataTarget") -> SparkSneezeResult:
        """Execute the Historize strategy."""

        self.logger.info("Starting Historize strategy")

        try:
            # Get source dataframe
            source_df = source.to_dataframe()

            # Handle schema evolution with key consideration
            df_with_metadata = self._handle_schema_evolution(
                source_df,
                target,
                key_columns=self.key,
                valid_from=self.valid_from,
                valid_to=self.valid_to,
            )

            # Get row count for result message
            row_count = self._get_row_count_safely(df_with_metadata)

            # Check if target supports native merge operations
            if target.supports_merge():
                self.logger.info("Using native merge operations for historize")
                self._perform_native_historize(df_with_metadata, target)
            else:
                self.logger.info(
                    "Target doesn't support merge, using fallback DataFrame operations"
                )
                self._perform_fallback_historize(df_with_metadata, target)

            return self._create_success_result(
                "Historize completed successfully", df_with_metadata, row_count
            )

        except Exception as e:
            return self._create_error_result("Historize failed", e)

    def _perform_native_historize(
        self, source_df: "DataFrame", target: "DataTarget"
    ) -> None:
        """Perform historize using target's native merge operations with hash-based change detection.

        Args:
            source_df: Source DataFrame with metadata already applied
            target: Target that supports merge operations
        """
        # Handle empty target case
        if not target.exists():
            self.logger.info(
                "Target doesn't exist, inserting all source records as new historical records"
            )
            target.write(source_df, mode="overwrite")
            return

        # Read existing target data
        try:
            existing_df = target.read()
            if existing_df.count() == 0:
                self.logger.info(
                    "Target is empty, inserting all source records as new historical records"
                )
                target.write(source_df, mode="overwrite")
                return
        except Exception as e:
            # If we can't read the target, treat it as empty
            self.logger.warning(
                f"Cannot read target (treating as empty): {e}, inserting all source records"
            )
            target.write(source_df, mode="overwrite")
            return

        # Get metadata column names from config
        config = self.metadata_applier.config
        valid_to_col = config.prefixed_valid_to
        active_col = config.prefixed_active
        row_hash_col = config.prefixed_row_hash

        try:
            # Native SCD2 implementation using hash-based merge operations
            self.logger.info("Performing hash-based native merge for SCD2 historize")

            # Primary merge operation handles:
            # 1. Close changed records (hash differs)
            # 2. Close removed records (keys not in source)
            # 3. Insert new records (keys not in target)
            self._perform_hash_based_merge(
                source_df, target, row_hash_col, valid_to_col, active_col
            )

            # Follow-up: Insert new versions of changed records
            self._insert_changed_record_versions(source_df, target, row_hash_col)

            self.logger.info("Hash-based native SCD2 historize completed successfully")

        except Exception as e:
            self.logger.warning(
                f"Native merge operations failed ({str(e)}), falling back to DataFrame operations"
            )
            # Fall back to the proven DataFrame implementation
            self._perform_fallback_historize(source_df, target)

    def _perform_fallback_historize(
        self, source_df: "DataFrame", target: "DataTarget"
    ) -> None:
        """Perform historize using hash-based discrete CRUD operations.

        Args:
            source_df: Source DataFrame with metadata already applied
            target: Target that doesn't support merge operations or fallback needed
        """

        # Handle empty target case
        if not target.exists():
            self.logger.info(
                "Target doesn't exist, inserting all source records as new historical records"
            )
            target.write(source_df, mode="overwrite")
            return

        # Read existing target data
        try:
            existing_df = target.read()
            if existing_df.count() == 0:
                self.logger.info(
                    "Target is empty, inserting all source records as new historical records"
                )
                target.write(source_df, mode="overwrite")
                return
        except Exception as e:
            # If we can't read the target, treat it as empty
            self.logger.warning(
                f"Cannot read target (treating as empty): {e}, inserting all source records"
            )
            target.write(source_df, mode="overwrite")
            return

        # Get metadata column names from config
        config = self.metadata_applier.config
        valid_to_col = config.prefixed_valid_to
        active_col = config.prefixed_active
        row_hash_col = config.prefixed_row_hash

        self.logger.info(
            "Performing hash-based fallback historize using discrete CRUD operations"
        )

        # Use hash-based change detection to categorize records efficiently
        record_categories = self._categorize_records_by_hash(
            source_df, existing_df, row_hash_col, active_col
        )

        # Execute discrete CRUD operations in sequence
        self._execute_fallback_crud_sequence(
            existing_df, record_categories, target, valid_to_col, active_col
        )

    def _categorize_records_by_hash(
        self,
        source_df: "DataFrame",
        existing_df: "DataFrame",
        row_hash_col: str,
        active_col: str,
    ) -> dict:
        """Categorize records using hash-based change detection.

        Returns dict with categories: new_records, changed_records, unchanged_records, removed_records
        """
        from pyspark.sql.functions import col

        # Get currently active records from target
        active_target_df = existing_df.filter(col(active_col))

        # Get distinct keys from source and active target
        source_keys = source_df.select(*self.key).distinct()
        active_target_keys = active_target_df.select(*self.key).distinct()

        # Find new records (keys in source but not in active target)
        new_records = source_df.join(active_target_keys, on=self.key, how="left_anti")

        # Find removed records (keys in active target but not in source)
        removed_records = active_target_df.join(
            source_keys, on=self.key, how="left_anti"
        )

        # For existing keys, compare hashes to find changed vs unchanged
        existing_comparison = source_df.alias("src").join(
            active_target_df.alias("tgt"), on=self.key, how="inner"
        )

        # Changed records: same key but different hash
        changed_records = existing_comparison.filter(
            col(f"src.{row_hash_col}") != col(f"tgt.{row_hash_col}")
        ).select([col(f"tgt.{c}").alias(c) for c in active_target_df.columns])

        # Unchanged records: same key and same hash
        unchanged_records = existing_comparison.filter(
            col(f"src.{row_hash_col}") == col(f"tgt.{row_hash_col}")
        ).select([col(f"tgt.{c}").alias(c) for c in active_target_df.columns])

        # Get source versions of changed records for insertion
        changed_source_records = existing_comparison.filter(
            col(f"src.{row_hash_col}") != col(f"tgt.{row_hash_col}")
        ).select([col(f"src.{c}").alias(c) for c in source_df.columns])

        return {
            "new_records": new_records,
            "changed_records": changed_records,
            "unchanged_records": unchanged_records,
            "removed_records": removed_records,
            "changed_source_records": changed_source_records,
        }

    def _execute_fallback_crud_sequence(
        self,
        existing_df: "DataFrame",
        categories: dict,
        target: "DataTarget",
        valid_to_col: str,
        active_col: str,
    ) -> None:
        """Execute the discrete CRUD operations for SCD2 historize."""
        from pyspark.sql.functions import col, lit

        final_dfs = []

        # Helper function to check if DataFrame has data - using collect for reliability
        def has_data(df):
            try:
                return len(df.head(1)) > 0
            except Exception as e:
                self.logger.debug(f"Failed to check if DataFrame has data: {e}")
                return False

        # Preserve existing historical records (already inactive)
        historical_records = existing_df.filter(~col(active_col))
        if has_data(historical_records):
            final_dfs.append(historical_records)

        # Keep unchanged active records as-is
        unchanged_records = categories["unchanged_records"]
        if has_data(unchanged_records):
            final_dfs.append(unchanged_records)

        # Close changed records (mark as inactive)
        changed_records = categories["changed_records"]
        if has_data(changed_records):
            # Use metadata applier's effective valid_from for deterministic timestamps
            close_timestamp = self.metadata_applier.config.get_effective_valid_from(
                self.valid_from
            )
            closed_changed_records = changed_records.withColumn(
                valid_to_col, lit(close_timestamp)
            ).withColumn(active_col, lit(False))
            final_dfs.append(closed_changed_records)

        # Close removed records (mark as inactive)
        removed_records = categories["removed_records"]
        if has_data(removed_records):
            # Use metadata applier's effective valid_from for deterministic timestamps
            close_timestamp = self.metadata_applier.config.get_effective_valid_from(
                self.valid_from
            )
            closed_removed_records = removed_records.withColumn(
                valid_to_col, lit(close_timestamp)
            ).withColumn(active_col, lit(False))
            final_dfs.append(closed_removed_records)

        # Add new records
        new_records = categories["new_records"]
        if has_data(new_records):
            final_dfs.append(new_records)

        # Add new versions of changed records
        changed_source_records = categories["changed_source_records"]
        if has_data(changed_source_records):
            final_dfs.append(changed_source_records)

        # Union all DataFrames and write final result
        if final_dfs:
            final_df = final_dfs[0]
            for df in final_dfs[1:]:
                final_df = final_df.unionByName(df, allowMissingColumns=True)
            target.write(final_df, mode="overwrite")
        else:
            # Fallback - write existing data
            target.write(existing_df, mode="overwrite")

    def _perform_hash_based_merge(
        self,
        source_df: "DataFrame",
        target: "DataTarget",
        row_hash_col: str,
        valid_to_col: str,
        active_col: str,
    ) -> None:
        """Perform primary merge operation using hash-based change detection.

        This single merge handles:
        1. Close changed records (keys match but hash differs)
        2. Close removed records (keys in target but not in source)
        3. Insert new records (keys not in target)

        Args:
            source_df: Source DataFrame with metadata
            target: Target that supports merge operations
            row_hash_col: Name of row hash metadata column
            valid_to_col: Name of valid_to metadata column
            active_col: Name of active metadata column
        """

        # Build merge condition: match on keys where target is active
        key_conditions = [f"target.{key} = source.{key}" for key in self.key]
        active_condition = f"target.{active_col} = true"
        merge_condition = f"({' AND '.join(key_conditions)}) AND {active_condition}"

        # When matched and hash differs: close the record (it changed)
        hash_differs_condition = f"target.{row_hash_col} != source.{row_hash_col}"
        when_matched_update_changed = {
            valid_to_col: f"source.{valid_to_col}",  # Use source's valid_from as close time
            active_col: "false",
        }

        # When not matched by source: close removed records
        effective_valid_from = self.metadata_applier.config.get_effective_valid_from(
            self.valid_from
        )
        when_not_matched_by_source_update = {
            valid_to_col: f"'{effective_valid_from}'",
            active_col: "false",
        }

        # When not matched by target: insert new records
        when_not_matched_insert = {col: f"source.{col}" for col in source_df.columns}

        # Execute the merge with hash-based logic
        target.merge(
            source_df=source_df,
            merge_condition=merge_condition,
            when_matched_update=when_matched_update_changed,
            when_matched_condition=hash_differs_condition,
            when_not_matched_by_source_update=when_not_matched_by_source_update,
            when_not_matched_by_source_condition=f"target.{active_col} = true",
            when_not_matched_insert=when_not_matched_insert,
        )

    def _insert_changed_record_versions(
        self, source_df: "DataFrame", target: "DataTarget", row_hash_col: str
    ) -> None:
        """Insert new versions of records that changed (have different hashes).

        This is the follow-up operation after the primary merge that closed old versions.
        We only insert new versions for keys where the hash actually changed.

        Args:
            source_df: Source DataFrame with metadata
            target: Target that supports merge operations
            row_hash_col: Name of row hash metadata column
        """
        # Get existing target data to identify which records changed
        existing_df = target.read()

        # Get the latest version of each key from target (could be active or just closed)
        from pyspark.sql import Window
        from pyspark.sql.functions import row_number, desc, col

        # Window to get latest record per key
        window = Window.partitionBy(*self.key).orderBy(
            desc(self.metadata_applier.config.prefixed_valid_from)
        )
        latest_target_df = (
            existing_df.withColumn("rn", row_number().over(window))
            .filter(col("rn") == 1)
            .drop("rn")
        )

        # Find records where hash changed by joining source with latest target versions
        changed_records = (
            source_df.alias("src")
            .join(latest_target_df.alias("tgt"), on=self.key, how="inner")
            .filter(col(f"src.{row_hash_col}") != col(f"tgt.{row_hash_col}"))
            .select([col(f"src.{c}").alias(c) for c in source_df.columns])
        )

        # Insert only the changed records as new active versions
        if changed_records.count() > 0:
            target.write(changed_records, mode="append")
