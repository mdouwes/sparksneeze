import pytest
from tests.test_utils import (
    StrategyTestCase,
    execute_strategy_test,
    execute_strategy_test_with_deterministic_metadata,
    assert_strategy_success,
    assert_dataframes_equal,
    markdown_to_dataframe,
)
from sparksneeze.strategy import Truncate


class TestStrategyTruncate(StrategyTestCase):
    """Test cases for Truncate strategy."""

    @pytest.fixture
    def basic_test_data(self, spark_session, request):
        """Create basic test dataframes with matching schemas."""
        md_source_table = """
        | name (varchar) | age (int) | job (varchar)   |
        |----------------------|-----------|-----------------|
        | Ricky                | 31        | Sales Agent     |
        | Julian               | 34        | Manager         |
        | Bubbles              | 33        | Analyst         |
        """

        md_existing_target = """
        | name (varchar) | age (int) | job (varchar)   | _META_valid_from (timestamp) | _META_valid_to (timestamp) | _META_active (boolean) | _META_row_hash (string) | _META_system_info (string) |
        |----------------------|-----------|-----------------|------------------------------|----------------------------|------------------------|-------------------------|----------------------------|
        | Randy                | 36        | Ass. Supervisor | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,job,name)                   | {"strategy":"Truncate"}   |
        | Mr  Lahey            | 54        | Supervisor      | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,job,name)                   | {"strategy":"Truncate"}   |
        """

        md_expected_result = """
        | name (varchar) | age (int) | job (varchar)   | _META_valid_from (timestamp) | _META_valid_to (timestamp) | _META_active (boolean) | _META_row_hash (string) | _META_system_info (string) |
        |----------------------|-----------|-----------------|------------------------------|----------------------------|------------------------|-------------------------|----------------------------|
        | Bubbles              | 33        | Analyst         | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,job,name)                   | {\"strategy\":\"Truncate\"}   |
        | Julian               | 34        | Manager         | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,job,name)                   | {\"strategy\":\"Truncate\"}   |
        | Ricky                | 31        | Sales Agent     | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,job,name)                   | {\"strategy\":\"Truncate\"}   |
        """

        df_source_table = markdown_to_dataframe(spark_session, md_source_table)
        df_existing_target = markdown_to_dataframe(spark_session, md_existing_target)
        df_expected_result = markdown_to_dataframe(spark_session, md_expected_result)

        if request.config.getoption("--verbose-dataframes"):
            print("\n=== TRUNCATE - SOURCE DATAFRAME ===")
            df_source_table.show()
            print("\n=== TRUNCATE - EXISTING TARGET DATAFRAME ===")
            df_existing_target.show()
            print("\n=== TRUNCATE - EXPECTED RESULT DATAFRAME ===")
            df_expected_result.show()

        return {
            "source": df_source_table,
            "existing_target": df_existing_target,
            "expected": df_expected_result,
        }

    @pytest.fixture
    def auto_expand_test_data(self, spark_session, request):
        """Create test dataframes for schema expansion testing."""
        # Source has additional columns compared to target
        md_source_table = """
        | name (varchar) | age (int) | job (varchar)   | department (varchar) | salary (int) |
        |----------------------|-----------|-----------------|---------------------|--------------|
        | Ricky                | 31        | Sales Agent     | Sales               | 45000        |
        | Julian               | 34        | Manager         | Operations          | 65000        |
        | Bubbles              | 33        | Analyst         | Analytics           | 55000        |
        """

        # Target has fewer columns than source (missing department, salary)
        md_existing_target = """
        | name (varchar) | age (int) | job (varchar)   | _META_valid_from (timestamp) | _META_valid_to (timestamp) | _META_active (boolean) | _META_row_hash (string) | _META_system_info (string) |
        |----------------------|-----------|-----------------|------------------------------|----------------------------|------------------------|-------------------------|----------------------------|
        | Randy                | 36        | Ass. Supervisor | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,job,name)                   | {"strategy":"Truncate"}   |
        | Mr  Lahey            | 54        | Supervisor      | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,job,name)                   | {"strategy":"Truncate"}   |
        """

        # Expected result with auto_expand=True should include all columns
        md_expected_result_auto_expand = """
        | name (varchar) | age (int) | job (varchar)   | department (varchar) | salary (int) | _META_valid_from (timestamp) | _META_valid_to (timestamp) | _META_active (boolean) | _META_row_hash (string) | _META_system_info (string) |
        |----------------------|-----------|-----------------|---------------------|--------------|------------------------------|----------------------------|------------------------|-------------------------|----------------------------|
        | Bubbles              | 33        | Analyst         | Analytics           | 55000        | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,department,job,name,salary)                   | {\"strategy\":\"Truncate\"}   |
        | Julian               | 34        | Manager         | Operations          | 65000        | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,department,job,name,salary)                   | {\"strategy\":\"Truncate\"}   |
        | Ricky                | 31        | Sales Agent     | Sales               | 45000        | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,department,job,name,salary)                   | {\"strategy\":\"Truncate\"}   |
        """

        # Expected result with auto_expand=False should only include target columns
        md_expected_result_no_expand = """
        | name (varchar) | age (int) | job (varchar)   | _META_valid_from (timestamp) | _META_valid_to (timestamp) | _META_active (boolean) | _META_row_hash (string) | _META_system_info (string) |
        |----------------------|-----------|-----------------|------------------------------|----------------------------|------------------------|-------------------------|----------------------------|
        | Bubbles              | 33        | Analyst         | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,job,name)                   | {\"strategy\":\"Truncate\"}   |
        | Julian               | 34        | Manager         | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,job,name)                   | {\"strategy\":\"Truncate\"}   |
        | Ricky                | 31        | Sales Agent     | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,job,name)                   | {\"strategy\":\"Truncate\"}   |
        """

        df_source_table = markdown_to_dataframe(spark_session, md_source_table)
        df_existing_target = markdown_to_dataframe(spark_session, md_existing_target)
        df_expected_result_auto_expand = markdown_to_dataframe(
            spark_session, md_expected_result_auto_expand
        )
        df_expected_result_no_expand = markdown_to_dataframe(
            spark_session, md_expected_result_no_expand
        )

        if request.config.getoption("--verbose-dataframes"):
            print("\n=== TRUNCATE AUTO EXPAND - SOURCE DATAFRAME ===")
            df_source_table.show()
            print("\n=== TRUNCATE AUTO EXPAND - EXISTING TARGET DATAFRAME ===")
            df_existing_target.show()
            print("\n=== TRUNCATE AUTO EXPAND - EXPECTED RESULT (AUTO_EXPAND=TRUE) ===")
            df_expected_result_auto_expand.show()
            print(
                "\n=== TRUNCATE AUTO EXPAND - EXPECTED RESULT (AUTO_EXPAND=FALSE) ==="
            )
            df_expected_result_no_expand.show()

        return {
            "source": df_source_table,
            "existing_target": df_existing_target,
            "expected_auto_expand": df_expected_result_auto_expand,
            "expected_no_expand": df_expected_result_no_expand,
        }

    @pytest.fixture
    def auto_shrink_test_data(self, spark_session, request):
        """Create test dataframes for schema shrinking testing."""
        # Source has fewer columns than target
        md_source_table = """
        | name (varchar) | age (int) | job (varchar)   |
        |----------------------|-----------|-----------------|
        | Ricky                | 31        | Sales Agent     |
        | Julian               | 34        | Manager         |
        | Bubbles              | 33        | Analyst         |
        """

        # Target has more columns than source (has department, salary)
        md_existing_target = """
        | name (varchar) | age (int) | job (varchar)   | department (varchar) | salary (int) | _META_valid_from (timestamp) | _META_valid_to (timestamp) | _META_active (boolean) | _META_row_hash (string) | _META_system_info (string) |
        |----------------------|-----------|-----------------|---------------------|--------------|------------------------------|----------------------------|------------------------|-------------------------|----------------------------|
        | Randy                | 36        | Ass. Supervisor | Administration      | 50000        | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,job,name)                   | {"strategy":"Truncate"}   |
        | Mr  Lahey            | 54        | Supervisor      | Management          | 70000        | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,job,name)                   | {"strategy":"Truncate"}   |
        """

        # Expected result with auto_shrink=True should only include source columns
        md_expected_result_auto_shrink = """
        | name (varchar) | age (int) | job (varchar)   | _META_valid_from (timestamp) | _META_valid_to (timestamp) | _META_active (boolean) | _META_row_hash (string) | _META_system_info (string) |
        |----------------------|-----------|-----------------|------------------------------|----------------------------|------------------------|-------------------------|----------------------------|
        | Bubbles              | 33        | Analyst         | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,job,name)                   | {\"strategy\":\"Truncate\"}   |
        | Julian               | 34        | Manager         | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,job,name)                   | {\"strategy\":\"Truncate\"}   |
        | Ricky                | 31        | Sales Agent     | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,job,name)                   | {\"strategy\":\"Truncate\"}   |
        """

        # Expected result with auto_shrink=False should keep target columns
        # All rows are new after truncation, so hash includes final target schema (age,department,job,name,salary)
        # Source data gets null values for missing target columns (department, salary)
        md_expected_result_no_shrink = """
        | name (varchar) | age (int) | job (varchar)   | department (varchar) | salary (int) | _META_valid_from (timestamp) | _META_valid_to (timestamp) | _META_active (boolean) | _META_row_hash (string) | _META_system_info (string) |
        |----------------------|-----------|-----------------|---------------------|--------------|------------------------------|----------------------------|------------------------|-------------------------|----------------------------|
        | Bubbles              | 33        | Analyst         | null                | null         | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,department,job,name,salary)                   | {\"strategy\":\"Truncate\"}   |
        | Julian               | 34        | Manager         | null                | null         | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,department,job,name,salary)                   | {\"strategy\":\"Truncate\"}   |
        | Ricky                | 31        | Sales Agent     | null                | null         | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,department,job,name,salary)                   | {\"strategy\":\"Truncate\"}   |
        """

        df_source_table = markdown_to_dataframe(spark_session, md_source_table)
        df_existing_target = markdown_to_dataframe(spark_session, md_existing_target)
        df_expected_result_auto_shrink = markdown_to_dataframe(
            spark_session, md_expected_result_auto_shrink
        )
        df_expected_result_no_shrink = markdown_to_dataframe(
            spark_session, md_expected_result_no_shrink
        )

        if request.config.getoption("--verbose-dataframes"):
            print("\n=== TRUNCATE AUTO SHRINK - SOURCE DATAFRAME ===")
            df_source_table.show()
            print("\n=== TRUNCATE AUTO SHRINK - EXISTING TARGET DATAFRAME ===")
            df_existing_target.show()
            print("\n=== TRUNCATE AUTO SHRINK - EXPECTED RESULT (AUTO_SHRINK=TRUE) ===")
            df_expected_result_auto_shrink.show()
            print(
                "\n=== TRUNCATE AUTO SHRINK - EXPECTED RESULT (AUTO_SHRINK=FALSE) ==="
            )
            df_expected_result_no_shrink.show()

        return {
            "source": df_source_table,
            "existing_target": df_existing_target,
            "expected_auto_shrink": df_expected_result_auto_shrink,
            "expected_no_shrink": df_expected_result_no_shrink,
        }

    def test_basic_execution(self, basic_test_data, request):
        """Test Truncate strategy with matching schemas."""
        strategy = Truncate(auto_expand=True, auto_shrink=False)
        source_df = basic_test_data["source"]
        target_df = basic_test_data["existing_target"]
        expected_df = basic_test_data["expected"]

        result, final_target = execute_strategy_test_with_deterministic_metadata(
            strategy, source_df, target_df, source_df.sparkSession
        )

        assert_strategy_success(result)
        assert final_target.exists()

        # Verify the target was cleared and contains only source data with metadata
        final_data = final_target.get_written_data()
        assert final_data is not None

        if request.config.getoption("--verbose-dataframes"):
            print("\n=== TRUNCATE BASIC TEST - FINAL OUTPUT DATAFRAME ===")
            final_data.show()

        assert_dataframes_equal(final_data, expected_df)

        # Verify strategy parameters
        assert strategy.auto_expand is True
        assert strategy.auto_shrink is False

    def test_truncate_auto_expand_true(self, auto_expand_test_data, request):
        """Test Truncate strategy with auto_expand=True should add new columns from source."""
        strategy = Truncate(auto_expand=True, auto_shrink=False)
        source_df = auto_expand_test_data["source"]
        target_df = auto_expand_test_data["existing_target"]
        expected_df = auto_expand_test_data["expected_auto_expand"]

        result, final_target = execute_strategy_test_with_deterministic_metadata(
            strategy, source_df, target_df, source_df.sparkSession
        )

        assert_strategy_success(result)
        assert final_target.exists()
        assert strategy.auto_expand is True
        assert strategy.auto_shrink is False

        # Verify the result matches expected dataframe
        final_data = final_target.get_written_data()
        assert final_data is not None

        if request.config.getoption("--verbose-dataframes"):
            print("\n=== TRUNCATE AUTO EXPAND TRUE - FINAL OUTPUT DATAFRAME ===")
            final_data.show()

        assert_dataframes_equal(final_data, expected_df)

    def test_truncate_auto_expand_false(self, auto_expand_test_data, request):
        """Test Truncate strategy with auto_expand=False should not add new columns."""
        strategy = Truncate(auto_expand=False, auto_shrink=False)
        source_df = auto_expand_test_data["source"]
        target_df = auto_expand_test_data["existing_target"]
        expected_df = auto_expand_test_data["expected_no_expand"]

        result, final_target = execute_strategy_test_with_deterministic_metadata(
            strategy, source_df, target_df, source_df.sparkSession
        )

        assert_strategy_success(result)
        assert final_target.exists()
        assert strategy.auto_expand is False
        assert strategy.auto_shrink is False

        # Verify the result matches expected dataframe
        final_data = final_target.get_written_data()
        assert final_data is not None

        if request.config.getoption("--verbose-dataframes"):
            print("\n=== TRUNCATE AUTO EXPAND FALSE - FINAL OUTPUT DATAFRAME ===")
            final_data.show()

        assert_dataframes_equal(final_data, expected_df)

    def test_truncate_auto_shrink_true(self, auto_shrink_test_data, request):
        """Test Truncate strategy with auto_shrink=True should remove columns not in source."""
        strategy = Truncate(auto_expand=False, auto_shrink=True)
        source_df = auto_shrink_test_data["source"]
        target_df = auto_shrink_test_data["existing_target"]
        expected_df = auto_shrink_test_data["expected_auto_shrink"]

        result, final_target = execute_strategy_test_with_deterministic_metadata(
            strategy, source_df, target_df, source_df.sparkSession
        )

        assert_strategy_success(result)
        assert final_target.exists()
        assert strategy.auto_expand is False
        assert strategy.auto_shrink is True

        # Verify the result matches expected dataframe
        final_data = final_target.get_written_data()
        assert final_data is not None

        if request.config.getoption("--verbose-dataframes"):
            print("\n=== TRUNCATE AUTO SHRINK TRUE - FINAL OUTPUT DATAFRAME ===")
            final_data.show()

        assert_dataframes_equal(final_data, expected_df)

    def test_truncate_auto_shrink_false(self, auto_shrink_test_data, request):
        """Test Truncate strategy with auto_shrink=False should keep target columns."""
        strategy = Truncate(auto_expand=False, auto_shrink=False)
        source_df = auto_shrink_test_data["source"]
        target_df = auto_shrink_test_data["existing_target"]
        expected_df = auto_shrink_test_data["expected_no_shrink"]

        result, final_target = execute_strategy_test_with_deterministic_metadata(
            strategy, source_df, target_df, source_df.sparkSession
        )

        assert_strategy_success(result)
        assert final_target.exists()
        assert strategy.auto_expand is False
        assert strategy.auto_shrink is False

        # Verify the result matches expected dataframe
        final_data = final_target.get_written_data()
        assert final_data is not None

        if request.config.getoption("--verbose-dataframes"):
            print("\n=== TRUNCATE AUTO SHRINK FALSE - FINAL OUTPUT DATAFRAME ===")
            final_data.show()

        assert_dataframes_equal(final_data, expected_df)

    def test_truncate_clears_existing_data(self, basic_test_data):
        """Test that Truncate strategy clears existing target data."""
        source_df = basic_test_data["source"]
        target_df = basic_test_data["existing_target"]

        strategy = Truncate(auto_expand=True, auto_shrink=False)
        result, final_target = execute_strategy_test(
            strategy, source_df, target_df, source_df.sparkSession
        )

        assert_strategy_success(result)
        assert final_target.exists()

        # Verify original target data is cleared
        final_data = final_target.get_written_data()
        assert final_data is not None

        # Only source data should remain (3 rows, not 2 original + 3 source)
        assert final_data.count() == 3

        # Verify it contains only source data
        names = [row.name for row in final_data.collect()]
        assert "Ricky" in names
        assert "Julian" in names
        assert "Bubbles" in names

        # Original target data should be completely cleared
        assert "Randy" not in names
        assert "Mr  Lahey" not in names

    def test_strategy_parameters(self):
        """Test Truncate strategy parameter initialization."""
        # Test default parameters
        strategy_default = Truncate()
        assert strategy_default.auto_expand is True
        assert strategy_default.auto_shrink is False

        # Test custom parameters
        strategy_custom = Truncate(auto_expand=False, auto_shrink=True)
        assert strategy_custom.auto_expand is False
        assert strategy_custom.auto_shrink is True

    def test_truncate_with_empty_target(self, basic_test_data):
        """Test Truncate strategy when target doesn't exist initially."""
        source_df = basic_test_data["source"]

        strategy = Truncate(auto_expand=True, auto_shrink=False)
        result, final_target = execute_strategy_test(
            strategy,
            source_df,
            None,
            source_df.sparkSession,  # None = no existing target
        )

        assert_strategy_success(result)
        # Verify target is created with source data
        final_data = final_target.get_written_data()
        assert final_data is not None
        assert final_data.count() == 3  # Should contain all source rows

        # Verify it contains source data
        names = [row.name for row in final_data.collect()]
        assert "Ricky" in names
        assert "Julian" in names
        assert "Bubbles" in names
