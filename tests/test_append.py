import pytest
from tests.test_utils import (
    StrategyTestCase,
    execute_strategy_test_with_deterministic_metadata,
    assert_strategy_success,
    assert_dataframes_equal,
    markdown_to_dataframe,
)
from sparksneeze.strategy import Append


class TestStrategyAppend(StrategyTestCase):
    """Test cases for Append strategy."""

    @pytest.fixture
    def basic_test_data(self, spark_session, request):
        """Create basic test dataframes with matching schemas."""
        md_source_table = """
        | name (varchar) | age (int) | business (varchar)  | income (int) |
        |----------------------|-----------|---------------------|--------------|
        | Ricky          | 31        | Get Rich Quick        | 2500         |
        | Julian         | 34        | Bar Business        | 5000         |
        | Bubbles        | 33        | Cart Business       | 1200         |
        """

        md_existing_target = """
        | name (varchar) | age (int) | business (varchar)  | income (int) | _META_valid_from (timestamp) | _META_valid_to (timestamp) | _META_active (boolean) | _META_row_hash (string) | _META_system_info (string) |
        |----------------------|-----------|---------------------|--------------|------------------------------|----------------------------|------------------------|-------------------------|----------------------------|
        | Randy          | 36        | Security            | 3000         | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,business,income,name)                   | {\"strategy\":\"Append\"}     |
        | Mr Lahey       | 54        | Park Supervisor     | 4500         | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,business,income,name)                  | {\"strategy\":\"Append\"}     |
        """

        md_expected_result = """
        | name (varchar) | age (int) | business (varchar)  | income (int) | _META_valid_from (timestamp) | _META_valid_to (timestamp) | _META_active (boolean) | _META_row_hash (string) | _META_system_info (string) |
        |----------------------|-----------|---------------------|--------------|------------------------------|----------------------------|------------------------|-------------------------|----------------------------|
        | Randy          | 36        | Security            | 3000         | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,business,income,name)                   | {\"strategy\":\"Append\"}     |
        | Mr Lahey       | 54        | Park Supervisor     | 4500         | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,business,income,name)                   | {\"strategy\":\"Append\"}     |
        | Bubbles        | 33        | Cart Business       | 1200         | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,business,income,name)                   | {\"strategy\":\"Append\"}     |
        | Julian         | 34        | Bar Business        | 5000         | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,business,income,name)                   | {\"strategy\":\"Append\"}     |
        | Ricky          | 31        | Get Rich Quick        | 2500         | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,business,income,name)                   | {\"strategy\":\"Append\"}     |
        """

        df_source_table = markdown_to_dataframe(spark_session, md_source_table)
        df_existing_target = markdown_to_dataframe(spark_session, md_existing_target)
        df_expected_result = markdown_to_dataframe(spark_session, md_expected_result)

        if request.config.getoption("--verbose-dataframes"):
            print("\n=== SOURCE DATAFRAME ===")
            df_source_table.show()
            print("\n=== EXISTING TARGET DATAFRAME ===")
            df_existing_target.show()
            print("\n=== EXPECTED RESULT DATAFRAME ===")
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
        | name (varchar) | age (int) | business (varchar)  | income (int) | phone (varchar) | email (varchar)      |
        |----------------------|-----------|---------------------|--------------|-----------------|----------------------|
        | Ricky          | 31        | Get Rich Quick        | 2500         | 555-0123        | ricky@park.com       |
        | Julian         | 34        | Bar Business        | 5000         | 555-0456        | julian@park.com      |
        | Bubbles        | 33        | Cart Business       | 1200         | 555-0789        | bubbles@sheds.com    |
        """

        # Target has fewer columns than source (missing phone, email)
        md_existing_target = """
        | name (varchar) | age (int) | business (varchar)  | income (int) | _META_valid_from (timestamp) | _META_valid_to (timestamp) | _META_active (boolean) | _META_row_hash (string) | _META_system_info (string) |
        |----------------------|-----------|---------------------|--------------|------------------------------|----------------------------|------------------------|-------------------------|----------------------------|
        | Randy          | 36        | Security            | 3000         | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,business,income,name)                   | {\"strategy\":\"Append\"}     |
        | Mr Lahey       | 54        | Park Supervisor     | 4500         | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,business,income,name)                   | {\"strategy\":\"Append\"}     |
        """

        # Expected result with auto_expand=True should include all columns
        # Existing rows (Randy, Mr Lahey) keep original hash based on pre-expansion schema (age,business,income,name)
        # New rows (Bubbles, Julian, Ricky) get hash based on expanded schema (age,business,email,income,name,phone)
        md_expected_result_auto_expand = """
        | name (varchar) | age (int) | business (varchar)  | income (int) | phone (varchar) | email (varchar)      | _META_valid_from (timestamp) | _META_valid_to (timestamp) | _META_active (boolean) | _META_row_hash (string) | _META_system_info (string) |
        |----------------------|-----------|---------------------|--------------|-----------------|----------------------|------------------------------|----------------------------|------------------------|-------------------------|----------------------------|
        | Randy          | 36        | Security            | 3000         | null            | null                 | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,business,income,name)                   | {\"strategy\":\"Append\"}     |
        | Mr Lahey       | 54        | Park Supervisor     | 4500         | null            | null                 | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,business,income,name)                   | {\"strategy\":\"Append\"}     |
        | Bubbles        | 33        | Cart Business       | 1200         | 555-0789        | bubbles@sheds.com    | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,business,email,income,name,phone)                   | {\"strategy\":\"Append\"}     |
        | Julian         | 34        | Bar Business        | 5000         | 555-0456        | julian@park.com      | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,business,email,income,name,phone)                   | {\"strategy\":\"Append\"}     |
        | Ricky          | 31        | Get Rich Quick        | 2500         | 555-0123        | ricky@park.com       | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,business,email,income,name,phone)                   | {\"strategy\":\"Append\"}     |
        """

        # Expected result with auto_expand=False should only include target columns
        md_expected_result_no_expand = """
        | name (varchar) | age (int) | business (varchar)  | income (int) | _META_valid_from (timestamp) | _META_valid_to (timestamp) | _META_active (boolean) | _META_row_hash (string) | _META_system_info (string) |
        |----------------------|-----------|---------------------|--------------|------------------------------|----------------------------|------------------------|-------------------------|----------------------------|
        | Randy          | 36        | Security            | 3000         | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,business,income,name)                   | {\"strategy\":\"Append\"}     |
        | Mr Lahey       | 54        | Park Supervisor     | 4500         | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,business,income,name)                   | {\"strategy\":\"Append\"}     |
        | Bubbles        | 33        | Cart Business       | 1200         | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,business,income,name)                   | {\"strategy\":\"Append\"}     |
        | Julian         | 34        | Bar Business        | 5000         | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,business,income,name)                   | {\"strategy\":\"Append\"}     |
        | Ricky          | 31        | Get Rich Quick        | 2500         | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,business,income,name)                   | {\"strategy\":\"Append\"}     |
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
            print("\n=== AUTO EXPAND - SOURCE DATAFRAME ===")
            df_source_table.show()
            print("\n=== AUTO EXPAND - EXISTING TARGET DATAFRAME ===")
            df_existing_target.show()
            print("\n=== AUTO EXPAND - EXPECTED RESULT (AUTO_EXPAND=TRUE) ===")
            df_expected_result_auto_expand.show()
            print("\n=== AUTO EXPAND - EXPECTED RESULT (AUTO_EXPAND=FALSE) ===")
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
        | name (varchar) | age (int) | business (varchar)  |
        |----------------------|-----------|---------------------|
        | Ricky          | 31        | Get Rich Quick        |
        | Julian         | 34        | Bar Business        |
        | Bubbles        | 33        | Cart Business       |
        """

        # Target has more columns than source (has income, phone)
        md_existing_target = """
        | name (varchar) | age (int) | business (varchar)  | income (int) | phone (varchar) | _META_valid_from (timestamp) | _META_valid_to (timestamp) | _META_active (boolean) | _META_row_hash (string) | _META_system_info (string) |
        |----------------------|-----------|---------------------|--------------|-----------------|------------------------------|----------------------------|------------------------|-------------------------|----------------------------|
        | Randy          | 36        | Security            | 3000         | 555-9999        | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,business,income,name,phone)                   | {\"strategy\":\"Append\"}   |
        | Mr Lahey       | 54        | Park Supervisor     | 4500         | 555-8888        | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,business,income,name,phone)                   | {\"strategy\":\"Append\"}   |
        """

        # Expected result with auto_shrink=True should only include source columns
        # Existing rows (Randy, Mr Lahey) keep original hash based on original schema (age,business,income,name,phone)
        # Dropped columns (income,phone) are marked as (dropped) - not in actual data but used for hash calculation
        # New rows (Bubbles, Julian, Ricky) get hash based on final shrunk schema (age,business,name)
        md_expected_result_auto_shrink = """
        | name (varchar) | age (int) | business (varchar) | income (int) (dropped) | phone (varchar) (dropped) | _META_valid_from (timestamp) | _META_valid_to (timestamp) | _META_active (boolean) | _META_row_hash (string) | _META_system_info (string) |
        |----------------------|-----------|---------------------|------------------------|---------------------------|------------------------------|----------------------------|------------------------|-------------------------|----------------------------|
        | Randy          | 36        | Security            | 3000                   | 555-9999                  | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,business,income,name,phone)                   | {\"strategy\":\"Append\"}     |
        | Mr Lahey       | 54        | Park Supervisor     | 4500                   | 555-8888                  | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,business,income,name,phone)                   | {\"strategy\":\"Append\"}     |
        | Bubbles        | 33        | Cart Business       | null                   | null                      | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,business,name)                   | {\"strategy\":\"Append\"}     |
        | Julian         | 34        | Bar Business        | null                   | null                      | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,business,name)                   | {\"strategy\":\"Append\"}     |
        | Ricky          | 31        | Get Rich Quick        | null                   | null                      | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,business,name)                   | {\"strategy\":\"Append\"}     |
        """

        # Expected result with auto_shrink=False should keep target columns
        # Existing rows (Randy, Mr Lahey) keep original hash based on pre-shrink schema (age,business,income,name,phone)
        # New rows (Bubbles, Julian, Ricky) get hash based on current target schema (age,business,income,name,phone)
        md_expected_result_no_shrink = """
        | name (varchar) | age (int) | business (varchar)  | income (int) | phone (varchar) | _META_valid_from (timestamp) | _META_valid_to (timestamp) | _META_active (boolean) | _META_row_hash (string) | _META_system_info (string) |
        |----------------------|-----------|---------------------|--------------|-----------------|------------------------------|----------------------------|------------------------|-------------------------|----------------------------|
        | Randy          | 36        | Security            | 3000         | 555-9999        | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,business,income,name,phone)                   | {\"strategy\":\"Append\"}     |
        | Mr Lahey       | 54        | Park Supervisor     | 4500         | 555-8888        | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,business,income,name,phone)                   | {\"strategy\":\"Append\"}     |
        | Bubbles        | 33        | Cart Business       | null         | null            | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,business,income,name,phone)                   | {\"strategy\":\"Append\"}     |
        | Julian         | 34        | Bar Business        | null         | null            | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,business,income,name,phone)                   | {\"strategy\":\"Append\"}     |
        | Ricky          | 31        | Get Rich Quick        | null         | null            | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,business,income,name,phone)                   | {\"strategy\":\"Append\"}     |
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
            print("\n=== AUTO SHRINK - SOURCE DATAFRAME ===")
            df_source_table.show()
            print("\n=== AUTO SHRINK - EXISTING TARGET DATAFRAME ===")
            df_existing_target.show()
            print("\n=== AUTO SHRINK - EXPECTED RESULT (AUTO_SHRINK=TRUE) ===")
            df_expected_result_auto_shrink.show()
            print("\n=== AUTO SHRINK - EXPECTED RESULT (AUTO_SHRINK=FALSE) ===")
            df_expected_result_no_shrink.show()

        return {
            "source": df_source_table,
            "existing_target": df_existing_target,
            "expected_auto_shrink": df_expected_result_auto_shrink,
            "expected_no_shrink": df_expected_result_no_shrink,
        }

    def test_basic_execution(self, basic_test_data, request):
        """Test Append strategy with matching schemas."""
        strategy = Append(auto_expand=True, auto_shrink=False)
        source_df = basic_test_data["source"]
        target_df = basic_test_data["existing_target"]
        expected_df = basic_test_data["expected"]

        result, final_target = execute_strategy_test_with_deterministic_metadata(
            strategy, source_df, target_df, source_df.sparkSession
        )

        assert_strategy_success(result)
        assert final_target.exists()

        # Verify existing data is preserved and source data is appended with metadata
        final_data = final_target.get_written_data()
        assert final_data is not None

        if request.config.getoption("--verbose-dataframes"):
            print("\n=== FINAL OUTPUT DATAFRAME ===")
            final_data.show()

        assert_dataframes_equal(final_data, expected_df)

        # Verify strategy parameters
        assert strategy.auto_expand is True
        assert strategy.auto_shrink is False

    def test_append_auto_expand_true(self, auto_expand_test_data):
        """Test Append strategy with auto_expand=True should add new columns from source."""
        strategy = Append(auto_expand=True, auto_shrink=False)
        source_df = auto_expand_test_data["source"]
        target_df = auto_expand_test_data["existing_target"]

        result, final_target = execute_strategy_test_with_deterministic_metadata(
            strategy, source_df, target_df, source_df.sparkSession
        )

        assert_strategy_success(result)
        assert final_target.exists()
        assert strategy.auto_expand is True
        assert strategy.auto_shrink is False

        # Verify final result matches expected with expanded schema
        final_data = final_target.get_written_data()
        assert final_data is not None
        expected_df = auto_expand_test_data["expected_auto_expand"]
        assert_dataframes_equal(final_data, expected_df)

    def test_append_auto_expand_false(self, auto_expand_test_data):
        """Test Append strategy with auto_expand=False should not add new columns."""
        strategy = Append(auto_expand=False, auto_shrink=False)
        source_df = auto_expand_test_data["source"]
        target_df = auto_expand_test_data["existing_target"]

        result, final_target = execute_strategy_test_with_deterministic_metadata(
            strategy, source_df, target_df, source_df.sparkSession
        )

        assert_strategy_success(result)
        assert final_target.exists()
        assert strategy.auto_expand is False
        assert strategy.auto_shrink is False

        # Verify final result matches target schema without expansion
        final_data = final_target.get_written_data()
        assert final_data is not None
        expected_df = auto_expand_test_data["expected_no_expand"]
        assert_dataframes_equal(final_data, expected_df)

    def test_append_auto_shrink_true(self, auto_shrink_test_data):
        """Test Append strategy with auto_shrink=True should remove columns not in source."""
        strategy = Append(auto_expand=False, auto_shrink=True)
        source_df = auto_shrink_test_data["source"]
        target_df = auto_shrink_test_data["existing_target"]

        result, final_target = execute_strategy_test_with_deterministic_metadata(
            strategy, source_df, target_df, source_df.sparkSession
        )

        assert_strategy_success(result)
        assert final_target.exists()
        assert strategy.auto_expand is False
        assert strategy.auto_shrink is True

        # Verify final result matches source schema with shrinking
        final_data = final_target.get_written_data()
        assert final_data is not None
        expected_df = auto_shrink_test_data["expected_auto_shrink"]
        assert_dataframes_equal(final_data, expected_df)

    def test_append_auto_shrink_false(self, auto_shrink_test_data):
        """Test Append strategy with auto_shrink=False should keep target columns."""
        strategy = Append(auto_expand=False, auto_shrink=False)
        source_df = auto_shrink_test_data["source"]
        target_df = auto_shrink_test_data["existing_target"]

        result, final_target = execute_strategy_test_with_deterministic_metadata(
            strategy, source_df, target_df, source_df.sparkSession
        )

        assert_strategy_success(result)
        assert final_target.exists()
        assert strategy.auto_expand is False
        assert strategy.auto_shrink is False

        # Verify final result keeps all target columns without shrinking
        final_data = final_target.get_written_data()
        assert final_data is not None
        expected_df = auto_shrink_test_data["expected_no_shrink"]
        assert_dataframes_equal(final_data, expected_df)

    def test_append_preserves_existing_data(self, basic_test_data, request):
        """Test that Append strategy preserves existing target data."""
        source_df = basic_test_data["source"]
        target_df = basic_test_data["existing_target"]
        expected_df = basic_test_data["expected"]

        strategy = Append(auto_expand=True, auto_shrink=False)
        result, final_target = execute_strategy_test_with_deterministic_metadata(
            strategy, source_df, target_df, source_df.sparkSession
        )

        assert_strategy_success(result)
        assert final_target.exists()

        # Verify original target data is preserved and source data is added
        final_data = final_target.get_written_data()
        assert final_data is not None

        if request.config.getoption("--verbose-dataframes"):
            print("\n=== PRESERVE DATA TEST - FINAL OUTPUT DATAFRAME ===")
            final_data.show()

        # Total row count should be original target rows + source rows
        expected_total_rows = target_df.count() + source_df.count()
        assert final_data.count() == expected_total_rows

        # All data should match expected with metadata
        assert_dataframes_equal(final_data, expected_df)

    def test_strategy_parameters(self):
        """Test Append strategy parameter initialization."""
        # Test default parameters
        strategy_default = Append()
        assert strategy_default.auto_expand is True
        assert strategy_default.auto_shrink is False

        # Test custom parameters
        strategy_custom = Append(auto_expand=False, auto_shrink=True)
        assert strategy_custom.auto_expand is False
        assert strategy_custom.auto_shrink is True
