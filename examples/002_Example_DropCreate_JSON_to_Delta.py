#!/usr/bin/env python3
"""
Example 002: JSON to Delta using DropCreate Strategy

Julian's product catalog is getting an upgrade from JSON to Delta.
Nested JSON structures are automatically preserved in Delta format.
Run from repo root: uv run python examples/002_Example_DropCreate_JSON_to_Delta.py
"""

from sparksneeze import sparksneeze
from sparksneeze.strategy import DropCreate

source_json = "examples/data/products.json"
target_delta = "examples/targets/002_Example_DropCreate.delta"

result = sparksneeze(source_json, target_delta, strategy=DropCreate()).run()

if result.success:
    print("✅ SUCCESS! Product catalog updated!")
    print(f"📦 Processed {result.data['rows_processed']} product records")
    print("🔍 Nested JSON structures preserved in Delta format!")
else:
    print(f"❌ FAILURE: {result.message}")