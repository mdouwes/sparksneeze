import pytest
from datetime import datetime
from tests.test_utils import (
    StrategyTestCase,
    execute_strategy_test,
    execute_strategy_test_with_deterministic_metadata,
    assert_strategy_success,
    assert_dataframes_equal,
    markdown_to_dataframe,
)
from sparksneeze.strategy import Historize


class TestStrategyHistorize(StrategyTestCase):
    """Test cases for Historize strategy."""

    @pytest.fixture
    def basic_test_data(self, spark_session, request):
        """Create basic test dataframes with matching schemas."""
        md_source_table = """
        | resident_id (int) (key) | name (varchar) | age (int) | trailer_number (int) | rent_status (varchar) |
        |-------------------------|----------------|-----------|---------------------|----------------------|
        | 1                 | Ricky          | 32        | 1                   | Behind               |
        | 2                 | Julian         | 35        | 2                   | Paid                 |
        | 3                 | Bubbles        | 34        | 0                   | Shed Owner           |
        | 4                 | Randy          | 37        | 5                   | Free Housing         |
        """

        md_existing_target = """
        | resident_id (int) (key) | name (varchar) | age (int) | trailer_number (int) | rent_status (varchar) | _META_valid_from (timestamp) | _META_valid_to (timestamp) | _META_active (boolean) | _META_row_hash (string) | _META_system_info (string) |
        |-------------------------|----------------|-----------|---------------------|----------------------|------------------------------|----------------------------|------------------------|-------------------------|----------------------------|
        | 1                 | Ricky          | 31        | 1                   | Paid                 | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,name,rent_status,trailer_number)                   | {"strategy":"Historize"}  |
        | 2                 | Julian         | 34        | 2                   | Paid                 | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,name,rent_status,trailer_number)                   | {"strategy":"Historize"}  |
        | 5                 | Mr Lahey       | 54        | 3                   | Supervisor           | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,name,rent_status,trailer_number)                   | {"strategy":"Historize"}  |
        """

        # Expected result would include historized records with _META_ columns
        # This is complex SCD2 logic that would be implemented in the actual strategy
        md_expected_result = """
        | resident_id (int) (key) | name (varchar) | age (int) | trailer_number (int) | rent_status (varchar) | _META_valid_from (timestamp) | _META_valid_to (timestamp) | _META_active (boolean) | _META_row_hash (string) | _META_system_info (string) |
        |-------------------------|----------------|-----------|---------------------|----------------------|------------------------------|----------------------------|------------------------|-------------------------|----------------------------|
        | 1                 | Ricky          | 31        | 1                   | Paid                 | 2024-01-01 00:00:00         | 2024-01-01 00:00:00       | false                  | hash(age,name,rent_status,trailer_number)                   | {"strategy":"Historize"}  |
        | 1                 | Ricky          | 32        | 1                   | Behind               | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,name,rent_status,trailer_number)                   | {"strategy":"Historize"}  |
        | 2                 | Julian         | 34        | 2                   | Paid                 | 2024-01-01 00:00:00         | 2024-01-01 00:00:00       | false                  | hash(age,name,rent_status,trailer_number)                   | {"strategy":"Historize"}  |
        | 2                 | Julian         | 35        | 2                   | Paid                 | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,name,rent_status,trailer_number)                   | {"strategy":"Historize"}  |
        | 3                 | Bubbles        | 34        | 0                   | Shed Owner           | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,name,rent_status,trailer_number)                   | {"strategy":"Historize"}  |
        | 4                 | Randy          | 37        | 5                   | Free Housing         | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,name,rent_status,trailer_number)                   | {"strategy":"Historize"}  |
        | 5                 | Mr Lahey       | 54        | 3                   | Supervisor           | 2024-01-01 00:00:00         | 2024-01-01 00:00:00       | false                  | hash(age,name,rent_status,trailer_number)                   | {"strategy":"Historize"}  |
        """

        df_source_table = markdown_to_dataframe(spark_session, md_source_table)
        df_existing_target = markdown_to_dataframe(spark_session, md_existing_target)
        df_expected_result = markdown_to_dataframe(spark_session, md_expected_result)

        if request.config.getoption("--verbose-dataframes"):
            print("\n=== HISTORIZE - SOURCE DATAFRAME ===")
            df_source_table.show()
            print("\n=== HISTORIZE - EXISTING TARGET DATAFRAME ===")
            df_existing_target.show()
            print("\n=== HISTORIZE - EXPECTED RESULT DATAFRAME ===")
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
        | resident_id (int) (key) | name (varchar) | age (int) | trailer_number (int) | rent_status (varchar) | phone (varchar) | emergency_contact (varchar) |
        |-------------------------|----------------|-----------|---------------------|----------------------|----------------|---------------------------|
        | 1                 | Ricky          | 32        | 1                   | Behind               | 555-0123       | Julian                    |
        | 2                 | Julian         | 35        | 2                   | Paid                 | 555-0456       | Ricky                     |
        | 3                 | Bubbles        | 34        | 0                   | Shed Owner           | 555-0789       | Ricky                     |
        | 4                 | Randy          | 37        | 5                   | Free Housing         | 555-9999       | Mr Lahey                  |
        """

        # Target has fewer columns than source (missing phone, emergency_contact)
        md_existing_target = """
        | resident_id (int) (key) | name (varchar) | age (int) | trailer_number (int) | rent_status (varchar) | _META_valid_from (timestamp) | _META_valid_to (timestamp) | _META_active (boolean) | _META_row_hash (string) | _META_system_info (string) |
        |-------------------------|----------------|-----------|---------------------|----------------------|------------------------------|----------------------------|------------------------|-------------------------|----------------------------|
        | 1                 | Ricky          | 31        | 1                   | Paid                 | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,name,rent_status,trailer_number)                   | {"strategy":"Historize"}  |
        | 2                 | Julian         | 34        | 2                   | Paid                 | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,name,rent_status,trailer_number)                   | {"strategy":"Historize"}  |
        | 5                 | Mr Lahey       | 54        | 3                   | Supervisor           | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,name,rent_status,trailer_number)                   | {"strategy":"Historize"}  |
        """

        # Expected result with auto_expand=True should include all columns + META columns
        md_expected_result_auto_expand = """
        | resident_id (int) (key) | name (varchar) | age (int) | trailer_number (int) | rent_status (varchar) | phone (varchar) | emergency_contact (varchar) | _META_valid_from (timestamp) | _META_valid_to (timestamp) | _META_active (boolean) | _META_row_hash (string) | _META_system_info (string) |
        |-------------------------|----------------|-----------|---------------------|----------------------|----------------|---------------------------|------------------------------|----------------------------|------------------------|-------------------------|----------------------------|
        | 1                 | Ricky          | 31        | 1                   | Paid                 | null           | null                      | 2024-01-01 00:00:00         | 2024-01-01 00:00:00       | false                  | hash(age,emergency_contact,name,phone,rent_status,trailer_number)                   | {"strategy":"Historize"}  |
        | 1                 | Ricky          | 32        | 1                   | Behind               | 555-0123       | Julian                    | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,emergency_contact,name,phone,rent_status,trailer_number)                   | {"strategy":"Historize"}  |
        | 2                 | Julian         | 34        | 2                   | Paid                 | null           | null                      | 2024-01-01 00:00:00         | 2024-01-01 00:00:00       | false                  | hash(age,emergency_contact,name,phone,rent_status,trailer_number)                   | {"strategy":"Historize"}  |
        | 2                 | Julian         | 35        | 2                   | Paid                 | 555-0456       | Ricky                     | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,emergency_contact,name,phone,rent_status,trailer_number)                   | {"strategy":"Historize"}  |
        | 3                 | Bubbles        | 34        | 0                   | Shed Owner           | 555-0789       | Ricky                     | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,emergency_contact,name,phone,rent_status,trailer_number)                   | {"strategy":"Historize"}  |
        | 4                 | Randy          | 37        | 5                   | Free Housing         | 555-9999       | Mr Lahey                  | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,emergency_contact,name,phone,rent_status,trailer_number)                   | {"strategy":"Historize"}  |
        | 5                 | Mr Lahey       | 54        | 3                   | Supervisor           | null           | null                      | 2024-01-01 00:00:00         | 2024-01-01 00:00:00       | false                  | hash(age,emergency_contact,name,phone,rent_status,trailer_number)                   | {"strategy":"Historize"}  |
        """

        # Expected result with auto_expand=False should only include target columns + META columns
        md_expected_result_no_expand = """
        | resident_id (int) (key) | name (varchar) | age (int) | trailer_number (int) | rent_status (varchar) | _META_valid_from (timestamp) | _META_valid_to (timestamp) | _META_active (boolean) | _META_row_hash (string) | _META_system_info (string) |
        |-------------------------|----------------|-----------|---------------------|----------------------|------------------------------|----------------------------|------------------------|-------------------------|----------------------------|
        | 1                 | Ricky          | 31        | 1                   | Paid                 | 2024-01-01 00:00:00         | 2024-01-01 00:00:00       | false                  | hash(age,name,rent_status,trailer_number)                   | {"strategy":"Historize"}  |
        | 1                 | Ricky          | 32        | 1                   | Behind               | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,name,rent_status,trailer_number)                   | {"strategy":"Historize"}  |
        | 2                 | Julian         | 34        | 2                   | Paid                 | 2024-01-01 00:00:00         | 2024-01-01 00:00:00       | false                  | hash(age,name,rent_status,trailer_number)                   | {"strategy":"Historize"}  |
        | 2                 | Julian         | 35        | 2                   | Paid                 | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,name,rent_status,trailer_number)                   | {"strategy":"Historize"}  |
        | 3                 | Bubbles        | 34        | 0                   | Shed Owner           | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,name,rent_status,trailer_number)                   | {"strategy":"Historize"}  |
        | 4                 | Randy          | 37        | 5                   | Free Housing         | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,name,rent_status,trailer_number)                   | {"strategy":"Historize"}  |
        | 5                 | Mr Lahey       | 54        | 3                   | Supervisor           | 2024-01-01 00:00:00         | 2024-01-01 00:00:00       | false                  | hash(age,name,rent_status,trailer_number)                   | {"strategy":"Historize"}  |
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
            print("\n=== HISTORIZE AUTO_EXPAND - SOURCE DATAFRAME ===")
            df_source_table.show()
            print("\n=== HISTORIZE AUTO_EXPAND - EXISTING TARGET DATAFRAME ===")
            df_existing_target.show()
            print(
                "\n=== HISTORIZE AUTO_EXPAND - EXPECTED RESULT AUTO_EXPAND DATAFRAME ==="
            )
            df_expected_result_auto_expand.show()
            print(
                "\n=== HISTORIZE AUTO_EXPAND - EXPECTED RESULT NO_EXPAND DATAFRAME ==="
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
        | resident_id (int) (key) | name (varchar) | age (int) | rent_status (varchar) |
        |-------------------------|----------------|-----------|----------------------|
        | 1                       | Ricky          | 32        | Behind               |
        | 2                       | Julian         | 35        | Paid                 |
        | 3                       | Bubbles        | 34        | Shed Owner           |
        | 4                       | Randy          | 37        | Free Housing         |
        """

        # Target has more columns than source (has trailer_number, deposit)
        md_existing_target = """
        | resident_id (int) (key) | name (varchar) | age (int) | trailer_number (int) | rent_status (varchar) | deposit (int) | _META_valid_from (timestamp) | _META_valid_to (timestamp) | _META_active (boolean) | _META_row_hash (string)                      | _META_system_info (string) |
        |-------------------------|----------------|-----------|----------------------|----------------------|---------------|------------------------------|----------------------------|------------------------|----------------------------------------------|---------------------------|
        | 1                       | Ricky          | 31        | 1                    | Paid                 | 500           | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,deposit,name,rent_status,trailer_number)    | {"strategy":"Historize"}  |
        | 2                       | Julian         | 34        | 2                    | Paid                 | 750           | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,deposit,name,rent_status,trailer_number)    | {"strategy":"Historize"}  |
        | 5                       | Mr Lahey       | 54        | 3                    | Supervisor           | 0             | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,deposit,name,rent_status,trailer_number)    | {"strategy":"Historize"}  |
        """

        # Expected result with auto_shrink=True should only include source columns + META columns
        md_expected_result_auto_shrink = """
        | resident_id (int) (key) | name (varchar) | age (int) | rent_status (varchar) | trailer_number (int) (dropped) | deposit (int) (dropped) | _META_valid_from (timestamp) | _META_valid_to (timestamp) | _META_active (boolean) | _META_row_hash (string)                              | _META_system_info (string) |
        |-------------------------|----------------|-----------|----------------------|---------------------------------|-------------------------|------------------------------|----------------------------|------------------------|------------------------------------------------------|---------------------------|
        | 1                       | Ricky          | 31        | Paid                 | 1                               | 500                     | 2024-01-01 00:00:00         | 2024-01-01 00:00:00       | false                  | hash(age,deposit,name,rent_status,trailer_number)   | {"strategy":"Historize"}  |
        | 1                       | Ricky          | 32        | Behind               | null                            | null                    | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,name,rent_status)                           | {"strategy":"Historize"}  |
        | 2                       | Julian         | 34        | Paid                 | 2                               | 750                     | 2024-01-01 00:00:00         | 2024-01-01 00:00:00       | false                  | hash(age,deposit,name,rent_status,trailer_number)   | {"strategy":"Historize"}  |
        | 2                       | Julian         | 35        | Paid                 | null                            | null                    | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,name,rent_status)                           | {"strategy":"Historize"}  |
        | 3                       | Bubbles        | 34        | Shed Owner           | null                            | null                    | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,name,rent_status)                           | {"strategy":"Historize"}  |
        | 4                       | Randy          | 37        | Free Housing         | null                            | null                    | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,name,rent_status)                           | {"strategy":"Historize"}  |
        | 5                       | Mr Lahey       | 54        | Supervisor           | 3                               | 0                       | 2024-01-01 00:00:00         | 2024-01-01 00:00:00       | false                  | hash(age,deposit,name,rent_status,trailer_number)   | {"strategy":"Historize"}  |
        """

        # Expected result with auto_shrink=False should keep target columns + META columns
        md_expected_result_no_shrink = """
        | resident_id (int) (key) | name (varchar) | age (int) | trailer_number (int) | rent_status (varchar) | deposit (int) | _META_valid_from (timestamp) | _META_valid_to (timestamp) | _META_active (boolean) | _META_row_hash (string)                              | _META_system_info (string) |
        |-------------------------|----------------|-----------|----------------------|----------------------|---------------|------------------------------|----------------------------|------------------------|------------------------------------------------------|---------------------------|
        | 1                       | Ricky          | 31        | 1                    | Paid                 | 500           | 2024-01-01 00:00:00         | 2024-01-01 00:00:00       | false                  | hash(age,deposit,name,rent_status,trailer_number)   | {"strategy":"Historize"}  |
        | 1                       | Ricky          | 32        | null                 | Behind               | null          | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,deposit,name,rent_status,trailer_number)   | {"strategy":"Historize"}  |
        | 2                       | Julian         | 34        | 2                    | Paid                 | 750           | 2024-01-01 00:00:00         | 2024-01-01 00:00:00       | false                  | hash(age,deposit,name,rent_status,trailer_number)   | {"strategy":"Historize"}  |
        | 2                       | Julian         | 35        | null                 | Paid                 | null          | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,deposit,name,rent_status,trailer_number)   | {"strategy":"Historize"}  |
        | 3                       | Bubbles        | 34        | null                 | Shed Owner           | null          | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,deposit,name,rent_status,trailer_number)   | {"strategy":"Historize"}  |
        | 4                       | Randy          | 37        | null                 | Free Housing         | null          | 2024-01-01 00:00:00         | 2999-12-31 23:59:59       | true                   | hash(age,deposit,name,rent_status,trailer_number)   | {"strategy":"Historize"}  |
        | 5                       | Mr Lahey       | 54        | 3                    | Supervisor           | 0             | 2024-01-01 00:00:00         | 2024-01-01 00:00:00       | false                  | hash(age,deposit,name,rent_status,trailer_number)   | {"strategy":"Historize"}  |
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
            print("\n=== HISTORIZE AUTO_SHRINK - SOURCE DATAFRAME ===")
            df_source_table.show()
            print("\n=== HISTORIZE AUTO_SHRINK - EXISTING TARGET DATAFRAME ===")
            df_existing_target.show()
            print(
                "\n=== HISTORIZE AUTO_SHRINK - EXPECTED RESULT AUTO_SHRINK DATAFRAME ==="
            )
            df_expected_result_auto_shrink.show()
            print(
                "\n=== HISTORIZE AUTO_SHRINK - EXPECTED RESULT NO_SHRINK DATAFRAME ==="
            )
            df_expected_result_no_shrink.show()

        return {
            "source": df_source_table,
            "existing_target": df_existing_target,
            "expected_auto_shrink": df_expected_result_auto_shrink,
            "expected_no_shrink": df_expected_result_no_shrink,
        }

    def test_basic_execution(self, basic_test_data, request):
        """Test Historize strategy with matching schemas."""
        strategy = Historize(key="resident_id", auto_expand=True, auto_shrink=False)
        source_df = basic_test_data["source"]
        target_df = basic_test_data["existing_target"]
        expected_df = basic_test_data["expected"]

        result, final_target = execute_strategy_test_with_deterministic_metadata(
            strategy, source_df, target_df, source_df.sparkSession
        )

        assert_strategy_success(result)
        assert final_target.exists()

        # Verify historize behavior: SCD2 with validity tracking
        final_data = final_target.get_written_data()
        assert final_data is not None

        if request.config.getoption("--verbose-dataframes"):
            print("\n=== HISTORIZE BASIC - ACTUAL RESULT DATAFRAME ===")
            final_data.show()
            print("\n=== HISTORIZE BASIC - EXPECTED RESULT DATAFRAME ===")
            expected_df.show()

        assert_dataframes_equal(final_data, expected_df)

        # Verify strategy parameters
        assert strategy.key == ["resident_id"]
        assert strategy.auto_expand is True
        assert strategy.auto_shrink is False
        assert strategy.metadata_applier.config.prefix == "_META"

    def test_historize_auto_expand_true(self, auto_expand_test_data, request):
        """Test Historize strategy with auto_expand=True should add new columns from source."""
        strategy = Historize(key="resident_id", auto_expand=True, auto_shrink=False)
        source_df = auto_expand_test_data["source"]
        target_df = auto_expand_test_data["existing_target"]

        result, final_target = execute_strategy_test_with_deterministic_metadata(
            strategy, source_df, target_df, source_df.sparkSession
        )

        assert_strategy_success(result)
        assert final_target.exists()
        assert strategy.auto_expand is True
        assert strategy.auto_shrink is False

        # Verify final result matches expected with expanded schema and SCD2 logic
        final_data = final_target.get_written_data()
        assert final_data is not None
        expected_df = auto_expand_test_data["expected_auto_expand"]

        if request.config.getoption("--verbose-dataframes"):
            print("\n=== HISTORIZE AUTO_EXPAND_TRUE - ACTUAL RESULT DATAFRAME ===")
            final_data.show()
            print("\n=== HISTORIZE AUTO_EXPAND_TRUE - EXPECTED RESULT DATAFRAME ===")
            expected_df.show()

        assert_dataframes_equal(final_data, expected_df)

    def test_historize_auto_expand_false(self, auto_expand_test_data, request):
        """Test Historize strategy with auto_expand=False should not add new columns."""
        strategy = Historize(key="resident_id", auto_expand=False, auto_shrink=False)
        source_df = auto_expand_test_data["source"]
        target_df = auto_expand_test_data["existing_target"]

        result, final_target = execute_strategy_test_with_deterministic_metadata(
            strategy, source_df, target_df, source_df.sparkSession
        )

        assert_strategy_success(result)
        assert final_target.exists()
        assert strategy.auto_expand is False
        assert strategy.auto_shrink is False

        # Verify final result matches target schema without expansion but with SCD2 logic
        final_data = final_target.get_written_data()
        assert final_data is not None
        expected_df = auto_expand_test_data["expected_no_expand"]

        if request.config.getoption("--verbose-dataframes"):
            print("\n=== HISTORIZE AUTO_EXPAND_FALSE - ACTUAL RESULT DATAFRAME ===")
            final_data.show()
            print("\n=== HISTORIZE AUTO_EXPAND_FALSE - EXPECTED RESULT DATAFRAME ===")
            expected_df.show()

        assert_dataframes_equal(final_data, expected_df)

    def test_historize_auto_shrink_true(self, auto_shrink_test_data, request):
        """Test Historize strategy with auto_shrink=True should remove columns not in source."""
        strategy = Historize(key="resident_id", auto_expand=False, auto_shrink=True)
        source_df = auto_shrink_test_data["source"]
        target_df = auto_shrink_test_data["existing_target"]

        result, final_target = execute_strategy_test_with_deterministic_metadata(
            strategy, source_df, target_df, source_df.sparkSession
        )

        assert_strategy_success(result)
        assert final_target.exists()
        assert strategy.auto_expand is False
        assert strategy.auto_shrink is True

        # Verify final result matches source schema with shrinking and SCD2 logic
        final_data = final_target.get_written_data()
        assert final_data is not None
        expected_df = auto_shrink_test_data["expected_auto_shrink"]

        if request.config.getoption("--verbose-dataframes"):
            print("\n=== HISTORIZE AUTO_SHRINK_TRUE - ACTUAL RESULT DATAFRAME ===")
            final_data.show()
            print("\n=== HISTORIZE AUTO_SHRINK_TRUE - EXPECTED RESULT DATAFRAME ===")
            expected_df.show()

        assert_dataframes_equal(final_data, expected_df)

    def test_historize_auto_shrink_false(self, auto_shrink_test_data, request):
        """Test Historize strategy with auto_shrink=False should keep target columns."""
        strategy = Historize(key="resident_id", auto_expand=False, auto_shrink=False)
        source_df = auto_shrink_test_data["source"]
        target_df = auto_shrink_test_data["existing_target"]

        result, final_target = execute_strategy_test_with_deterministic_metadata(
            strategy, source_df, target_df, source_df.sparkSession
        )

        assert_strategy_success(result)
        assert final_target.exists()
        assert strategy.auto_expand is False
        assert strategy.auto_shrink is False

        # Verify final result keeps all target columns without shrinking and SCD2 logic
        final_data = final_target.get_written_data()
        assert final_data is not None
        expected_df = auto_shrink_test_data["expected_no_shrink"]

        if request.config.getoption("--verbose-dataframes"):
            print("\n=== HISTORIZE AUTO_SHRINK_FALSE - ACTUAL RESULT DATAFRAME ===")
            final_data.show()
            print("\n=== HISTORIZE AUTO_SHRINK_FALSE - EXPECTED RESULT DATAFRAME ===")
            expected_df.show()

        assert_dataframes_equal(final_data, expected_df)

    def test_historize_key_operations(self, basic_test_data, request):
        """Test that Historize strategy handles key-based historization."""
        source_df = basic_test_data["source"]
        target_df = basic_test_data["existing_target"]

        strategy = Historize(key="resident_id", auto_expand=True, auto_shrink=False)
        result, final_target = execute_strategy_test_with_deterministic_metadata(
            strategy, source_df, target_df, source_df.sparkSession
        )

        assert_strategy_success(result)
        assert final_target.exists()

        # Verify key-based historization with SCD2 behavior
        final_data = final_target.get_written_data()
        assert final_data is not None
        expected_df = basic_test_data["expected"]

        if request.config.getoption("--verbose-dataframes"):
            print("\n=== HISTORIZE KEY_OPERATIONS - ACTUAL RESULT DATAFRAME ===")
            final_data.show()
            print("\n=== HISTORIZE KEY_OPERATIONS - EXPECTED RESULT DATAFRAME ===")
            expected_df.show()

        assert_dataframes_equal(final_data, expected_df)

    def test_strategy_parameters(self):
        """Test Historize strategy parameter initialization."""
        # Test single key as string with defaults
        strategy_single = Historize(key="resident_id")
        assert strategy_single.key == ["resident_id"]
        assert strategy_single.auto_expand is True
        assert strategy_single.auto_shrink is False
        assert strategy_single.metadata_applier.config.prefix == "_META"
        assert strategy_single.valid_from is None  # Default should be None
        assert strategy_single.valid_to is None  # Default should be None

        # Test multiple keys as list
        strategy_multi = Historize(key=["resident_id", "name"])
        assert strategy_multi.key == ["resident_id", "name"]

        # Test custom parameters
        from sparksneeze.metadata import MetadataConfig

        custom_valid_from = datetime(2024, 1, 1)
        custom_valid_to = datetime(2025, 12, 31)
        metadata_config = MetadataConfig(prefix="HIST_")
        strategy_custom = Historize(
            key="id",
            auto_expand=False,
            auto_shrink=True,
            valid_from=custom_valid_from,
            valid_to=custom_valid_to,
            metadata_config=metadata_config,
        )
        assert strategy_custom.key == ["id"]
        assert strategy_custom.auto_expand is False
        assert strategy_custom.auto_shrink is True
        assert strategy_custom.metadata_applier.config.prefix == "HIST_"
        assert strategy_custom.valid_from == custom_valid_from
        assert strategy_custom.valid_to == custom_valid_to

    @pytest.mark.parametrize(
        "key",
        [
            "resident_id",  # Single key as string
            ["resident_id"],  # Single key as list
            ["resident_id", "name"],  # Multiple keys
            ["resident_id", "trailer_number"],  # Multiple keys with different types
        ],
    )
    def test_different_key_configurations(self, basic_test_data, key, request):
        """Test Historize strategy with different key configurations."""
        strategy = Historize(key=key, auto_expand=True, auto_shrink=False)
        source_df = basic_test_data["source"]
        target_df = basic_test_data["existing_target"]

        result, final_target = execute_strategy_test_with_deterministic_metadata(
            strategy, source_df, target_df, source_df.sparkSession
        )

        assert_strategy_success(result)
        assert final_target.exists()

        # Verify key is stored as list regardless of input format
        expected_key = key if isinstance(key, list) else [key]
        assert strategy.key == expected_key

    @pytest.mark.parametrize(
        "prefix",
        [
            "META_",  # Default prefix
            "HIST_",  # Custom prefix
            "SCD2_",  # Another custom prefix
            "",  # Empty prefix
        ],
    )
    def test_different_prefix_configurations(self, basic_test_data, prefix, request):
        """Test Historize strategy with different prefix configurations."""
        from sparksneeze.metadata import MetadataConfig

        metadata_config = MetadataConfig(prefix=prefix)
        strategy = Historize(key="resident_id", metadata_config=metadata_config)
        source_df = basic_test_data["source"]
        target_df = basic_test_data["existing_target"]

        result, final_target = execute_strategy_test_with_deterministic_metadata(
            strategy, source_df, target_df, source_df.sparkSession
        )

        assert_strategy_success(result)
        assert final_target.exists()
        assert strategy.metadata_applier.config.prefix == prefix

    def test_datetime_parameter_handling(self):
        """Test Historize strategy datetime parameter handling."""
        # Test with None values (defaults)
        strategy_defaults = Historize(key="resident_id")
        assert strategy_defaults.valid_from is None  # Raw value should be None
        assert strategy_defaults.valid_to is None  # Raw value should be None

        # Test effective values are computed by metadata applier
        effective_from = (
            strategy_defaults.metadata_applier.config.get_effective_valid_from(
                strategy_defaults.valid_from
            )
        )
        effective_to = strategy_defaults.metadata_applier.config.get_effective_valid_to(
            strategy_defaults.valid_to
        )
        assert isinstance(effective_from, datetime)
        assert isinstance(effective_to, datetime)

        # Test with custom datetime values
        custom_from = datetime(2023, 6, 15, 10, 30, 0)
        custom_to = datetime(2024, 6, 15, 10, 30, 0)
        strategy_custom = Historize(
            key="resident_id", valid_from=custom_from, valid_to=custom_to
        )
        assert strategy_custom.valid_from == custom_from
        assert strategy_custom.valid_to == custom_to

    def test_historize_with_empty_target(self, basic_test_data, request):
        """Test Historize strategy when target doesn't exist initially."""
        source_df = basic_test_data["source"]

        strategy = Historize(key="resident_id", auto_expand=True, auto_shrink=False)
        result, final_target = execute_strategy_test(
            strategy,
            source_df,
            None,
            source_df.sparkSession,  # None = no existing target
        )

        assert_strategy_success(result)
        # Verify target is created with source data and proper META columns
        final_data = final_target.get_written_data()
        assert final_data is not None
        # When target is empty, result should be source data with SCD2 metadata
        if request.config.getoption("--verbose-dataframes"):
            print("\n=== HISTORIZE EMPTY_TARGET - ACTUAL RESULT DATAFRAME ===")
            final_data.show()
            print("\n=== HISTORIZE EMPTY_TARGET - SOURCE DATAFRAME ===")
            source_df.show()

        assert final_data.count() == source_df.count()
