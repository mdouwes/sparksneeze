"""Base abstract class for data sources."""

from abc import ABC, abstractmethod
from pyspark.sql import DataFrame, SparkSession


class DataSource(ABC):
    """Abstract base class for data sources."""

    def __init__(self, spark_session: SparkSession):
        """Initialize data source with Spark session.

        Args:
            spark_session: Spark session to use for operations
        """
        self.spark_session = spark_session

    @abstractmethod
    def to_dataframe(self) -> DataFrame:
        """Convert this data source to a Spark DataFrame.

        Returns:
            DataFrame: The loaded data as a Spark DataFrame

        Raises:
            Exception: If the data source cannot be loaded
        """
        pass

    @abstractmethod
    def __str__(self) -> str:
        """String representation for debugging and logging."""
        pass
