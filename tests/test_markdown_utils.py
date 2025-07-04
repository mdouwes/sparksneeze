"""Utilities for processing markdown tables in tests with hash function evaluation."""

from typing import List, Any, Tuple
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.types import (
    StructType,
    StructField,
    StringType,
    IntegerType,
    FloatType,
    BooleanType,
    TimestampType,
)


def parse_markdown_table(
    table_md: str,
) -> Tuple[List[str], List[StructField], List[str], List[List[str]]]:
    """Parse markdown table into components.

    Args:
        table_md: Markdown table string

    Returns:
        Tuple of (column_names, schema_fields, key_columns, data_rows)
    """
    lines = [line.strip() for line in table_md.strip().split("\n") if line.strip()]

    # Parse headers with types
    header_line = lines[0]
    header_cols = [col.strip() for col in header_line.split("|")[1:-1]]

    columns = []
    schema_fields = []
    key_columns = []  # Track key columns for hash calculation
    dropped_columns = []  # Track columns marked as (dropped)

    for col_spec in header_cols:
        if "(" in col_spec and ")" in col_spec:
            # Split by parentheses to get name and all markers
            parts = col_spec.split("(")
            name = parts[0].strip()

            # Extract type from first parentheses group
            type_str = parts[1].split(")")[0].strip().lower()

            # Check for special markers in any parentheses group
            is_dropped = False
            for part in parts[1:]:
                if "key" in part.lower():
                    key_columns.append(name)
                if "dropped" in part.lower():
                    is_dropped = True
                    dropped_columns.append(name)

            if type_str in ["int", "integer"]:
                spark_type = IntegerType()
            elif type_str in ["float", "double"]:
                spark_type = FloatType()
            elif type_str in ["bool", "boolean"]:
                spark_type = BooleanType()
            elif type_str == "timestamp":
                spark_type = TimestampType()
            else:  # varchar, string, etc.
                spark_type = StringType()

            # Determine nullable - metadata columns are non-nullable by default
            nullable = True
            if name.startswith("_META"):
                nullable = False

            columns.append(name)
            # Only add to schema if not dropped
            if not is_dropped:
                schema_fields.append(StructField(name, spark_type, nullable))
        else:
            columns.append(col_spec)
            schema_fields.append(StructField(col_spec, StringType()))

    # Parse data rows
    data_rows = []
    for line in lines[2:]:  # Skip header and separator
        row_data = [col.strip() for col in line.split("|")[1:-1]]
        data_rows.append(row_data)

    return columns, schema_fields, key_columns, data_rows


def cast_values(row_data: List[str], schema_fields: List[StructField]) -> List[Any]:
    """Cast string values to appropriate types based on schema.

    Args:
        row_data: List of string values from markdown table
        schema_fields: Schema field definitions

    Returns:
        List of properly typed values
    """
    converted_row = []
    for value, field in zip(row_data, schema_fields):
        # Handle null values
        if value.lower() == "null":
            converted_row.append(None)
        elif isinstance(field.dataType, IntegerType):
            converted_row.append(int(value))
        elif isinstance(field.dataType, FloatType):
            converted_row.append(float(value))
        elif isinstance(field.dataType, BooleanType):
            converted_row.append(value.lower() in ["true", "1", "yes"])
        elif isinstance(field.dataType, TimestampType):
            from datetime import datetime

            # Parse timestamp strings like "2024-01-01 00:00:00"
            converted_row.append(datetime.strptime(value, "%Y-%m-%d %H:%M:%S"))
        else:
            converted_row.append(value)

    return converted_row


def evaluate_hash_functions(
    spark: SparkSession,
    row_data: List[str],
    columns: List[str],
    key_columns: List[str],
    schema_fields: List[StructField],
) -> List[str]:
    """Evaluate hash() function expressions in row data.

    Args:
        spark: Spark session
        row_data: List of string values, may contain hash() expressions
        columns: Column names
        key_columns: Key column names to exclude from hashing
        schema_fields: Schema field definitions

    Returns:
        List of evaluated values with hash functions computed
    """
    evaluated_row = []

    for i, value in enumerate(row_data):
        # Check if this is a hash function expression
        if value.startswith("hash(") and value.endswith(")"):
            # Extract column names from hash(col1,col2,col3)
            hash_cols_str = value[5:-1]  # Remove 'hash(' and ')'
            hash_col_names = [c.strip() for c in hash_cols_str.split(",")]

            # Build the hash input using only the specified columns
            # Get the data for the specified hash columns from this row
            hash_values = []
            for hash_col in hash_col_names:
                if hash_col in columns:
                    col_index = columns.index(hash_col)
                    col_value = row_data[col_index]

                    # Get the field type for proper casting
                    field = next((f for f in schema_fields if f.name == hash_col), None)
                    if field:
                        # Cast the value properly
                        if col_value.lower() == "null":
                            hash_values.append(None)
                        elif isinstance(field.dataType, IntegerType):
                            hash_values.append(str(int(col_value)))
                        elif isinstance(field.dataType, FloatType):
                            hash_values.append(str(float(col_value)))
                        elif isinstance(field.dataType, BooleanType):
                            hash_values.append(
                                str(col_value.lower() in ["true", "1", "yes"])
                            )
                        elif isinstance(field.dataType, TimestampType):
                            hash_values.append(col_value)  # Keep as string for hash
                        else:
                            hash_values.append(col_value)
                    else:
                        hash_values.append(col_value)

            # Create a hash using the same logic as production
            # Use concat_ws behavior: exclude NULL values entirely (same as Spark's concat_ws)
            non_null_values = [str(v) for v in hash_values if v is not None]
            hash_input = "|".join(non_null_values)

            # Use Spark to compute the hash
            hash_df = spark.sql(f"SELECT xxhash64('{hash_input}') as hash_value")
            hash_value = hash_df.collect()[0][0]

            evaluated_row.append(str(hash_value))
        else:
            evaluated_row.append(value)

    return evaluated_row


def markdown_to_dataframe(
    spark: SparkSession, table_md: str, metadata_columns_non_nullable: bool = True
) -> DataFrame:
    """Convert markdown table to Spark DataFrame with hash function evaluation.

    Args:
        spark: Spark session
        table_md: Markdown table string
        metadata_columns_non_nullable: Whether metadata columns should be non-nullable

    Returns:
        Spark DataFrame with evaluated hash functions (dropped columns excluded from schema)
    """
    # Parse with support for dropped columns
    lines = [line.strip() for line in table_md.strip().split("\n") if line.strip()]
    header_line = lines[0]
    header_cols = [col.strip() for col in header_line.split("|")[1:-1]]

    all_columns = []
    schema_fields = []
    key_columns = []
    dropped_columns = []

    # Parse headers with dropped column detection
    for col_spec in header_cols:
        if "(" in col_spec and ")" in col_spec:
            parts = col_spec.split("(")
            name = parts[0].strip()
            type_str = parts[1].split(")")[0].strip().lower()

            is_dropped = False
            for part in parts[1:]:
                if "key" in part.lower():
                    key_columns.append(name)
                if "dropped" in part.lower():
                    is_dropped = True
                    dropped_columns.append(name)

            if type_str in ["int", "integer"]:
                spark_type = IntegerType()
            elif type_str in ["float", "double"]:
                spark_type = FloatType()
            elif type_str in ["bool", "boolean"]:
                spark_type = BooleanType()
            elif type_str == "timestamp":
                spark_type = TimestampType()
            else:
                spark_type = StringType()

            nullable = True
            if name.startswith("_META"):
                nullable = False

            all_columns.append(name)
            # Only add to schema if not dropped
            if not is_dropped:
                schema_fields.append(StructField(name, spark_type, nullable))
        else:
            all_columns.append(col_spec)
            schema_fields.append(StructField(col_spec, StringType()))

    # Parse data rows
    data_rows = []
    for line in lines[2:]:
        row_data = [col.strip() for col in line.split("|")[1:-1]]
        data_rows.append(row_data)

    # Process each row, evaluating hash functions
    processed_rows = []
    for row_data in data_rows:
        # Evaluate hash functions using ALL columns (including dropped ones)
        evaluated_row = evaluate_hash_functions(
            spark,
            row_data,
            all_columns,
            key_columns,
            [StructField(name, StringType(), True) for name in all_columns],
        )

        # Filter out dropped columns from row data
        filtered_row = []
        for i, col_name in enumerate(all_columns):
            if col_name not in dropped_columns:
                # Cast value to proper type
                value = evaluated_row[i]
                field = next((f for f in schema_fields if f.name == col_name), None)
                if field and value.lower() != "null":
                    if isinstance(field.dataType, IntegerType):
                        value = int(value)
                    elif isinstance(field.dataType, FloatType):
                        value = float(value)
                    elif isinstance(field.dataType, BooleanType):
                        value = value.lower() in ["true", "1", "yes"]
                    elif isinstance(field.dataType, TimestampType):
                        from datetime import datetime

                        value = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
                elif value.lower() == "null":
                    value = None
                filtered_row.append(value)

        processed_rows.append(tuple(filtered_row))

    # Create DataFrame with filtered schema (no dropped columns)
    schema = StructType(schema_fields)
    df = spark.createDataFrame(processed_rows, schema)

    # TEST-ONLY METADATA: Dynamically attach key column information to DataFrame.
    #
    # IMPORTANT: _key_columns is NOT a real attribute of pyspark.sql.DataFrame.
    # This is runtime monkey-patching used exclusively in test utilities to pass
    # key column metadata to downstream test functions without changing signatures.
    #
    # Usage: test_utils.py checks hasattr(df, '_key_columns') to detect this
    # metadata and enable deterministic hash generation during testing scenarios.
    # This ensures consistent test behavior across different test runs.
    #
    # Production code should never rely on this attribute.
    if key_columns:
        df._key_columns = key_columns  # type: ignore[attr-defined]

    return df
