import pytest
from tests.test_utils import (
    StrategyTestCase,
    execute_strategy_test,
    execute_strategy_test_with_deterministic_metadata,
    assert_strategy_success,
    assert_dataframes_equal,
    markdown_to_dataframe,
)
from sparksneeze.strategy import Upsert


class TestStrategyUpsert(StrategyTestCase):
    """Test cases for Upsert strategy."""

    @pytest.fixture
    def basic_test_data(self, spark_session, request):
        """Create basic test dataframes with matching schemas."""
        md_source_table = """
        | character_id (int) (key) | name (varchar) | age (int) | status (varchar)    | money (int) |
        |--------------------------|----------------|-----------|---------------------|-------------|
        | 1                  | Ricky          | 32        | Out of Jail         | 150         |
        | 2                  | Julian         | 35        | Running Bar         | 5500        |
        | 4                  | Bubbles        | 34        | Cart Supervisor     | 1800        |
        | 5                  | Corey          | 20        | Working at Store    | 800         |
        """

        md_existing_target = """
        | character_id (int) (key) | name (varchar) | age (int) | status (varchar)    | money (int) | _META_valid_from (timestamp) | _META_valid_to (timestamp) | _META_active (boolean) | _META_row_hash (string) | _META_system_info (string) |
        |--------------------------|----------------|-----------|---------------------|-------------|------------------------------|----------------------------|------------------------|-------------------------|----------------------------|
        | 1                  | Ricky          | 31        | In Jail             | 50          | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,money,name,status)                   | {"strategy":"Upsert"}     |
        | 2                  | Julian         | 34        | Planning Schemes    | 3000        | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,money,name,status)                   | {"strategy":"Upsert"}     |
        | 3                  | Randy          | 36        | Ass. Supervisor     | 2500        | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,money,name,status)                   | {"strategy":"Upsert"}     |
        """

        md_expected_result = """
        | character_id (int) (key) | name (varchar) | age (int) | status (varchar)    | money (int) | _META_valid_from (timestamp) | _META_valid_to (timestamp) | _META_active (boolean) | _META_row_hash (string) | _META_system_info (string)    |
        |--------------------------|----------------|-----------|---------------------|-------------|------------------------------|----------------------------|------------------------|-------------------------|-------------------------------|
        | 1                  | Ricky          | 32        | Out of Jail         | 150         | 2024-01-01 00:00:00          | 2999-12-31 23:59:59        | true                   | hash(age,money,name,status)                   | {"strategy":"Upsert"}        |
        | 2                  | Julian         | 35        | Running Bar         | 5500        | 2024-01-01 00:00:00          | 2999-12-31 23:59:59        | true                   | hash(age,money,name,status)                   | {"strategy":"Upsert"}        |
        | 3                  | Randy          | 36        | Ass. Supervisor     | 2500        | 2024-01-01 00:00:00          | 2999-12-31 23:59:59        | true                   | hash(age,money,name,status)                   | {"strategy":"Upsert"}        |
        | 4                  | Bubbles        | 34        | Cart Supervisor     | 1800        | 2024-01-01 00:00:00          | 2999-12-31 23:59:59        | true                   | hash(age,money,name,status)                   | {"strategy":"Upsert"}        |
        | 5                  | Corey          | 20        | Working at Store    | 800         | 2024-01-01 00:00:00          | 2999-12-31 23:59:59        | true                   | hash(age,money,name,status)                   | {"strategy":"Upsert"}        |
        """

        df_source_table = markdown_to_dataframe(spark_session, md_source_table)
        df_existing_target = markdown_to_dataframe(spark_session, md_existing_target)
        df_expected_result = markdown_to_dataframe(spark_session, md_expected_result)

        if request.config.getoption("--verbose-dataframes"):
            print("\n=== UPSERT - SOURCE DATAFRAME ===")
            df_source_table.show()
            print("\n=== UPSERT - EXISTING TARGET DATAFRAME ===")
            df_existing_target.show()
            print("\n=== UPSERT - EXPECTED RESULT DATAFRAME ===")
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
        | character_id (int) (key) | name (varchar) | age (int) | status (varchar)    | money (int) | location (varchar) | occupation (varchar) |
        |--------------------------|----------------|-----------|---------------------|-------------|------------------|---------------------|
        | 1                  | Ricky          | 32        | Out of Jail         | 150         | Trailer Park     | Get Rich Quick         |
        | 2                  | Julian         | 35        | Running Bar         | 5500        | Trailer Park     | Bar Owner           |
        | 4                  | Bubbles        | 34        | Cart Supervisor     | 1800        | Shed             | Cat Caretaker       |
        | 5                  | Corey          | 20        | Working at Store    | 800         | Convenience Store| Assistant           |
        """

        # Target has fewer columns than source (missing location, occupation)
        md_existing_target = """
        | character_id (int) (key) | name (varchar) | age (int) | status (varchar)    | money (int) | _META_valid_from (timestamp) | _META_valid_to (timestamp) | _META_active (boolean) | _META_row_hash (string) | _META_system_info (string) |
        |--------------------------|----------------|-----------|---------------------|-------------|------------------------------|----------------------------|------------------------|-------------------------|----------------------------|
        | 1                  | Ricky          | 31        | In Jail             | 50          | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,money,name,status)                   | {"strategy":"Upsert"}     |
        | 2                  | Julian         | 34        | Planning Schemes    | 3000        | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,money,name,status)                   | {"strategy":"Upsert"}     |
        | 3                  | Randy          | 36        | Ass. Supervisor     | 2500        | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,money,name,status)                   | {"strategy":"Upsert"}     |
        """

        # Expected result with auto_expand=True should include all columns
        md_expected_result_auto_expand = """
        | character_id (int) (key) | name (varchar) | age (int) | status (varchar)    | money (int) | location (varchar) | occupation (varchar) | _META_valid_from (timestamp) | _META_valid_to (timestamp) | _META_active (boolean) | _META_row_hash (string) | _META_system_info (string)    |
        |--------------------------|----------------|-----------|---------------------|-------------|------------------|---------------------|------------------------------|----------------------------|------------------------|-------------------------|-------------------------------|
        | 1                  | Ricky          | 32        | Out of Jail         | 150         | Trailer Park     | Get Rich Quick         | 2024-01-01 00:00:00          | 2999-12-31 23:59:59        | true                   | hash(age,location,money,name,occupation,status)                   | {"strategy":"Upsert"}        |
        | 2                  | Julian         | 35        | Running Bar         | 5500        | Trailer Park     | Bar Owner           | 2024-01-01 00:00:00          | 2999-12-31 23:59:59        | true                   | hash(age,location,money,name,occupation,status)                   | {"strategy":"Upsert"}        |
        | 3                  | Randy          | 36        | Ass. Supervisor     | 2500        | null             | null                | 2024-01-01 00:00:00          | 2999-12-31 23:59:59        | true                   | hash(age,location,money,name,occupation,status)                   | {"strategy":"Upsert"}        |
        | 4                  | Bubbles        | 34        | Cart Supervisor     | 1800        | Shed             | Cat Caretaker       | 2024-01-01 00:00:00          | 2999-12-31 23:59:59        | true                   | hash(age,location,money,name,occupation,status)                   | {"strategy":"Upsert"}        |
        | 5                  | Corey          | 20        | Working at Store    | 800         | Convenience Store| Assistant           | 2024-01-01 00:00:00          | 2999-12-31 23:59:59        | true                   | hash(age,location,money,name,occupation,status)                   | {"strategy":"Upsert"}        |
        """

        # Expected result with auto_expand=False should only include target columns
        md_expected_result_no_expand = """
        | character_id (int) (key) | name (varchar) | age (int) | status (varchar)    | money (int) | _META_valid_from (timestamp) | _META_valid_to (timestamp) | _META_active (boolean) | _META_row_hash (string) | _META_system_info (string)    |
        |--------------------------|----------------|-----------|---------------------|-------------|------------------------------|----------------------------|------------------------|-------------------------|-------------------------------|
        | 1                  | Ricky          | 32        | Out of Jail         | 150         | 2024-01-01 00:00:00          | 2999-12-31 23:59:59        | true                   | hash(age,money,name,status)                   | {"strategy":"Upsert"}        |
        | 2                  | Julian         | 35        | Running Bar         | 5500        | 2024-01-01 00:00:00          | 2999-12-31 23:59:59        | true                   | hash(age,money,name,status)                   | {"strategy":"Upsert"}        |
        | 3                  | Randy          | 36        | Ass. Supervisor     | 2500        | 2024-01-01 00:00:00          | 2999-12-31 23:59:59        | true                   | hash(age,money,name,status)                   | {"strategy":"Upsert"}        |
        | 4                  | Bubbles        | 34        | Cart Supervisor     | 1800        | 2024-01-01 00:00:00          | 2999-12-31 23:59:59        | true                   | hash(age,money,name,status)                   | {"strategy":"Upsert"}        |
        | 5                  | Corey          | 20        | Working at Store    | 800         | 2024-01-01 00:00:00          | 2999-12-31 23:59:59        | true                   | hash(age,money,name,status)                   | {"strategy":"Upsert"}        |
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
            print("\n=== UPSERT AUTO EXPAND - SOURCE DATAFRAME ===")
            df_source_table.show()
            print("\n=== UPSERT AUTO EXPAND - EXISTING TARGET DATAFRAME ===")
            df_existing_target.show()
            print("\n=== UPSERT AUTO EXPAND - EXPECTED RESULT (AUTO_EXPAND=TRUE) ===")
            df_expected_result_auto_expand.show()
            print("\n=== UPSERT AUTO EXPAND - EXPECTED RESULT (AUTO_EXPAND=FALSE) ===")
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
        | character_id (int) (key) | name (varchar) | age (int) | status (varchar)    |
        |--------------------------|----------------|-----------|---------------------|
        | 1                  | Ricky          | 32        | Out of Jail         |
        | 2                  | Julian         | 35        | Running Bar         |
        | 4                  | Bubbles        | 34        | Cart Supervisor     |
        | 5                  | Corey          | 20        | Working at Store    |
        """

        # Target has more columns than source (has money, location)
        md_existing_target = """
        | character_id (int) (key) | name (varchar) | age (int) | status (varchar)    | money (int) | location (varchar) | _META_valid_from (timestamp) | _META_valid_to (timestamp) | _META_active (boolean) | _META_row_hash (string) | _META_system_info (string) |
        |--------------------------|----------------|-----------|---------------------|-------------|------------------|------------------------------|----------------------------|------------------------|-------------------------|----------------------------|
        | 1                  | Ricky          | 31        | In Jail             | 50          | Jail             | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,location,money,name,status)                   | {"strategy":"Upsert"}     |
        | 2                  | Julian         | 34        | Planning Schemes    | 3000        | Trailer Park     | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,location,money,name,status)                   | {"strategy":"Upsert"}     |
        | 3                  | Randy          | 36        | Ass. Supervisor     | 2500        | Trailer Park     | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,location,money,name,status)                   | {"strategy":"Upsert"}     |
        """

        # Expected result with auto_shrink=True should only include source columns
        md_expected_result_auto_shrink = """
        | character_id (int) (key) | name (varchar) | age (int) | status (varchar)    | money (int) (dropped) | location (varchar) (dropped) | _META_valid_from (timestamp) | _META_valid_to (timestamp) | _META_active (boolean) | _META_row_hash (string)                      | _META_system_info (string)    |
        |--------------------------|----------------|-----------|---------------------|----------------------|------------------------------|------------------------------|----------------------------|------------------------|----------------------------------------------|-------------------------------|
        | 1                        | Ricky          | 32        | Out of Jail         | 50                   | Jail                         | 2024-01-01 00:00:00          | 2999-12-31 23:59:59        | true                   | hash(age,name,status)         | {"strategy":"Upsert"}         |
        | 2                        | Julian         | 35        | Running Bar         | 3000                 | Trailer Park                 | 2024-01-01 00:00:00          | 2999-12-31 23:59:59        | true                   | hash(age,name,status)         | {"strategy":"Upsert"}         |
        | 3                        | Randy          | 36        | Ass. Supervisor     | 2500                 | Trailer Park                 | 2024-01-01 00:00:00          | 2999-12-31 23:59:59        | true                   | hash(age,location,money,name,status)         | {"strategy":"Upsert"}         |
        | 4                        | Bubbles        | 34        | Cart Supervisor     | null                 | null                         | 2024-01-01 00:00:00          | 2999-12-31 23:59:59        | true                   | hash(age,name,status)                        | {"strategy":"Upsert"}         |
        | 5                        | Corey          | 20        | Working at Store    | null                 | null                         | 2024-01-01 00:00:00          | 2999-12-31 23:59:59        | true                   | hash(age,name,status)                        | {"strategy":"Upsert"}         |
        """

        # Expected result with auto_shrink=False should keep target columns
        md_expected_result_no_shrink = """
        | character_id (int) (key) | name (varchar) | age (int) | status (varchar)    | money (int) | location (varchar) | _META_valid_from (timestamp) | _META_valid_to (timestamp) | _META_active (boolean) | _META_row_hash (string) | _META_system_info (string)    |
        |--------------------------|----------------|-----------|---------------------|-------------|------------------|------------------------------|----------------------------|------------------------|-------------------------|-------------------------------|
        | 1                  | Ricky          | 32        | Out of Jail         | null        | null             | 2024-01-01 00:00:00          | 2999-12-31 23:59:59        | true                   | hash(age,location,money,name,status)                   | {"strategy":"Upsert"}        |
        | 2                  | Julian         | 35        | Running Bar         | null        | null             | 2024-01-01 00:00:00          | 2999-12-31 23:59:59        | true                   | hash(age,location,money,name,status)                   | {"strategy":"Upsert"}        |
        | 3                  | Randy          | 36        | Ass. Supervisor     | 2500        | Trailer Park     | 2024-01-01 00:00:00          | 2999-12-31 23:59:59        | true                   | hash(age,location,money,name,status)                   | {"strategy":"Upsert"}        |
        | 4                  | Bubbles        | 34        | Cart Supervisor     | null        | null             | 2024-01-01 00:00:00          | 2999-12-31 23:59:59        | true                   | hash(age,location,money,name,status)                   | {"strategy":"Upsert"}        |
        | 5                  | Corey          | 20        | Working at Store    | null        | null             | 2024-01-01 00:00:00          | 2999-12-31 23:59:59        | true                   | hash(age,location,money,name,status)                   | {"strategy":"Upsert"}        |
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
            print("\n=== UPSERT AUTO SHRINK - SOURCE DATAFRAME ===")
            df_source_table.show()
            print("\n=== UPSERT AUTO SHRINK - EXISTING TARGET DATAFRAME ===")
            df_existing_target.show()
            print("\n=== UPSERT AUTO SHRINK - EXPECTED RESULT (AUTO_SHRINK=TRUE) ===")
            df_expected_result_auto_shrink.show()
            print("\n=== UPSERT AUTO SHRINK - EXPECTED RESULT (AUTO_SHRINK=FALSE) ===")
            df_expected_result_no_shrink.show()

        return {
            "source": df_source_table,
            "existing_target": df_existing_target,
            "expected_auto_shrink": df_expected_result_auto_shrink,
            "expected_no_shrink": df_expected_result_no_shrink,
        }

    def test_basic_execution(self, basic_test_data, request):
        """Test Upsert strategy with matching schemas."""
        strategy = Upsert(key="character_id", auto_expand=True, auto_shrink=False)
        source_df = basic_test_data["source"]
        target_df = basic_test_data["existing_target"]
        expected_df = basic_test_data["expected"]

        result, final_target = execute_strategy_test_with_deterministic_metadata(
            strategy, source_df, target_df, source_df.sparkSession
        )

        assert_strategy_success(result)
        assert final_target.exists()

        # Verify upsert behavior: updates existing records and inserts new ones
        final_data = final_target.get_written_data()
        assert final_data is not None

        if request.config.getoption("--verbose-dataframes"):
            print("\n=== UPSERT BASIC TEST - FINAL OUTPUT DATAFRAME ===")
            final_data.show()
        assert_dataframes_equal(final_data, expected_df)

        # Verify strategy parameters
        assert strategy.key == ["character_id"]
        assert strategy.auto_expand is True
        assert strategy.auto_shrink is False

    def test_upsert_auto_expand_true(self, auto_expand_test_data):
        """Test Upsert strategy with auto_expand=True should add new columns from source."""
        strategy = Upsert(key="character_id", auto_expand=True, auto_shrink=False)
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

    def test_upsert_auto_expand_false(self, auto_expand_test_data):
        """Test Upsert strategy with auto_expand=False should not add new columns."""
        strategy = Upsert(key="character_id", auto_expand=False, auto_shrink=False)
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

    def test_upsert_auto_shrink_true(self, auto_shrink_test_data):
        """Test Upsert strategy with auto_shrink=True should remove columns not in source."""
        strategy = Upsert(key="character_id", auto_expand=False, auto_shrink=True)
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

    def test_upsert_auto_shrink_false(self, auto_shrink_test_data, request):
        """Test Upsert strategy with auto_shrink=False should keep target columns."""
        strategy = Upsert(key="character_id", auto_expand=False, auto_shrink=False)
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

        if request.config.getoption("--verbose-dataframes"):
            print("\n=== UPSERT AUTO SHRINK FALSE - FINAL OUTPUT DATAFRAME ===")
            final_data.show()

        assert_dataframes_equal(final_data, expected_df)

    def test_upsert_key_operations(self, basic_test_data):
        """Test that Upsert strategy handles key-based operations."""
        source_df = basic_test_data["source"]
        target_df = basic_test_data["existing_target"]

        strategy = Upsert(key="character_id", auto_expand=True, auto_shrink=False)
        result, final_target = execute_strategy_test_with_deterministic_metadata(
            strategy, source_df, target_df, source_df.sparkSession
        )

        assert_strategy_success(result)
        assert final_target.exists()

        # Verify key-based upsert operations work correctly
        final_data = final_target.get_written_data()
        assert final_data is not None
        expected_df = basic_test_data["expected"]
        assert_dataframes_equal(final_data, expected_df)

    def test_strategy_parameters(self):
        """Test Upsert strategy parameter initialization."""
        # Test single key as string
        strategy_single = Upsert(key="character_id")
        assert strategy_single.key == ["character_id"]
        assert strategy_single.auto_expand is True
        assert strategy_single.auto_shrink is False

        # Test multiple keys as list
        strategy_multi = Upsert(key=["character_id", "name"])
        assert strategy_multi.key == ["character_id", "name"]

        # Test custom parameters
        strategy_custom = Upsert(key="id", auto_expand=False, auto_shrink=True)
        assert strategy_custom.key == ["id"]
        assert strategy_custom.auto_expand is False
        assert strategy_custom.auto_shrink is True

    @pytest.mark.parametrize(
        "key",
        [
            "character_id",  # Single key as string
            ["character_id"],  # Single key as list
            ["character_id", "name"],  # Multiple keys
            ["character_id", "status"],  # Multiple keys with different types
        ],
    )
    def test_different_key_configurations(self, basic_test_data, key):
        """Test Upsert strategy with different key configurations."""
        strategy = Upsert(key=key, auto_expand=True, auto_shrink=False)
        source_df = basic_test_data["source"]
        target_df = basic_test_data["existing_target"]

        result, final_target = execute_strategy_test(
            strategy, source_df, target_df, source_df.sparkSession
        )

        assert_strategy_success(result)
        assert final_target.exists()

        # Verify key is stored as list regardless of input format
        expected_key = key if isinstance(key, list) else [key]
        assert strategy.key == expected_key

    def test_upsert_with_empty_target(self, basic_test_data):
        """Test Upsert strategy when target doesn't exist initially."""
        source_df = basic_test_data["source"]

        strategy = Upsert(key="character_id", auto_expand=True, auto_shrink=False)
        result, final_target = execute_strategy_test(
            strategy,
            source_df,
            None,
            source_df.sparkSession,  # None = no existing target
        )

        assert_strategy_success(result)
        # Verify target is created with source data when starting empty
        final_data = final_target.get_written_data()
        assert final_data is not None
        # When target is empty, result should be source data with metadata
        assert final_data.count() == source_df.count()
