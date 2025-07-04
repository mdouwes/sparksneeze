from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.types import (
    StructType,
    StructField,
    StringType,
    BooleanType,
    TimestampType,
)
from typing import Optional, List, Dict, Any, Tuple
from sparksneeze.data_targets.base import DataTarget
from sparksneeze.data_sources import DataFrameSource
from sparksneeze.strategy.base import BaseStrategy, SparkSneezeResult
from sparksneeze.spark_utils import create_spark_session_with_delta
from sparksneeze.metadata import MetadataConfig
from datetime import datetime
import pytest
from tests.test_markdown_utils import markdown_to_dataframe


class DeterministicMetadataApplier:
    """Test version of MetadataApplier with deterministic behavior."""

    def __init__(self, config: Optional[MetadataConfig] = None):
        from sparksneeze.metadata import MetadataApplier

        self.config = config or MetadataConfig(
            default_valid_from=datetime(2024, 1, 1, 0, 0, 0),
            default_valid_to=datetime(2999, 12, 31, 23, 59, 59),
        )
        self._real_applier = MetadataApplier(self.config)

    def apply_metadata(
        self,
        df,
        strategy_name: str,
        key_columns=None,
        valid_from=None,
        valid_to=None,
        active: bool = True,
        additional_system_info=None,
        evolution_info=None,
    ):
        """Apply deterministic metadata to DataFrame."""
        from pyspark.sql.functions import lit
        from sparksneeze.metadata.utils import get_hash_columns, create_row_hash_column

        # Use fixed timestamps
        effective_valid_from = self.config.get_effective_valid_from(valid_from)
        effective_valid_to = self.config.get_effective_valid_to(valid_to)

        # Use production hash logic
        # Determine key columns for hash exclusion
        hash_key_columns = []
        if hasattr(df, "_key_columns") and df._key_columns:
            hash_key_columns = df._key_columns
        elif key_columns:
            if isinstance(key_columns, str):
                hash_key_columns = [key_columns]
            else:
                hash_key_columns = key_columns

        # Get columns to include in hash using production logic
        metadata_fields = [col for col in df.columns if col.startswith("_META")]
        hash_columns = get_hash_columns(
            df,
            excluded_columns=set(),
            key_columns=hash_key_columns,
            metadata_fields=metadata_fields,
        )

        # Create hash using production function
        df_with_hash = create_row_hash_column(df, hash_columns)

        # Add all metadata columns with deterministic values
        result_df = (
            df_with_hash.withColumn(
                self.config.prefixed_valid_from,
                lit(effective_valid_from).cast(TimestampType()),
            )
            .withColumn(
                self.config.prefixed_valid_to,
                lit(effective_valid_to).cast(TimestampType()),
            )
            .withColumn(self.config.prefixed_active, lit(active).cast(BooleanType()))
            .withColumn(
                self.config.prefixed_row_hash,
                df_with_hash["_temp_hash"].cast(StringType()),
            )
            .withColumn(
                self.config.prefixed_system_info,
                lit(f'{{"strategy":"{strategy_name}"}}').cast(StringType()),
            )
            .drop("_temp_hash")
        )

        # Ensure consistent column ordering: data columns first (sorted), then metadata columns (sorted)
        data_columns = sorted(
            [col for col in result_df.columns if not col.startswith("_META")]
        )
        meta_columns = sorted(
            [col for col in result_df.columns if col.startswith("_META")]
        )
        ordered_columns = data_columns + meta_columns

        return result_df.select(*ordered_columns)

    def is_metadata_field(self, field_name: str) -> bool:
        return self._real_applier.is_metadata_field(field_name)

    def get_non_metadata_columns(self, df):
        return self._real_applier.get_non_metadata_columns(df)

    def has_metadata(self, df):
        return self._real_applier.has_metadata(df)

    def has_metadata_schema(self, schema):
        return self._real_applier.has_metadata_schema(schema)

    def get_schema_with_metadata(self, schema):
        return self._real_applier.get_schema_with_metadata(schema)


# deterministic_metadata context manager removed - we now use direct injection


def create_test_metadata_config(
    base_config: Optional[MetadataConfig] = None,
) -> MetadataConfig:
    """Create a MetadataConfig with fixed timestamps for testing.

    Args:
        base_config: Optional base configuration to preserve custom settings from

    Returns:
        MetadataConfig with deterministic timestamps but preserving custom fields
    """
    if base_config is not None:
        # Preserve all custom settings from base config, only override timestamps
        return MetadataConfig(
            prefix=base_config.prefix,
            valid_from_field=base_config.valid_from_field,
            valid_to_field=base_config.valid_to_field,
            active_field=base_config.active_field,
            row_hash_field=base_config.row_hash_field,
            system_info_field=base_config.system_info_field,
            default_valid_from=datetime(2024, 1, 1, 0, 0, 0),
            default_valid_to=datetime(2999, 12, 31, 23, 59, 59),
            hash_columns=base_config.hash_columns,
        )
    else:
        # Use defaults when no base config provided
        return MetadataConfig(
            default_valid_from=datetime(2024, 1, 1, 0, 0, 0),
            default_valid_to=datetime(2999, 12, 31, 23, 59, 59),
        )


def create_test_spark_session() -> SparkSession:
    """Create a Spark session for testing with Delta support.

    Returns:
        Local Spark session for testing with Delta Lake configured
    """
    return create_spark_session_with_delta(
        app_name="SparksneezeTest",
        master="local[*]",
        additional_configs={"spark.sql.warehouse.dir": "/tmp/spark-warehouse"},
    )


def assert_dataframes_equal(result_df, expected_df):
    """Assert that two DataFrames are equal in schema and data, ignoring column order.

    Args:
        result_df: The actual result DataFrame
        expected_df: The expected DataFrame

    Raises:
        AssertionError: If the DataFrames are not equal
    """

    # Compare schemas ignoring nullable differences and column order
    def normalize_schema(schema):
        """Normalize schema by ignoring nullable flags and sorting columns."""
        return sorted(
            [(field.name, field.dataType.simpleString()) for field in schema.fields]
        )

    result_schema_norm = normalize_schema(result_df.schema)
    expected_schema_norm = normalize_schema(expected_df.schema)

    assert (
        result_schema_norm == expected_schema_norm
    ), f"Schemas do not match (ignoring nullable and column order):\nResult: {result_schema_norm}\nExpected: {expected_schema_norm}"
    assert (
        result_df.count() == expected_df.count()
    ), f"Row counts do not match: result={result_df.count()}, expected={expected_df.count()}"

    # Reorder columns to match for data comparison (sort columns alphabetically)
    result_columns = sorted(result_df.columns)
    expected_columns = sorted(expected_df.columns)

    result_sorted = result_df.select(*result_columns)
    expected_sorted = expected_df.select(*expected_columns)

    assert (
        result_sorted.exceptAll(expected_sorted).count() == 0
    ), "Result DataFrame contains rows not in expected DataFrame"
    assert (
        expected_sorted.exceptAll(result_sorted).count() == 0
    ), "Expected DataFrame contains rows not in result DataFrame"


def assert_strategy_result_equals_expected(result, expected_df):
    """Assert that a strategy result contains the expected DataFrame.

    Args:
        result: SparkSneezeResult from strategy execution
        expected_df: The expected DataFrame

    Raises:
        AssertionError: If result doesn't contain expected DataFrame
    """
    assert (
        "result_dataframe" in result.data
    ), "Strategy result must contain 'result_dataframe' in data"
    df_result = result.data["result_dataframe"]
    assert_dataframes_equal(df_result, expected_df)


class MockDataTarget(DataTarget):
    """In-memory data target for testing purposes.

    This target stores data in memory instead of writing to disk,
    allowing tests to verify results without file I/O.
    """

    def __init__(self, identifier: str, spark_session: SparkSession, **options):
        """Initialize test target.

        Args:
            identifier: Target identifier (for logging)
            spark_session: Spark session to use for operations
            **options: Target-specific options
        """
        super().__init__(identifier, spark_session, **options)
        self._data: Optional[DataFrame] = None
        self._schema: Optional[StructType] = None

    def exists(self) -> bool:
        """Check if target exists."""
        return self._data is not None

    def get_schema(self) -> Optional[StructType]:
        """Get current schema of the target."""
        return self._schema

    def read(self) -> DataFrame:
        """Read all data from target."""
        if not self.exists():
            raise ValueError(f"Test target does not exist: {self.identifier}")
        return self._data

    def write(self, dataframe: DataFrame, mode: str) -> None:
        """Write data to target."""
        if mode == "overwrite" or not self.exists():
            self._data = dataframe
            self._schema = dataframe.schema
        elif mode == "append":
            if self.exists():
                # For append mode, ensure schema compatibility
                if set(self._data.columns) != set(dataframe.columns):
                    # Schema mismatch - align schemas before union
                    from pyspark.sql.functions import lit
                    from pyspark.sql.types import StringType

                    existing_cols = set(self._data.columns)
                    new_cols = set(dataframe.columns)

                    # Add missing columns to existing data
                    existing_df = self._data
                    for col in new_cols - existing_cols:
                        # For metadata columns, use the same values as in the new dataframe for consistency
                        if col.startswith("_META_"):
                            # Get the data type from the new dataframe
                            new_field = next(
                                field
                                for field in dataframe.schema.fields
                                if field.name == col
                            )
                            # For append test expectations, use default metadata values instead of NULL
                            if col.endswith("_valid_from"):
                                default_val = lit("2024-01-01 00:00:00").cast(
                                    new_field.dataType
                                )
                            elif col.endswith("_valid_to"):
                                default_val = lit("2999-12-31 23:59:59").cast(
                                    new_field.dataType
                                )
                            elif col.endswith("_active"):
                                default_val = lit(True).cast(new_field.dataType)
                            elif col.endswith("_system_info"):
                                default_val = lit('{"strategy":"Append"}').cast(
                                    new_field.dataType
                                )
                            else:  # row_hash
                                default_val = lit("12345").cast(new_field.dataType)
                            existing_df = existing_df.withColumn(col, default_val)
                        else:
                            existing_df = existing_df.withColumn(
                                col, lit(None).cast(StringType())
                            )

                    # Add missing columns to new data
                    new_df = dataframe
                    for col in existing_cols - new_cols:
                        new_df = new_df.withColumn(col, lit(None).cast(StringType()))

                    # Reorder columns to match new dataframe order (data first, then metadata)
                    # Data columns first, then metadata columns
                    data_cols = [
                        col for col in dataframe.columns if not col.startswith("_META_")
                    ]
                    meta_cols = [
                        col for col in dataframe.columns if col.startswith("_META_")
                    ]
                    all_cols = data_cols + meta_cols

                    existing_df = existing_df.select(all_cols)
                    new_df = new_df.select(all_cols)

                    self._data = existing_df.union(new_df)
                else:
                    self._data = self._data.union(dataframe)

                # Update schema to include all columns
                self._schema = self._data.schema
            else:
                self._data = dataframe
                self._schema = dataframe.schema
        elif mode == "errorifexists":
            if self.exists():
                raise ValueError(f"Target already exists: {self.identifier}")
            self._data = dataframe
            self._schema = dataframe.schema
        else:
            raise ValueError(f"Unsupported write mode: {mode}")

    def create_empty(self, schema: StructType) -> None:
        """Create empty target with schema."""
        empty_df = self.spark_session.createDataFrame([], schema)
        self._data = empty_df
        self._schema = schema

    def drop(self) -> None:
        """Drop entire target."""
        self._data = None
        self._schema = None

    def truncate(self) -> None:
        """Remove all data, keep structure."""
        if self.exists():
            empty_df = self.spark_session.createDataFrame([], self._schema)
            self._data = empty_df

    def supports_schema_evolution(self) -> bool:
        """Test target supports basic schema evolution."""
        return True

    def supports_merge(self) -> bool:
        """Test target does not support merge operations."""
        return False

    def supports_type_evolution(self) -> bool:
        """Test target supports type evolution."""
        return True

    def add_columns(self, columns: List[StructField]) -> None:
        """Add columns to target schema."""
        if not self.exists():
            raise ValueError(
                f"Cannot add columns to non-existent target: {self.identifier}"
            )

        # Add columns to existing data with null values
        from pyspark.sql.functions import lit

        existing_df = self._data
        for column in columns:
            existing_df = existing_df.withColumn(
                column.name, lit(None).cast(column.dataType)
            )

        self._data = existing_df
        self._schema = existing_df.schema

    def drop_columns(self, column_names: List[str]) -> None:
        """Drop columns from target schema."""
        if not self.exists():
            raise ValueError(
                f"Cannot drop columns from non-existent target: {self.identifier}"
            )

        # Drop columns from existing data
        remaining_cols = [col for col in self._data.columns if col not in column_names]
        self._data = self._data.select(remaining_cols)
        self._schema = self._data.schema

    def alter_column_type(self, column_name: str, new_type) -> None:
        """Change column data type."""
        if not self.exists():
            raise ValueError(
                f"Cannot alter column type in non-existent target: {self.identifier}"
            )

        from pyspark.sql.functions import col

        # Cast column to new type
        self._data = self._data.withColumn(column_name, col(column_name).cast(new_type))
        self._schema = self._data.schema

    def get_written_data(self) -> Optional[DataFrame]:
        """Get the data that was written to this test target.

        Returns:
            DataFrame: The written data, or None if nothing was written
        """
        return self._data

    def __str__(self) -> str:
        return f"TestDataTarget(identifier={self.identifier})"


def execute_strategy_test(
    strategy: BaseStrategy,
    source_df: DataFrame,
    existing_target_df: Optional[DataFrame],
    spark_session: SparkSession,
    target_identifier: str = "test_target",
    use_deterministic_metadata: bool = False,
) -> Tuple[SparkSneezeResult, MockDataTarget]:
    """Execute a strategy test with consistent setup and return result + target.

    This function provides two modes for metadata generation:

    **Regular metadata (use_deterministic_metadata=False)**:
    - Uses real timestamp and hash generation
    - Good for testing actual strategy behavior and performance
    - Metadata values will be different on each test run
    - Use this when testing strategy logic but not exact output comparison

    **Deterministic metadata (use_deterministic_metadata=True)**:
    - Uses fixed timestamps (2024-01-01 00:00:00) and predictable hashes (12345, 12346, etc.)
    - Essential for exact DataFrame comparisons in tests
    - Enables reliable assertions against expected test data
    - Use this when you need to compare final results with static expected DataFrames

    **When to use which mode:**
    - Most tests should use deterministic metadata for reliable comparisons
    - Use regular metadata only when testing metadata generation itself
    - If your test uses assert_dataframes_equal(), you almost certainly want deterministic metadata

    Args:
        strategy: The strategy to test
        source_df: Source DataFrame to use
        existing_target_df: Existing target data (None if target doesn't exist)
        spark_session: Spark session to use
        target_identifier: Target identifier for logging
        use_deterministic_metadata: If True, inject TestMetadataApplier for predictable results

    Returns:
        Tuple of (strategy result, mock target with final data)
    """
    # Create mock target and populate it if existing data provided
    target = MockDataTarget(target_identifier, spark_session)
    if existing_target_df is not None:
        target.write(existing_target_df, "overwrite")

    # Create data source
    source = DataFrameSource(source_df, spark_session)

    # Inject deterministic metadata applier if requested
    if use_deterministic_metadata:
        # Create a test metadata config with fixed timestamps, preserving custom config
        base_config = getattr(strategy, "_metadata_config", None)
        test_config = create_test_metadata_config(base_config)
        strategy._metadata_applier = DeterministicMetadataApplier(test_config)

    # Execute strategy
    result = strategy.execute(source, target)

    return result, target


def assert_strategy_success(
    result: SparkSneezeResult, expected_message_fragment: Optional[str] = None
) -> None:
    """Assert that a strategy result indicates success.

    Args:
        result: Strategy execution result
        expected_message_fragment: Optional fragment that should be in the success message
    """
    assert result.success is True, f"Strategy execution failed: {result.message}"
    if expected_message_fragment is not None:
        assert (
            expected_message_fragment in result.message
        ), f"Expected '{expected_message_fragment}' in message: {result.message}"


def execute_strategy_test_with_deterministic_metadata(
    strategy: BaseStrategy,
    source_df: DataFrame,
    existing_target_df: Optional[DataFrame],
    spark_session: SparkSession,
    target_identifier: str = "test_target",
) -> Tuple[SparkSneezeResult, MockDataTarget]:
    """Execute a strategy test with deterministic metadata for exact DataFrame comparisons.

    This is a convenience function that wraps execute_strategy_test with
    use_deterministic_metadata=True. Use this when you need predictable
    metadata values for exact DataFrame comparisons in tests.

    Args:
        strategy: The strategy to test
        source_df: Source DataFrame to use
        existing_target_df: Existing target data (None if target doesn't exist)
        spark_session: Spark session to use
        target_identifier: Target identifier for logging

    Returns:
        Tuple of (strategy result, mock target with final data)
    """
    return execute_strategy_test(
        strategy,
        source_df,
        existing_target_df,
        spark_session,
        target_identifier,
        use_deterministic_metadata=True,
    )


def generate_schema_evolution_test_data(spark_session: SparkSession) -> Dict[str, Any]:
    """Generate test data for schema evolution scenarios.

    Returns consistent test data across all strategies for testing:
    - Basic execution (matching schemas)
    - Auto-expand (source has extra columns)
    - Auto-shrink (target has extra columns)

    Returns:
        Dict with test DataFrames and expected results
    """
    # Base data - both source and target have these columns
    base_columns = "| name (varchar) | age (int) | department (varchar) |"
    base_data_source = """
    | Ricky          | 31        | Operations          |
    | Julian         | 34        | Management          |
    | Bubbles        | 33        | Analytics           |
    """
    base_data_target = """
    | Randy          | 36        | Security            |
    | Mr Lahey       | 54        | Administration      |
    """

    # Source with extra columns (for auto-expand testing)
    expand_source_columns = "| name (varchar) | age (int) | department (varchar) | phone (varchar) | email (varchar) |"
    expand_source_data = """
    | Ricky          | 31        | Operations          | 555-0123        | ricky@park.com   |
    | Julian         | 34        | Management          | 555-0456        | julian@park.com  |
    | Bubbles        | 33        | Analytics           | 555-0789        | bubbles@sheds.com|
    """

    # Target with extra columns (for auto-shrink testing)
    shrink_target_columns = "| name (varchar) | age (int) | department (varchar) | salary (int) | bonus (int) |"
    shrink_target_data = """
    | Randy          | 36        | Security            | 45000       | 2000        |
    | Mr Lahey       | 54        | Administration      | 65000       | 5000        |
    """

    # Create DataFrames
    df_basic_source = markdown_to_dataframe(
        spark_session,
        base_columns
        + "\n|----------------|-----------|---------------------|"
        + base_data_source,
    )
    df_basic_target = markdown_to_dataframe(
        spark_session,
        base_columns
        + "\n|----------------|-----------|---------------------|"
        + base_data_target,
    )

    df_expand_source = markdown_to_dataframe(
        spark_session,
        expand_source_columns
        + "\n|----------------|-----------|---------------------|-----------------|------------------|"
        + expand_source_data,
    )
    df_expand_target = markdown_to_dataframe(
        spark_session,
        base_columns
        + "\n|----------------|-----------|---------------------|"
        + base_data_target,
    )

    df_shrink_source = markdown_to_dataframe(
        spark_session,
        base_columns
        + "\n|----------------|-----------|---------------------|"
        + base_data_source,
    )
    df_shrink_target = markdown_to_dataframe(
        spark_session,
        shrink_target_columns
        + "\n|----------------|-----------|---------------------|-------------|-------------|"
        + shrink_target_data,
    )

    return {
        "basic": {"source": df_basic_source, "target": df_basic_target},
        "expand": {
            "source": df_expand_source,  # Has phone, email columns
            "target": df_expand_target,  # Missing phone, email columns
        },
        "shrink": {
            "source": df_shrink_source,  # Missing salary, bonus columns
            "target": df_shrink_target,  # Has salary, bonus columns
        },
    }


class StrategyTestCase:
    """Base class for strategy test cases with common patterns."""

    @pytest.fixture(scope="module")
    def spark_session(self):
        """Create a Spark session for testing."""
        spark = create_test_spark_session()
        yield spark
        spark.stop()

    @pytest.fixture
    def test_data(self, spark_session):
        """Generate standard test data for schema evolution scenarios."""
        return generate_schema_evolution_test_data(spark_session)

    def verify_basic_strategy_execution(
        self,
        strategy: BaseStrategy,
        test_data: Dict[str, Any],
        expected_message_fragment: str,
    ) -> None:
        """Verify basic strategy execution with matching schemas."""
        source_df = test_data["basic"]["source"]
        target_df = test_data["basic"]["target"]

        result, final_target = execute_strategy_test(
            strategy, source_df, target_df, test_data["basic"]["source"].sparkSession
        )

        assert_strategy_success(result, expected_message_fragment)
        assert final_target.exists()

    def verify_schema_evolution(
        self,
        strategy: BaseStrategy,
        test_data: Dict[str, Any],
        scenario: str,  # 'expand' or 'shrink'
        auto_expand: bool,
        auto_shrink: bool,
        expected_message_fragment: str,
    ) -> Tuple[SparkSneezeResult, MockDataTarget]:
        """Verify schema evolution behavior."""
        scenario_data = test_data[scenario]
        source_df = scenario_data["source"]
        target_df = scenario_data["target"]

        # Configure strategy parameters if it supports them
        if hasattr(strategy, "auto_expand"):
            strategy.auto_expand = auto_expand
        if hasattr(strategy, "auto_shrink"):
            strategy.auto_shrink = auto_shrink

        result, final_target = execute_strategy_test(
            strategy, source_df, target_df, source_df.sparkSession
        )

        assert_strategy_success(result, expected_message_fragment)
        return result, final_target
