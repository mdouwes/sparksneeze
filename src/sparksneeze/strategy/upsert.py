"""Upsert strategy implementation."""

from typing import List, Union, TYPE_CHECKING, Optional
from .base import BaseStrategy, SparkSneezeResult

if TYPE_CHECKING:
    from pyspark.sql import DataFrame
    from ..data_sources import DataSource
    from ..data_targets import DataTarget
    from ..metadata import MetadataConfig


class Upsert(BaseStrategy):
    """Load data from the source entity into the target entity by using one or more keys.

    After the key comparison, the following happens:
    - New keys have their records inserted into the target entity
    - Existing keys will have their records updated in the target entity
    - (Optional) Nonexistent keys will have their records removed from the target entity
    """

    def __init__(
        self,
        key: Union[str, List[str]],
        auto_expand: bool = True,
        auto_shrink: bool = False,
        metadata_config: Optional["MetadataConfig"] = None,
    ) -> None:
        super().__init__(metadata_config)
        self._init_schema_evolution(auto_expand, auto_shrink)
        self.key: List[str] = key if isinstance(key, list) else [key]

    def execute(self, source: "DataSource", target: "DataTarget") -> SparkSneezeResult:
        """Execute the Upsert strategy."""

        self.logger.info("Starting Upsert strategy")

        try:
            # Get source dataframe
            source_df = source.to_dataframe()

            # Handle schema evolution with key consideration
            df_with_metadata = self._handle_schema_evolution(
                source_df, target, key_columns=self.key
            )

            # Get row count for result message
            row_count = self._get_row_count_safely(df_with_metadata)

            # Check if target supports native merge operations
            if target.supports_merge():
                self.logger.info("Using native merge operations for upsert")
                self._perform_native_merge(df_with_metadata, target)
            else:
                self.logger.info(
                    "Target doesn't support merge, using fallback DataFrame operations"
                )
                self._perform_fallback_upsert(df_with_metadata, target)

            return self._create_success_result(
                "Upsert completed successfully", df_with_metadata, row_count
            )

        except Exception as e:
            return self._create_error_result("Upsert failed", e)

    def _perform_native_merge(
        self, source_df: "DataFrame", target: "DataTarget"
    ) -> None:
        """Perform upsert using target's native merge operations.

        Args:
            source_df: Source DataFrame with metadata already applied
            target: Target that supports merge operations
        """
        # Generate merge condition based on key columns
        merge_condition = " AND ".join(
            [f"target.{key} = source.{key}" for key in self.key]
        )

        # Get all non-key columns for update/insert operations
        all_columns = source_df.columns
        non_key_columns = [col for col in all_columns if col not in self.key]

        # Build column mappings for when matched (update) and when not matched (insert)
        when_matched_update = {col: f"source.{col}" for col in non_key_columns}
        when_not_matched_insert = {col: f"source.{col}" for col in all_columns}

        # Perform the merge operation
        target.merge(
            source_df=source_df,
            merge_condition=merge_condition,
            when_matched_update=when_matched_update,
            when_not_matched_insert=when_not_matched_insert,
        )

    def _perform_fallback_upsert(
        self, source_df: "DataFrame", target: "DataTarget"
    ) -> None:
        """Perform upsert using DataFrame operations for targets that don't support merge.

        Args:
            source_df: Source DataFrame with metadata already applied
            target: Target that doesn't support merge operations
        """
        # Read existing target data
        existing_df = target.read()

        # Find records to keep from target (keys that don't exist in source)
        keeps_df = existing_df.join(
            source_df.select(*self.key).distinct(), on=self.key, how="left_anti"
        )

        # All source records become updates/inserts
        # (source takes precedence for any key conflicts)
        upserts_df = source_df

        # Union keeps + upserts to create final result
        final_df = keeps_df.unionByName(upserts_df)

        # Write the final result, overwriting the target
        target.write(final_df, mode="overwrite")
