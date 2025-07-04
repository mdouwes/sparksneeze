#!/usr/bin/env python3
"""
Example 003: Parquet to Delta using DropCreate Strategy

The boys need to upgrade their sales tracking from Parquet to Delta for ACID transactions and time travel.
First run: uv run python examples/create_sales_parquet.py
Then run: uv run python examples/003_Example_DropCreate_Parquet_to_Delta.py
"""

import os
from sparksneeze import sparksneeze
from sparksneeze.strategy import DropCreate

source_parquet = "examples/data/sales.parquet"
target_delta = "examples/targets/003_Example_DropCreate.delta"

if not os.path.exists(source_parquet):
    print("❌ Parquet file not found! Run create_sales_parquet.py first.")
    exit(1)

result = sparksneeze(source_parquet, target_delta, strategy=DropCreate()).run()

if result.success:
    print("✅ SUCCESS! Sales data converted to Delta!")
    print(f"💸 Processed {result.data['rows_processed']} sales transactions")
    print("🚀 Now with ACID transactions and time travel!")
else:
    print(f"❌ FAILURE: {result.message}")