#!/usr/bin/env python3
"""
Example 001: CSV to Delta using DropCreate Strategy

Ricky needs to update the employee database with the latest roster.
Run from repo root: uv run python examples/001_Example_DropCreate_CSV_to_Delta.py
"""

from sparksneeze import sparksneeze
from sparksneeze.strategy import DropCreate
from sparksneeze.spark_utils import create_spark_session_with_delta

spark = create_spark_session_with_delta(app_name="TPB_CSV_to_Delta")

source_csv = "examples/data/employees.csv"
target_delta = "examples/targets/001_Example_DropCreate.delta"

result = sparksneeze(source_csv, target_delta, strategy=DropCreate()).run(spark)

if result.success:
    print("✅ SUCCESS! Employee database updated!")
    print(f"👥 Processed {result.data['rows_processed']} employee records")
else:
    print(f"❌ FAILURE: {result.message}")

spark.stop()