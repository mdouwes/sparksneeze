"""DataFrame data source implementation."""

from pyspark.sql import DataFrame, SparkSession
from .base import DataSource


class DataFrameSource(DataSource):
    """Data source from an existing Spark DataFrame."""

    def __init__(self, dataframe: DataFrame, spark_session: SparkSession):
        """Initialize with existing DataFrame.

        Args:
            dataframe: Existing Spark DataFrame
            spark_session: Spark session to use for operations
        """
        super().__init__(spark_session)
        if not hasattr(dataframe, "schema") or not hasattr(dataframe, "count"):
            raise ValueError(
                "Invalid DataFrame: must have 'schema' and 'count' attributes"
            )

        self.dataframe = dataframe

    def to_dataframe(self) -> DataFrame:
        """Return the existing DataFrame."""
        return self.dataframe

    def __str__(self) -> str:
        return f"DataFrameSource(columns={len(self.dataframe.columns)})"
