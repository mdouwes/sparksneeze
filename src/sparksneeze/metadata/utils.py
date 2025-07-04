"""Utility functions for metadata processing."""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from pyspark.sql import DataFrame
from pyspark.sql.functions import col, concat_ws, xxhash64
from pyspark.sql.types import StringType


def create_system_info_json(
    strategy_name: str,
    sparksneeze_version: Optional[str] = None,
    user: str = "system",
    additional_info: Optional[Dict[str, Any]] = None,
) -> str:
    """Create system info JSON string.

    Args:
        strategy_name: Name of the strategy being executed
        sparksneeze_version: Version of SparkSneeze (auto-detected if None)
        user: User executing the operation
        additional_info: Additional key-value pairs to include

    Returns:
        JSON string with system metadata
    """
    # Auto-detect version if not provided
    if sparksneeze_version is None:
        try:
            from .. import __version__

            sparksneeze_version = __version__
        except ImportError:
            sparksneeze_version = "unknown"

    system_info = {
        "sparksneeze_version": sparksneeze_version,
        "strategy": strategy_name,
        "created_at": datetime.now().isoformat() + "Z",
        "user": user,
    }

    if additional_info:
        system_info.update(additional_info)

    return json.dumps(system_info, sort_keys=True)


def get_hash_columns(
    df: DataFrame,
    excluded_columns: Optional[Set[str]] = None,
    key_columns: Optional[List[str]] = None,
    metadata_fields: Optional[List[str]] = None,
) -> List[str]:
    """Get columns to include in row hash calculation.

    Args:
        df: DataFrame to analyze
        excluded_columns: Additional columns to exclude from hashing
        key_columns: Key columns to exclude from hashing (e.g., primary keys)
        metadata_fields: Metadata fields to exclude from hashing

    Returns:
        List of column names to include in hash
    """
    all_columns = set(df.columns)

    # Start with columns to exclude
    exclude_set = set(excluded_columns or [])
    exclude_set.update(key_columns or [])
    exclude_set.update(metadata_fields or [])

    # Return remaining columns in deterministic order
    hash_columns = sorted(all_columns - exclude_set)
    return hash_columns


def create_row_hash_column(df: DataFrame, hash_columns: List[str]) -> DataFrame:
    """Add a row hash column to the DataFrame using xxhash64.

    Args:
        df: DataFrame to add hash column to
        hash_columns: List of columns to include in hash calculation

    Returns:
        DataFrame with hash column added
    """
    if not hash_columns:
        # If no columns to hash, use a constant
        return df.withColumn("_temp_hash", xxhash64())

    # Create concatenated string of all hash columns (with separator)
    # Handle nulls by converting to empty string
    concat_expr = concat_ws("|", *[col(c).cast(StringType()) for c in hash_columns])

    hash_expr = xxhash64(concat_expr)

    return df.withColumn("_temp_hash", hash_expr)
