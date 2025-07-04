"""DropCreate strategy implementation."""

from typing import TYPE_CHECKING, Optional
from .base import BaseStrategy, SparkSneezeResult

if TYPE_CHECKING:
    from ..data_sources import DataSource
    from ..data_targets import DataTarget
    from ..metadata import MetadataConfig


class DropCreate(BaseStrategy):
    """Remove the target entity and create it anew based on the schema of the source entity.

    There are no parameters, no data or schema will be kept of the old target.
    """

    def __init__(self, metadata_config: Optional["MetadataConfig"] = None) -> None:
        super().__init__(metadata_config)

    def execute(self, source: "DataSource", target: "DataTarget") -> SparkSneezeResult:
        """Execute the DropCreate strategy."""

        self.logger.info("Starting DropCreate strategy")

        try:
            source_df = source.to_dataframe()

            df_with_metadata = self.apply_metadata(source_df)

            row_count = self._get_row_count_safely(df_with_metadata)

            # Drop and recreate target
            target.drop()
            target.write(df_with_metadata, "overwrite")

            return self._create_success_result(
                "DropCreate completed successfully", df_with_metadata, row_count
            )

        except Exception as e:
            return self._create_error_result("DropCreate failed", e)
