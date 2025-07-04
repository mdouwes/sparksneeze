# Testing Guide for SparkSneeze

## Testing Approaches

SparkSneeze tests use two approaches for metadata generation, each suited for different scenarios.

### Deterministic Metadata (Recommended)

Use deterministic metadata for tests requiring exact DataFrame comparisons:

```python
from tests.test_utils import execute_strategy_test_with_deterministic_metadata, assert_dataframes_equal

def test_strategy_exact_comparison(self, test_data, spark_session):
    strategy = MyStrategy()
    result, target = execute_strategy_test_with_deterministic_metadata(
        strategy, source_df, existing_df, spark_session
    )
    
    final_data = target.get_written_data()
    assert_dataframes_equal(final_data, expected_df)
```

**Deterministic metadata provides:**
- Fixed timestamps: `2024-01-01 00:00:00` (valid_from) and `2999-12-31 23:59:59` (valid_to)
- Hash values based on row content (not sequential integers)
- Consistent system info: `{"strategy":"StrategyName"}`

### Regular Metadata

Use for performance tests or when exact values don't matter:

```python
from tests.test_utils import execute_strategy_test, assert_strategy_success

def test_strategy_basic(self, test_data, spark_session):
    strategy = MyStrategy()
    result, target = execute_strategy_test(strategy, source_df, existing_df, spark_session)
    
    assert_strategy_success(result)
    assert target.exists()
```

## Key Testing Utilities

- `execute_strategy_test_with_deterministic_metadata()` - For exact comparisons
- `execute_strategy_test()` - For basic execution tests  
- `assert_dataframes_equal()` - Compares DataFrames exactly
- `assert_strategy_success()` - Verifies strategy completed successfully

## Best Practices

- Use deterministic metadata for most tests requiring exact DataFrame comparisons
- Use regular metadata only when testing dynamic behavior or performance
- Hash values are generated from actual row content, not sequential integers