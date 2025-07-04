import pytest
from tests.test_utils import (
    create_test_spark_session,
    markdown_to_dataframe,
    assert_dataframes_equal,
    execute_strategy_test_with_deterministic_metadata,
)
from sparksneeze.strategy import DropCreate


@pytest.fixture(scope="module")
def spark_session():
    """Create a Spark session for testing."""
    spark = create_test_spark_session()
    yield spark
    spark.stop()


@pytest.fixture
def test_dataframes(spark_session, request):
    """Create test dataframes for the test class."""
    md_source_table = """
    | name (varchar) (key) | age (int) | occupation (varchar) | location (varchar) |
    |----------------------|-----------|----------------------|--------------------|
    | Ricky          | 31        | Convenience Store    | Trailer Park       |
    | Julian         | 34        | Bar Owner            | Trailer Park       |
    | Bubbles        | 33        | Cat Caretaker        | Shed               |
    | Corey          | 19        | Assistant            | Convenience Store  |
    """

    md_existing_table = """
    | name (varchar) (key) | age (int) | job_title (varchar) |
    |----------------------|-----------|---------------------|
    | Randy          | 36        | Ass. Supervisor     |
    | Mr Lahey       | 54        | Supervisor          |
    | Trevor         | 20        | Assistant           |
    """

    md_expected_table = """
    | name (varchar) (key) | age (int) | occupation (varchar) | location (varchar) | _META_valid_from (timestamp) | _META_valid_to (timestamp) | _META_active (boolean) | _META_row_hash (string) | _META_system_info (string)    |
    |----------------------|-----------|---------------------|---------------------|------------------------------|----------------------------|------------------------|-------------------------|-------------------------------|
    | Bubbles        | 33        | Cat Caretaker       | Shed                | 2024-01-01 00:00:00          | 2999-12-31 23:59:59        | true                   | hash(age,location,occupation)                   | {\"strategy\":\"DropCreate\"} |
    | Corey          | 19        | Assistant           | Convenience Store   | 2024-01-01 00:00:00          | 2999-12-31 23:59:59        | true                   | hash(age,location,occupation)                   | {\"strategy\":\"DropCreate\"} |
    | Julian         | 34        | Bar Owner           | Trailer Park        | 2024-01-01 00:00:00          | 2999-12-31 23:59:59        | true                   | hash(age,location,occupation)                   | {\"strategy\":\"DropCreate\"} |
    | Ricky          | 31        | Convenience Store   | Trailer Park        | 2024-01-01 00:00:00          | 2999-12-31 23:59:59        | true                   | hash(age,location,occupation)                   | {\"strategy\":\"DropCreate\"} |
    """

    df_source_table = markdown_to_dataframe(spark_session, md_source_table)
    df_existing_table = markdown_to_dataframe(spark_session, md_existing_table)
    df_expected_table = markdown_to_dataframe(spark_session, md_expected_table)

    if request.config.getoption("--verbose-dataframes"):
        print("\n=== SOURCE DATAFRAME ===")
        df_source_table.show()
        print("\n=== EXISTING DATAFRAME ===")
        df_existing_table.show()
        print("\n=== EXPECTED DATAFRAME ===")
        df_expected_table.show()

    return {
        "source": df_source_table,
        "existing": df_existing_table,
        "expected": df_expected_table,
    }


class TestStrategyDropCreate:
    def test_initialize_tables(self, test_dataframes):
        df_source_table = test_dataframes["source"]
        df_existing_table = test_dataframes["existing"]
        df_expected_table = test_dataframes["expected"]

        assert df_source_table.count() == 4
        assert "name" in df_source_table.columns
        assert "age" in df_source_table.columns
        assert "occupation" in df_source_table.columns
        assert "location" in df_source_table.columns

        assert df_existing_table.count() == 3
        assert "name" in df_existing_table.columns
        assert "age" in df_existing_table.columns
        assert "job_title" in df_existing_table.columns

        assert df_expected_table.count() == 4
        assert "name" in df_expected_table.columns
        assert "age" in df_expected_table.columns
        assert "occupation" in df_expected_table.columns
        assert "location" in df_expected_table.columns

    def test_strategy_run(self, test_dataframes, spark_session, request):
        df_source_table = test_dataframes["source"]
        df_expected_table = test_dataframes["expected"]

        # Create strategy and execute with deterministic metadata
        strategy = DropCreate()
        existing_data = test_dataframes["existing"]

        result, test_target = execute_strategy_test_with_deterministic_metadata(
            strategy, df_source_table, existing_data, spark_session
        )

        # Verify the strategy succeeded
        assert result.success is True

        # Verify the target was completely replaced with source data
        assert test_target.exists()
        final_data = test_target.get_written_data()
        assert final_data is not None

        if request.config.getoption("--verbose-dataframes"):
            print("\n=== FINAL RESULT DATAFRAME ===")
            final_data.show()

        # Check that the schema matches the source schema (not the original target schema)
        final_schema = final_data.schema
        assert "occupation" in [field.name for field in final_schema.fields]
        assert "location" in [field.name for field in final_schema.fields]
        assert "job_title" not in [field.name for field in final_schema.fields]

        # Verify the data matches exactly what was in the source
        assert_dataframes_equal(final_data, df_expected_table)

    def test_drop_operation_removes_table_structure(self, spark_session, tmp_path):
        """Test that drop() completely removes the Delta table structure."""
        from sparksneeze.data_targets.delta import DeltaTarget

        # Create a Delta table with initial schema
        target_path = str(tmp_path / "test_drop_table")
        target = DeltaTarget(target_path, spark_session)

        # Create initial data with specific schema
        initial_data = spark_session.createDataFrame(
            [(1, "test", 100)], ["id", "name", "value"]
        )
        target.write(initial_data, "overwrite")

        # Verify table exists and has expected schema
        assert target.exists()
        schema = target.get_schema()
        assert schema is not None
        assert len(schema.fields) == 3

        # Drop the table
        target.drop()

        # Verify table no longer exists
        assert not target.exists()
        assert target.get_schema() is None

        # Verify we can create a new table with completely different schema
        new_data = spark_session.createDataFrame(
            [("a", 1.5, True)], ["text", "score", "active"]
        )
        target.write(new_data, "overwrite")

        # Verify new schema is completely different
        new_schema = target.get_schema()
        assert new_schema is not None
        assert len(new_schema.fields) == 3
        field_names = [field.name for field in new_schema.fields]
        assert "text" in field_names
        assert "score" in field_names
        assert "active" in field_names
        # Old fields should not exist
        assert "id" not in field_names
        assert "name" not in field_names
        assert "value" not in field_names

    def test_drop_create_with_schema_evolution(self, spark_session, tmp_path):
        """Test DropCreate strategy with complete schema change."""
        from sparksneeze.data_targets.delta import DeltaTarget
        from sparksneeze.data_sources.dataframe import DataFrameSource

        target_path = str(tmp_path / "test_schema_evolution")
        target = DeltaTarget(target_path, spark_session)

        # Create existing table with old schema
        old_data = spark_session.createDataFrame(
            [(1, "John", 25), (2, "Jane", 30)], ["id", "name", "age"]
        )
        target.write(old_data, "overwrite")

        # Create new data with completely different schema
        new_data = spark_session.createDataFrame(
            [("Product A", 19.99, "Electronics"), ("Product B", 29.99, "Books")],
            ["product_name", "price", "category"],
        )
        source = DataFrameSource(new_data, spark_session)

        # Execute DropCreate strategy
        strategy = DropCreate()
        result = strategy.execute(source, target)

        # Verify success
        assert result.success

        # Verify schema is completely replaced
        final_schema = target.get_schema()
        field_names = [field.name for field in final_schema.fields]

        # New schema fields should exist
        assert "product_name" in field_names
        assert "price" in field_names
        assert "category" in field_names

        # Old schema fields should not exist
        assert "id" not in field_names
        assert "name" not in field_names
        assert "age" not in field_names

        # Metadata fields should be present
        assert "_META_valid_from" in field_names
        assert "_META_valid_to" in field_names
        assert "_META_active" in field_names
        assert "_META_row_hash" in field_names
        assert "_META_system_info" in field_names

    def test_drop_create_error_handling(self, spark_session, tmp_path):
        """Test DropCreate error handling for various failure scenarios."""
        from sparksneeze.data_targets.delta import DeltaTarget
        from sparksneeze.data_sources.dataframe import DataFrameSource

        # Test with non-existent target (should succeed)
        target_path = str(tmp_path / "non_existent_table")
        target = DeltaTarget(target_path, spark_session)

        source_data = spark_session.createDataFrame([(1, "test")], ["id", "value"])
        source = DataFrameSource(source_data, spark_session)

        strategy = DropCreate()
        result = strategy.execute(source, target)

        # Should succeed even with non-existent target
        assert result.success
        assert target.exists()

        # Verify data was written correctly
        final_data = target.read()
        assert final_data.count() == 1

    def test_catalog_table_identification(self, spark_session):
        """Test the _is_catalog_table() method correctly identifies different table types."""
        from sparksneeze.data_targets.delta import DeltaTarget

        # Test path-based tables (should return False)
        path_cases = [
            "/path/to/table",
            "/home/user/data.delta",
            "s3://bucket/path/table",
            "abfss://container@account.dfs.core.windows.net/path",
            "hdfs://namenode:port/path/table",
            "file:///local/path/table",
            "relative/path/table.delta",
            "table.parquet",
            "data.json",
        ]

        for path in path_cases:
            target = DeltaTarget(path, spark_session)
            assert (
                not target._is_catalog_table()
            ), f"Path '{path}' should not be identified as catalog table"

        # Test catalog tables (should return True)
        catalog_cases = [
            "database.table",
            "catalog.database.table",
            "my_db.my_table",
            "prod_catalog.sales_db.customers",
        ]

        for table_name in catalog_cases:
            target = DeltaTarget(table_name, spark_session)
            assert (
                target._is_catalog_table()
            ), f"Table '{table_name}' should be identified as catalog table"

        # Test edge cases (should return False)
        edge_cases = [
            "table",  # No dots - simple table name, treated as path
            ".",  # Just dot
            ".table",  # Starts with dot
            "db.",  # Ends with dot
            "a.b.c.d",  # Too many parts
        ]

        for case in edge_cases:
            target = DeltaTarget(case, spark_session)
            assert (
                not target._is_catalog_table()
            ), f"Edge case '{case}' should not be identified as catalog table"

    def test_drop_catalog_table(self, spark_session):
        """Test dropping a catalog-managed Delta table."""
        from sparksneeze.data_targets.delta import DeltaTarget

        # Create a test catalog table
        table_name = "test_db.test_drop_catalog"

        # Create the database first
        spark_session.sql("CREATE DATABASE IF NOT EXISTS test_db")

        # Create a Delta table in the catalog
        test_data = spark_session.createDataFrame(
            [(1, "test"), (2, "data")], ["id", "value"]
        )
        test_data.write.format("delta").mode("overwrite").saveAsTable(table_name)

        # Verify table exists in catalog
        assert spark_session.catalog.tableExists(table_name)

        # Test DeltaTarget with catalog table
        target = DeltaTarget(table_name, spark_session)
        assert target._is_catalog_table()
        assert target.exists()

        # Drop the table
        target.drop()

        # Verify table no longer exists in catalog
        assert not spark_session.catalog.tableExists(table_name)
        assert not target.exists()

        # Clean up database
        spark_session.sql("DROP DATABASE IF EXISTS test_db CASCADE")
