"""Data source abstractions for SparkSneeze operations."""

from typing import Union, cast
from pyspark.sql import DataFrame, SparkSession

from .base import DataSource
from .dataframe import DataFrameSource
from .path import PathSource
from .table import TableSource

__all__ = [
    "DataSource",
    "DataFrameSource",
    "PathSource",
    "TableSource",
    "create_data_source",
]


def create_data_source(
    entity: Union[DataFrame, str, DataSource], spark_session: SparkSession
) -> DataSource:
    """Factory function to create appropriate DataSource from various inputs.

    Args:
        entity: Can be a DataFrame, file path, table name, or existing DataSource
        spark_session: Spark session to use for operations

    Returns:
        DataSource: Appropriate data source instance

    Raises:
        ValueError: If entity type is not supported
    """
    # Input validation
    if entity is None:
        raise ValueError("Entity cannot be None")
    if spark_session is None:
        raise ValueError("SparkSession cannot be None")

    if isinstance(entity, DataSource):
        return entity

    if hasattr(entity, "schema") and hasattr(entity, "count"):
        # It's a DataFrame
        return DataFrameSource(cast(DataFrame, entity), spark_session)

    if isinstance(entity, str):
        # Additional string validation
        if not entity or entity.strip() == "":
            raise ValueError("Entity string cannot be empty")

        # Determine if it's a path or table name
        entity_lower = entity.lower()

        # Check for common file extensions
        if any(
            entity_lower.endswith(ext)
            for ext in [".parquet", ".json", ".csv", ".orc", ".avro"]
        ):
            # Extract format from extension
            format_name = entity_lower.split(".")[-1]
            return PathSource(entity, spark_session, format=format_name)

        # Check for path-like structures
        if (
            "/" in entity
            or "\\" in entity
            or entity.startswith("s3://")
            or entity.startswith("hdfs://")
            or entity.startswith("abfss://")
        ):
            # It's a path - default to delta format
            return PathSource(entity, spark_session, format="delta")

        # Check for database.table pattern
        if "." in entity and not entity.startswith("."):
            parts = entity.split(".")
            if len(parts) == 2 and all(part.strip() for part in parts):
                return TableSource(parts[1], spark_session, database=parts[0])

        # Default to table name
        return TableSource(entity, spark_session)

    raise ValueError(
        f"Unsupported entity type: {type(entity)}. "
        f"Expected DataFrame, string (path/table), or DataSource instance."
    )
