"""Table-based data source implementation."""

from typing import Optional
from pyspark.sql import DataFrame, SparkSession
from .base import DataSource


class TableSource(DataSource):
    """Data source from a table name (catalog table)."""

    def __init__(
        self,
        table_name: str,
        spark_session: SparkSession,
        database: Optional[str] = None,
    ):
        """Initialize with table name.

        Args:
            table_name: Name of the table
            spark_session: Spark session to use for operations
            database: Optional database name (if not specified, uses current database)
        """
        super().__init__(spark_session)
        self.table_name = table_name
        self.database = database
        self.full_table_name = f"{database}.{table_name}" if database else table_name

    def to_dataframe(self) -> DataFrame:
        """Load data from table using Spark."""
        return self.spark_session.table(self.full_table_name)

    def __str__(self) -> str:
        return f"TableSource(table={self.full_table_name})"
