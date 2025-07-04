"""Truncate strategy implementation."""

from typing import TYPE_CHECKING, Optional
from .base import BaseStrategy, SparkSneezeResult

if TYPE_CHECKING:
    from ..data_sources import DataSource
    from ..data_targets import DataTarget
    from ..metadata import MetadataConfig


class Truncate(BaseStrategy):
    """Clear the target entity and load the data from the source entity.

    By default it automatically expands the schema when new columns are found.
    Columns that are removed from the source entity will remain in the target entity.
    By enabling auto_shrink it will automatically drop columns from the target entity as well.
    """

    def __init__(
        self,
        auto_expand: bool = True,
        auto_shrink: bool = False,
        metadata_config: Optional["MetadataConfig"] = None,
    ) -> None:
        super().__init__(metadata_config)
        self._init_schema_evolution(auto_expand, auto_shrink)

    def execute(self, source: "DataSource", target: "DataTarget") -> SparkSneezeResult:
        """Execute the Truncate strategy."""

        self.logger.info("Starting Truncate strategy")

        try:
            # Get source dataframe
            source_df = source.to_dataframe()

            # Handle schema evolution using base class method
            df_with_metadata = self._handle_schema_evolution(source_df, target)

            # Get row count for result message
            row_count = self._get_row_count_safely(df_with_metadata)

            # KEY DIFFERENCE: Truncate target before writing (clear data, preserve structure)
            if target.exists():
                target.truncate()

            # Write to target using append mode (since target is now empty)
            target.write(df_with_metadata, "append")

            return self._create_success_result(
                "Truncate completed successfully", df_with_metadata, row_count
            )

        except Exception as e:
            return self._create_error_result("Truncate failed", e)
