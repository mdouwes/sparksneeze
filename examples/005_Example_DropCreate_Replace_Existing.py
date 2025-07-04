#!/usr/bin/env python3
"""
Example 005: DropCreate with Schema Evolution - Replacing Existing Data

The boys have completely overhauled their customer tracking system.
DropCreate doesn't care about schema compatibility - it replaces EVERYTHING.
This example creates an old table first, then completely replaces it with new schema.
Run from repo root: uv run python examples/005_Example_DropCreate_Replace_Existing.py

If you get an error, make sure the target_delta doesn't exist.
"""

from sparksneeze import sparksneeze
from sparksneeze.strategy import DropCreate
from sparksneeze.spark_utils import create_spark_session_with_delta

spark = create_spark_session_with_delta(app_name="TPB_SchemaEvolution")

target_delta = "examples/targets/005_Example_DropCreate.delta"

old_data = [
    (1, "Random Customer", "555-0001", 150.0, "East"),
    (2, "Another Person", "555-0002", 75.50, "West"),
    (3, "Some Guy", "555-0003", 200.25, "North"),
    (4, "Old Customer", "555-0004", 50.0, "South")
]

old_df = spark.createDataFrame(old_data, ["id", "customer_name", "phone", "total_purchases", "region"])
old_df.coalesce(1).write.mode("overwrite").format("delta").save(target_delta)

source_df = spark.read.csv("examples/data/customers.csv", header=True, inferSchema=True)

result = sparksneeze(source_df, target_delta, strategy=DropCreate()).run(spark)

if result.success:
    print("✅ SUCCESS! Complete schema evolution completed!")
    print(f"👥 Processed {result.data['rows_processed']} customer records")
else:
    print(f"❌ FAILURE: {result.message}")

spark.stop()