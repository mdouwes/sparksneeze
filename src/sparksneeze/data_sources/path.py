"""Path-based data source implementation."""

from pathlib import Path
from pyspark.sql import DataFrame, SparkSession
from .base import DataSource


class PathSource(DataSource):
    """Data source from a file path."""

    def __init__(
        self,
        path: str,
        spark_session: SparkSession,
        format: str = "delta",
        **read_options,
    ):
        """Initialize with file path and format.

        Args:
            path: File path or directory path
            spark_session: Spark session to use for operations
            format: Data format (delta, parquet, json, csv, etc.)
            **read_options: Additional options for spark.read
        """
        super().__init__(spark_session)
        self.path = str(Path(path).resolve())
        self.format = format.lower()
        self.read_options = read_options

    def to_dataframe(self) -> DataFrame:
        """Load data from path using Spark."""
        reader = self.spark_session.read.format(self.format)

        # Apply read options
        for key, value in self.read_options.items():
            reader = reader.option(key, value)

        return reader.load(self.path)

    def __str__(self) -> str:
        return f"PathSource(path={self.path}, format={self.format})"
