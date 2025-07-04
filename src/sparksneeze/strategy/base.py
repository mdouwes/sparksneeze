"""Base strategy classes and common elements for sparksneeze operations."""

from typing import Any, Dict, Optional, List, TYPE_CHECKING
from abc import ABC, abstractmethod

if TYPE_CHECKING:
    from pyspark.sql import DataFrame
    from pyspark.sql.types import StructField
    from ..data_sources import DataSource
    from ..data_targets import DataTarget
    from ..logging import SparkSneezeLogger
    from ..metadata import MetadataConfig
    from ..schema_evolution import SchemaEvolutionHandler


class SparkSneezeResult:
    """Result object returned by strategy operations.

    Contains comprehensive information about the execution of a sparksneeze strategy,
    including success status, performance metrics, and metadata about the operation.

    Attributes:
        success: Boolean indicating whether the strategy executed successfully
        message: Human-readable description of the operation result
        data: Dictionary containing strategy-specific metadata and metrics

    Examples:
        Successful execution result:

        >>> result = SparkSneezeResult(
        ...     success=True,
        ...     message="DropCreate completed successfully",
        ...     data={
        ...         "records_processed": 1000,
        ...         "execution_time": 2.5,
        ...         "target_schema": ["id", "name", "created_at"],
        ...         "strategy_metadata": {"tables_dropped": 1, "tables_created": 1}
        ...     }
        ... )
        >>> print(f"Processed {result.data['records_processed']} records")

        Failed execution result:

        >>> result = SparkSneezeResult(
        ...     success=False,
        ...     message="Schema validation failed: missing required column 'id'",
        ...     data={"error_type": "SchemaError", "failed_column": "id"}
        ... )
        >>> if not result.success:
        ...     print(f"Operation failed: {result.message}")
    """

    def __init__(
        self,
        success: bool = True,
        message: str = "",
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize a SparkSneezeResult.

        Args:
            success: Whether the operation completed successfully
            message: Descriptive message about the operation outcome
            data: Optional dictionary of additional result metadata

        Examples:
            Basic success result:

            >>> result = SparkSneezeResult(True, "Operation completed")

            Detailed result with metrics:

            >>> result = SparkSneezeResult(
            ...     success=True,
            ...     message="Upsert completed with schema evolution",
            ...     data={
            ...         "records_inserted": 500,
            ...         "records_updated": 300,
            ...         "columns_added": ["new_field"],
            ...         "execution_time": 4.2
            ...     }
            ... )
        """
        self.success: bool = success
        self.message: str = message
        self.data: Dict[str, Any] = data or {}


class BaseStrategy(ABC):
    """Base class for all sparksneeze strategies."""

    def __init__(self, metadata_config: Optional["MetadataConfig"] = None):
        """Initialize base strategy.

        Args:
            metadata_config: Configuration for metadata fields. Uses default if None.
        """
        self._logger: Optional["SparkSneezeLogger"] = None
        self._metadata_config = metadata_config
        self._metadata_applier: Optional[Any] = None
        self.key: Optional[List[str]] = None

        # Schema evolution attributes (used by strategies that support auto_expand/auto_shrink)
        self._schema_handler: Optional["SchemaEvolutionHandler"] = None

    @property
    def logger(self) -> "SparkSneezeLogger":
        """Get logger for this strategy."""
        if self._logger is None:
            # Import here to avoid circular imports
            from ..logging import get_logger

            self._logger = get_logger(
                f"sparksneeze.strategy.{self.__class__.__name__.lower()}"
            )
        return self._logger

    @property
    def metadata_applier(self):
        """Get metadata applier for this strategy."""
        if self._metadata_applier is None:
            # Import here to avoid circular imports
            from ..metadata import MetadataApplier

            self._metadata_applier = MetadataApplier(self._metadata_config)
        return self._metadata_applier

    def apply_metadata(
        self, df: "DataFrame", key_columns: Optional[List[str]] = None, **kwargs
    ) -> "DataFrame":
        """Apply metadata to a DataFrame.

        Args:
            df: DataFrame to add metadata to
            key_columns: Key columns to exclude from hashing
            **kwargs: Additional arguments passed to metadata applier

        Returns:
            DataFrame with metadata applied
        """
        return self.metadata_applier.apply_metadata(
            df=df,
            strategy_name=self.__class__.__name__,
            key_columns=key_columns,
            **kwargs,
        )

    def _get_row_count_safely(self, df: "DataFrame") -> Optional[int]:
        """Get row count from DataFrame with safe error handling.

        Args:
            df: DataFrame to count rows for

        Returns:
            Row count or None if counting fails
        """
        try:
            return df.count()
        except Exception as e:
            self.logger.debug(f"Failed to count DataFrame rows: {e}")
            return None

    def _create_success_result(
        self, message: str, df: "DataFrame", row_count: Optional[int] = None
    ) -> SparkSneezeResult:
        """Create standardized success result.

        Args:
            message: Base success message
            df: Result DataFrame
            row_count: Optional row count for message formatting

        Returns:
            Success SparkSneezeResult
        """
        if row_count is not None:
            full_message = f"{message} ({row_count:,} rows)"
        else:
            full_message = message

        self.logger.success(full_message)

        return SparkSneezeResult(
            success=True,
            message=full_message,
            data={"result_dataframe": df, "rows_processed": row_count},
        )

    def _create_error_result(self, message: str, error: Exception) -> SparkSneezeResult:
        """Create standardized error result.

        Args:
            message: Base error message
            error: Exception that occurred

        Returns:
            Error SparkSneezeResult
        """
        error_message = f"{message}: {str(error)}"
        self.logger.error(error_message)

        return SparkSneezeResult(
            success=False, message=error_message, data={"error": str(error)}
        )

    def _init_schema_evolution(
        self, auto_expand: bool = True, auto_shrink: bool = False
    ) -> None:
        """Initialize schema evolution handler for strategies that support it.

        Args:
            auto_expand: Whether to automatically add new columns from source to target
            auto_shrink: Whether to automatically remove columns from target that don't exist in source
        """
        self.auto_expand = auto_expand
        self.auto_shrink = auto_shrink

    def _get_schema_handler(self) -> "SchemaEvolutionHandler":
        """Get schema evolution handler for this strategy."""
        if self._schema_handler is None:
            from ..schema_evolution import SchemaEvolutionHandler

            metadata_fields = set(self.metadata_applier.config.all_metadata_fields)
            self._schema_handler = SchemaEvolutionHandler(
                auto_expand=getattr(self, "auto_expand", True),
                auto_shrink=getattr(self, "auto_shrink", False),
                metadata_fields=metadata_fields,
                logger=self.logger,
            )
        return self._schema_handler

    def _get_metadata_fields(self) -> List["StructField"]:
        """Get metadata fields to add to target schema.

        Returns:
            List of StructField objects for metadata columns
        """
        from pyspark.sql.types import (
            StructField,
            TimestampType,
            BooleanType,
            StringType,
        )

        config = self.metadata_applier.config
        return [
            StructField(config.prefixed_valid_from, TimestampType(), False),
            StructField(config.prefixed_valid_to, TimestampType(), False),
            StructField(config.prefixed_active, BooleanType(), False),
            StructField(config.prefixed_row_hash, StringType(), False),
            StructField(config.prefixed_system_info, StringType(), False),
        ]

    def _handle_schema_evolution(
        self, source_df: "DataFrame", target: "DataTarget", **kwargs
    ) -> "DataFrame":
        """Handle complete schema evolution workflow.

        Args:
            source_df: Source DataFrame
            target: Target data entity
            **kwargs: Additional arguments passed to apply_metadata

        Returns:
            DataFrame aligned with evolved target schema and metadata applied
        """
        schema_handler = self._get_schema_handler()

        # Handle target existence - create if needed
        if not target.exists():
            self.logger.info(
                "Target doesn't exist, creating with source schema + metadata"
            )
            # Create target with source schema + metadata columns
            metadata_schema = self.metadata_applier.get_schema_with_metadata(
                source_df.schema
            )
            target.create_empty(metadata_schema)

        # Perform schema evolution
        evolved_source_df, evolution_info = schema_handler.evolve_schema(
            source_df, target
        )

        # Ensure target has metadata columns if it exists and doesn't have them
        schema_handler.ensure_metadata_columns(target, self._get_metadata_fields())

        # After all schema evolution, get refreshed target schema and align source DataFrame
        target_schema_post_evolution = target.get_schema()
        if target_schema_post_evolution is None:
            raise ValueError("Could not get target schema after evolution")

        # Align source DataFrame with evolved target schema (excluding metadata columns)
        aligned_source_df = schema_handler.align_with_target(
            evolved_source_df, target_schema_post_evolution, include_metadata=False
        )

        # Apply metadata to aligned source data
        df_with_metadata = self.apply_metadata(
            aligned_source_df, evolution_info=evolution_info, **kwargs
        )

        # FINAL ALIGNMENT: Ensure metadata DataFrame matches target schema exactly (column order & types)
        df_with_metadata = schema_handler.align_with_target(
            df_with_metadata, target_schema_post_evolution, include_metadata=True
        )

        return df_with_metadata

    @abstractmethod
    def execute(self, source: "DataSource", target: "DataTarget") -> SparkSneezeResult:
        """Execute the strategy.

        Args:
            source: Source data entity (DataSource instance)
            target: Target data entity (DataTarget instance)

        Returns:
            SparkSneezeResult: Result of the strategy execution
        """
        pass
