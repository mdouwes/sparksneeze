"""Base abstract class for data targets and related exceptions."""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Union, TYPE_CHECKING
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.types import StructType, StructField, DataType

if TYPE_CHECKING:
    from ..enums import WriteMode


class UnsupportedOperationError(Exception):
    """Raised when a target doesn't support a requested operation."""

    pass


class DataTarget(ABC):
    """Abstract base class for data targets."""

    def __init__(self, identifier: str, spark_session: SparkSession, **options):
        """Initialize target with identifier, spark session, and options.

        Args:
            identifier: Target identifier (path, table name, etc.)
            spark_session: Spark session to use for operations
            **options: Target-specific configuration
        """
        self.identifier = identifier
        self.spark_session = spark_session
        self.options = options

    @abstractmethod
    def exists(self) -> bool:
        """Check if target exists.

        Returns:
            bool: True if target exists, False otherwise
        """
        pass

    @abstractmethod
    def get_schema(self) -> Optional[StructType]:
        """Get current schema of the target.

        Returns:
            Optional[StructType]: Schema if target exists, None otherwise
        """
        pass

    @abstractmethod
    def read(self) -> DataFrame:
        """Read all data from target.

        Returns:
            DataFrame: All data from the target

        Raises:
            Exception: If target doesn't exist or can't be read
        """
        pass

    @abstractmethod
    def write(self, dataframe: DataFrame, mode: Union[str, "WriteMode"]) -> None:
        """Write data to target.

        Args:
            dataframe: Data to write
            mode: Write mode ('overwrite', 'append') or WriteMode enum
        """
        pass

    @abstractmethod
    def create_empty(self, schema: StructType) -> None:
        """Create empty target with given schema.

        Args:
            schema: Schema for the new target
        """
        pass

    @abstractmethod
    def drop(self) -> None:
        """Drop entire target."""
        pass

    @abstractmethod
    def truncate(self) -> None:
        """Remove all data, keep structure."""
        pass

    def supports_schema_evolution(self) -> bool:
        """Check if target supports adding/removing columns.

        Returns:
            bool: True if target supports schema evolution
        """
        return False

    def supports_merge(self) -> bool:
        """Check if target supports native merge/upsert operations.

        Returns:
            bool: True if target supports merge operations
        """
        return False

    def supports_type_evolution(self) -> bool:
        """Check if target supports changing column data types.

        Returns:
            bool: True if target supports type evolution
        """
        return False

    def add_columns(self, columns: List[StructField]) -> None:
        """Add columns to target schema.

        Args:
            columns: List of columns to add

        Raises:
            UnsupportedOperationError: If target doesn't support schema evolution
        """
        if not self.supports_schema_evolution():
            raise UnsupportedOperationError(
                f"{type(self).__name__} doesn't support schema evolution"
            )

    def drop_columns(self, column_names: List[str]) -> None:
        """Drop columns from target schema.

        Args:
            column_names: List of column names to drop

        Raises:
            UnsupportedOperationError: If target doesn't support schema evolution
        """
        if not self.supports_schema_evolution():
            raise UnsupportedOperationError(
                f"{type(self).__name__} doesn't support schema evolution"
            )

    def merge(
        self,
        source_df: DataFrame,
        merge_condition: str,
        when_matched_update: Optional[Dict[str, str]] = None,
        when_matched_condition: Optional[str] = None,
        when_not_matched_insert: Optional[Dict[str, str]] = None,
        when_not_matched_by_source_update: Optional[Dict[str, str]] = None,
        when_not_matched_by_source_condition: Optional[str] = None,
    ) -> None:
        """Perform merge/upsert operation.

        Args:
            source_df: Source DataFrame to merge
            merge_condition: SQL condition for matching records
            when_matched_update: Column mappings for matched records
            when_matched_condition: Additional condition for when to update matched records
            when_not_matched_insert: Column mappings for new records
            when_not_matched_by_source_update: Column mappings for target records not in source
            when_not_matched_by_source_condition: Condition for when to update unmatched target records

        Raises:
            UnsupportedOperationError: If target doesn't support merge operations
        """
        if not self.supports_merge():
            raise UnsupportedOperationError(
                f"{type(self).__name__} doesn't support merge operations"
            )

    def alter_column_type(self, column_name: str, new_type: DataType) -> None:
        """Change column data type in target schema.

        Args:
            column_name: Name of column to modify
            new_type: New data type for the column

        Raises:
            UnsupportedOperationError: If target doesn't support type evolution
        """
        if not self.supports_type_evolution():
            raise UnsupportedOperationError(
                f"{type(self).__name__} doesn't support type evolution"
            )

    @abstractmethod
    def __str__(self) -> str:
        """String representation for debugging and logging."""
        pass
