"""Data target abstractions for SparkSneeze operations."""

from typing import Union
from pyspark.sql import SparkSession

from .base import DataTarget, UnsupportedOperationError
from .delta import DeltaTarget

__all__ = [
    "DataTarget",
    "UnsupportedOperationError",
    "DeltaTarget",
    "create_data_target",
]


def create_data_target(
    entity: Union[str, DataTarget], spark_session: SparkSession
) -> DataTarget:
    """Factory function to create appropriate DataTarget implementation.

    Currently only supports Delta format. Future versions will support
    Parquet, JSON, and CSV formats based on file extensions.

    Args:
        entity: Target path/table name or existing DataTarget
        spark_session: Spark session to use for operations

    Returns:
        DataTarget: DeltaTarget instance for all string inputs

    Raises:
        ValueError: If entity type is not supported
    """
    # Input validation
    if entity is None:
        raise ValueError("Entity cannot be None")
    if spark_session is None:
        raise ValueError("SparkSession cannot be None")

    if isinstance(entity, DataTarget):
        return entity

    # Later we expand this like...
    # if entity_lower.endswith('.parquet'):
    #   return ParquetTarget(entity, spark_session)
    if isinstance(entity, str):
        if not entity or entity.strip() == "":
            raise ValueError("Entity string cannot be empty")
        return DeltaTarget(entity, spark_session)

    raise ValueError(
        f"Unsupported target type: {type(entity)}. "
        f"Expected string (path/table) or DataTarget instance."
    )
