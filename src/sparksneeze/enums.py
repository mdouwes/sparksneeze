"""Enums for sparksneeze to replace magic strings."""

from enum import Enum


class WriteMode(Enum):
    """Enum for write modes to replace magic strings."""

    OVERWRITE = "overwrite"
    APPEND = "append"


class DataFormat(Enum):
    """Enum for data formats."""

    DELTA = "delta"
    PARQUET = "parquet"
    JSON = "json"
    CSV = "csv"
    ORC = "orc"
    AVRO = "avro"
