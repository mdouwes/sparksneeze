"""Delta Lake data target implementation."""

from pathlib import Path
from typing import Optional, List, Dict, Union
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.types import StructType, StructField, DataType
from delta.tables import DeltaTable
from .base import DataTarget
from ..enums import WriteMode


class DeltaTarget(DataTarget):
    """Delta Lake implementation of DataTarget."""

    def __init__(self, path: str, spark_session: SparkSession, **options):
        """Initialize Delta target.

        Args:
            path: Path to Delta table
            spark_session: Spark session to use for operations
            **options: Delta-specific options (mergeSchema, overwriteSchema, etc.)
        """
        # Validate path before processing
        if not path or path.strip() == "":
            raise ValueError("Path cannot be empty")

        super().__init__(path, spark_session, **options)
        # Store original path for catalog table detection
        self._original_path = path.strip()
        # Only resolve to absolute path for filesystem paths, not catalog tables
        if self._is_catalog_table_name(path):
            self.path = path.strip()
        else:
            self.path = str(Path(path).resolve())

    def _validate_identifier(self, identifier: str) -> str:
        """Validate SQL identifiers to prevent injection.

        Args:
            identifier: Identifier to validate

        Returns:
            The validated identifier

        Raises:
            ValueError: If identifier is invalid
        """
        if not identifier or not isinstance(identifier, str):
            raise ValueError(f"Invalid identifier: {identifier}")
        # Allow alphanumeric, underscores, hyphens, dots, and forward slashes for paths
        if not all(c.isalnum() or c in "_-./\\:" for c in identifier):
            raise ValueError(
                f"Invalid identifier contains unsafe characters: {identifier}"
            )
        return identifier

    def exists(self) -> bool:
        """Check if Delta table exists."""
        try:
            if self._is_catalog_table():
                # For catalog tables, use Spark catalog API
                return self.spark_session.catalog.tableExists(self.path)
            else:
                # For path-based tables, use Delta path check
                return DeltaTable.isDeltaTable(self.spark_session, self.path)
        except Exception:
            return False

    def get_schema(self) -> Optional[StructType]:
        """Get schema from Delta table metadata."""
        if not self.exists():
            return None

        try:
            if self._is_catalog_table():
                # For catalog tables, read schema via table name
                return self.spark_session.table(self.path).schema
            else:
                # For path-based tables, use Delta forPath
                delta_table = DeltaTable.forPath(self.spark_session, self.path)
                return delta_table.toDF().schema
        except Exception:
            return None

    def read(self) -> DataFrame:
        """Read using Delta format."""
        if not self.exists():
            raise ValueError(f"Delta table does not exist: {self.path}")

        if self._is_catalog_table():
            # For catalog tables, read via table name
            return self.spark_session.table(self.path)
        else:
            # For path-based tables, read via path
            return self.spark_session.read.format("delta").load(self.path)

    def write(self, dataframe: DataFrame, mode: Union[str, WriteMode]) -> None:
        """Write with Delta-specific options."""
        # Handle WriteMode enum
        mode_str = mode.value if isinstance(mode, WriteMode) else mode

        writer = dataframe.write.format("delta").mode(mode_str)

        # Apply Delta-specific options
        for key, value in self.options.items():
            writer = writer.option(key, value)

        writer.save(self.path)

    def create_empty(self, schema: StructType) -> None:
        """Create empty Delta table with schema."""
        empty_df = self.spark_session.createDataFrame([], schema)
        self.write(empty_df, WriteMode.OVERWRITE)

    def _is_catalog_table_name(self, path: str) -> bool:
        """Determine if a path string represents a catalog table name (static method)."""
        # Catalog tables typically have format: [catalog.]database.table
        # Path-based tables have filesystem paths or URIs
        path = path.strip()

        # Check for filesystem path indicators
        if any(char in path for char in ["/", "\\"]):
            return False
        if any(
            path.startswith(prefix)
            for prefix in ["s3://", "hdfs://", "abfss://", "gs://", "file:"]
        ):
            return False
        if any(path.endswith(ext) for ext in [".delta", ".parquet", ".json", ".csv"]):
            return False

        # Check for catalog table pattern (contains dots, splits into 2-3 parts)
        if "." in path:
            parts = path.split(".")
            if len(parts) in [2, 3] and all(part.strip() for part in parts):
                return True

        return False

    def _is_catalog_table(self) -> bool:
        """Determine if this is a catalog table vs path-based table."""
        return self._is_catalog_table_name(self._original_path)

    def drop(self) -> None:
        """Remove Delta table completely (structure and data)."""
        try:
            if self.exists():
                if self._is_catalog_table():
                    # For catalog tables, use SQL DROP TABLE
                    validated_table_name = self._validate_identifier(self.path)
                    sql = f"DROP TABLE IF EXISTS {validated_table_name}"
                    self.spark_session.sql(sql)
                else:
                    # For path-based Delta tables, physically remove the directory
                    # This works with all storage backends (local, ABFSS, S3, etc.)
                    # Use Hadoop filesystem operations through Spark
                    hadoop_conf = (
                        self.spark_session.sparkContext._jsc.hadoopConfiguration()
                    )
                    fs = self.spark_session.sparkContext._jvm.org.apache.hadoop.fs.FileSystem.get(
                        hadoop_conf
                    )
                    path = (
                        self.spark_session.sparkContext._jvm.org.apache.hadoop.fs.Path(
                            self.path
                        )
                    )

                    if fs.exists(path):
                        fs.delete(path, True)  # True means recursive deletion
        except Exception as e:
            # If we can't drop the table, log warning but continue - the write will overwrite
            # Using print since logger may not be available in this context
            print(f"Warning: Could not drop Delta table: {e}")

    def truncate(self) -> None:
        """Use Delta DELETE operation to remove all data."""
        if not self.exists():
            return

        delta_table = DeltaTable.forPath(self.spark_session, self.path)
        delta_table.delete()

    def supports_schema_evolution(self) -> bool:
        """Delta supports schema evolution."""
        return True

    def supports_merge(self) -> bool:
        """Delta supports merge operations."""
        return True

    def supports_type_evolution(self) -> bool:
        """Delta supports type evolution."""
        return True

    def add_columns(self, columns: List[StructField]) -> None:
        """Add columns using ALTER TABLE."""
        if not self.exists():
            raise ValueError(
                f"Cannot add columns to non-existent Delta table: {self.path}"
            )

        for column in columns:
            # Validate column name for SQL injection prevention
            validated_column_name = self._validate_identifier(column.name)
            column_def = f"{validated_column_name} {column.dataType.simpleString()}"
            # Note: Delta Lake doesn't support NOT NULL constraints in ALTER TABLE ADD COLUMN
            # so we skip the NOT NULL even for non-nullable columns

            validated_path = self._validate_identifier(self.path)
            sql = f"ALTER TABLE delta.`{validated_path}` ADD COLUMN {column_def}"
            self.spark_session.sql(sql)

    def drop_columns(self, column_names: List[str]) -> None:
        """Drop columns using ALTER TABLE."""
        if not self.exists():
            raise ValueError(
                f"Cannot drop columns from non-existent Delta table: {self.path}"
            )

        for column_name in column_names:
            validated_column_name = self._validate_identifier(column_name)
            validated_path = self._validate_identifier(self.path)
            sql = f"ALTER TABLE delta.`{validated_path}` DROP COLUMN {validated_column_name}"
            self.spark_session.sql(sql)

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
        """Perform Delta MERGE operation with advanced merge clauses."""
        if not self.exists():
            raise ValueError(f"Cannot merge into non-existent Delta table: {self.path}")

        delta_table = DeltaTable.forPath(self.spark_session, self.path)
        merge_builder = delta_table.alias("target").merge(
            source_df.alias("source"), merge_condition
        )

        # When matched clause with optional condition
        if when_matched_update:
            if when_matched_condition:
                merge_builder = merge_builder.whenMatchedUpdate(
                    condition=when_matched_condition, set=when_matched_update
                )
            else:
                merge_builder = merge_builder.whenMatchedUpdate(set=when_matched_update)

        # When not matched by source clause (target records not in source)
        if when_not_matched_by_source_update:
            if when_not_matched_by_source_condition:
                merge_builder = merge_builder.whenNotMatchedBySourceUpdate(
                    condition=when_not_matched_by_source_condition,
                    set=when_not_matched_by_source_update,
                )
            else:
                merge_builder = merge_builder.whenNotMatchedBySourceUpdate(
                    set=when_not_matched_by_source_update
                )

        # When not matched clause (source records not in target)
        if when_not_matched_insert:
            merge_builder = merge_builder.whenNotMatchedInsert(
                values=when_not_matched_insert
            )

        merge_builder.execute()

    def alter_column_type(self, column_name: str, new_type: DataType) -> None:
        """Change column type using ALTER TABLE."""
        if not self.exists():
            raise ValueError(
                f"Cannot alter column type in non-existent Delta table: {self.path}"
            )

        validated_column_name = self._validate_identifier(column_name)
        validated_path = self._validate_identifier(self.path)
        sql = f"ALTER TABLE delta.`{validated_path}` ALTER COLUMN {validated_column_name} TYPE {new_type.simpleString()}"
        self.spark_session.sql(sql)

    def __str__(self) -> str:
        return f"DeltaTarget(path={self.path})"
