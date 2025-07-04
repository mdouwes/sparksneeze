"""Append strategy implementation."""

from typing import TYPE_CHECKING, Optional
from .base import BaseStrategy, SparkSneezeResult

if TYPE_CHECKING:
    from ..data_sources import DataSource
    from ..data_targets import DataTarget
    from ..metadata import MetadataConfig


class Append(BaseStrategy):
    """Append strategy for adding new data to existing target without removal.

    The Append strategy adds all source data to the target while preserving existing
    records. It supports automatic schema evolution to handle structural changes
    in the source data over time.

    Key characteristics:
    - Preserves all existing target data
    - Adds all source records to target
    - Supports schema evolution (expansion/shrinkage)
    - Maintains separate metadata hashes for existing vs new data
    - No duplicate detection or removal

    Args:
        auto_expand: Automatically add new columns from source to target schema.
                    Existing records get NULL values for new columns. Default: True
        auto_shrink: Automatically remove columns from target that don't exist in source.
                    This permanently removes data. Default: False
        metadata_config: Custom metadata configuration. Uses defaults if None.

    Raises:
        ValueError: If both auto_expand and auto_shrink are disabled and schemas differ
        RuntimeError: If target cannot be written to or source cannot be read

    Examples:
        Basic append with schema expansion:

        >>> from sparksneeze.strategy import Append
        >>> strategy = Append(auto_expand=True, auto_shrink=False)
        >>> runner = SparkSneezeRunner(source_df, "target.delta", strategy)
        >>> result = runner.run()

        Conservative append (no schema changes):

        >>> strategy = Append(auto_expand=False, auto_shrink=False)
        >>> # Will fail if schemas don't match exactly

        Aggressive append with full schema evolution:

        >>> strategy = Append(auto_expand=True, auto_shrink=True)
        >>> # Adds new columns AND removes missing columns (data loss possible)

        With custom metadata:

        >>> from sparksneeze.metadata import MetadataConfig
        >>> config = MetadataConfig(valid_from_column="_start_time")
        >>> strategy = Append(metadata_config=config)

    Note:
        When auto_shrink=True, columns that exist in the target but not in the source
        will be permanently removed, causing data loss. Use with caution in production.
    """

    def __init__(
        self,
        auto_expand: bool = True,
        auto_shrink: bool = False,
        metadata_config: Optional["MetadataConfig"] = None,
    ) -> None:
        """Initialize Append strategy with schema evolution options.

        Args:
            auto_expand: Enable automatic schema expansion for new source columns
            auto_shrink: Enable automatic schema shrinkage for removed source columns
            metadata_config: Custom metadata field configuration
        """
        super().__init__(metadata_config)
        self._init_schema_evolution(auto_expand, auto_shrink)

    def execute(self, source: "DataSource", target: "DataTarget") -> SparkSneezeResult:
        """Execute the Append strategy."""

        self.logger.info("Starting Append strategy")

        try:
            # Get source dataframe
            source_df = source.to_dataframe()

            # For Append strategy, ALWAYS preserve existing data regardless of schema evolution
            # Only source data should be processed through schema evolution
            if target.exists():
                # Read existing target data BEFORE any schema evolution to preserve original hashes
                existing_data = target.read()

                # Handle schema evolution using base class method (only affects source data)
                df_with_metadata = self._handle_schema_evolution(source_df, target)

                # Combine existing data (preserved) and new data (evolved)
                if existing_data.count() > 0:
                    # Align schemas between existing and new data for union
                    final_schema = df_with_metadata.schema
                    aligned_existing = self._align_existing_data_to_evolved_schema(
                        existing_data, final_schema
                    )

                    # Union existing (preserved) + new (evolved) data
                    combined_data = aligned_existing.union(df_with_metadata)

                    # Write combined result using overwrite mode since we're managing the combination
                    target.write(combined_data, "overwrite")
                    final_df = combined_data
                else:
                    # No existing data, just write new data
                    target.write(df_with_metadata, "append")
                    final_df = df_with_metadata
            else:
                # No existing target, standard flow
                df_with_metadata = self._handle_schema_evolution(source_df, target)
                target.write(df_with_metadata, "append")
                final_df = df_with_metadata

            # Get row count for result message
            row_count = self._get_row_count_safely(final_df)

            return self._create_success_result(
                "Append completed successfully", final_df, row_count
            )

        except Exception as e:
            return self._create_error_result("Append failed", e)

    def _align_existing_data_to_evolved_schema(self, existing_df, target_schema):
        """Align existing DataFrame with evolved target schema while preserving metadata.

        This method handles the case where auto_shrink has removed columns from the target,
        but existing data still needs to be aligned with the new schema structure.

        Args:
            existing_df: Existing target DataFrame with original schema
            target_schema: Evolved target schema after auto_shrink/auto_expand

        Returns:
            DataFrame aligned with target schema, preserving original metadata
        """
        from pyspark.sql.functions import lit

        # Get column names from both schemas
        existing_cols = set(existing_df.columns)
        target_cols = {field.name for field in target_schema.fields}

        # Start with existing DataFrame
        aligned_df = existing_df

        # Add missing columns (from schema expansion) with null values
        missing_cols = target_cols - existing_cols
        for col_name in missing_cols:
            # Find the field definition in target schema
            field = next(
                field for field in target_schema.fields if field.name == col_name
            )
            aligned_df = aligned_df.withColumn(col_name, lit(None).cast(field.dataType))

        # Remove extra columns (from schema shrinkage) - these were already dropped by schema evolution
        # The existing data should only keep columns that exist in the target schema
        final_cols = [col for col in aligned_df.columns if col in target_cols]
        aligned_df = aligned_df.select(final_cols)

        # Ensure column order matches target schema
        target_col_order = [field.name for field in target_schema.fields]
        aligned_df = aligned_df.select(*target_col_order)

        return aligned_df
