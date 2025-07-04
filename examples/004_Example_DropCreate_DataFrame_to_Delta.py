#!/usr/bin/env python3
"""
Example 004: DataFrame to Delta using DropCreate Strategy

Bubbles has done some customer analysis and wants to save the results.
This example shows how to work with in-memory DataFrames and persist them to Delta.
Run from repo root: uv run python examples/004_Example_DropCreate_DataFrame_to_Delta.py
"""

from sparksneeze import sparksneeze
from sparksneeze.strategy import DropCreate
from sparksneeze.spark_utils import create_spark_session_with_delta
from pyspark.sql.functions import col, when

spark = create_spark_session_with_delta(app_name="TPB_CustomerAnalysis")

customers_df = spark.read.option("header", "true").option("inferSchema", "true") \
    .csv("examples/data/customers.csv")

analysis_df = customers_df.select(
    col("customer_id"),
    col("name"),
    col("age"),
    col("lifetime_spend"),
    col("complaints"),
    when(col("lifetime_spend") > 1000, "High Value")
    .when(col("lifetime_spend") > 500, "Medium Value")
    .otherwise("Low Value").alias("customer_segment"),
    
    when(col("complaints") == 0, "Happy")
    .when(col("complaints") <= 2, "Satisfied") 
    .otherwise("Problematic").alias("satisfaction_level")
)

target_delta = "examples/targets/004_Example_DropCreate.delta"

result = sparksneeze(analysis_df, target_delta, strategy=DropCreate()).run(spark)

if result.success:
    print("✅ SUCCESS! Customer analysis saved!")
    print(f"👥 Processed {result.data['rows_processed']} customer records")
    print("🔍 Analysis includes segmentation and satisfaction levels!")
else:
    print(f"❌ FAILURE: {result.message}")

spark.stop()