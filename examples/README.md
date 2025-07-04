# SparkSneeze Examples 

Welcome to the SparkSneeze examples! These examples use Trailer Park Boys themed data to demonstrate the clean, simple SparkSneeze API using the **simplified syntax** from the docs.

All examples follow the golden path pattern:
```python
result = sparksneeze(source, target, strategy=DropCreate()).run(spark)
```

All data is completely fictional and for educational/entertainment purposes.

## 🎭 About the Data

All examples use data from the fictional Sunnyvale Trailer Park and its residents:
- **Employees**: Ricky, Julian, Bubbles, and the gang with their various "business" roles
- **Products**: Hash, pepperoni sticks, shopping carts, liquor, and other trailer park essentials  
- **Customers**: Jacob, Trinity, and other park visitors and associates
- **Sales**: Transaction data from the boys' various entrepreneurial ventures

## 📁 Directory Structure

```
examples/
├── data/                                    # Sample data files
│   ├── employees.csv                        # Employee records
│   ├── customers.csv                        # Customer information
│   ├── products.json                        # Product catalog (nested JSON)
│   └── sales.parquet                        # Sales transactions
├── targets/                                 # Output directory for Delta tables
├── create_sales_parquet.py                  # Utility to regenerate sales data
├── 001_Example_DropCreate_CSV_to_Delta.py   # CSV → Delta conversion
├── 002_Example_DropCreate_JSON_to_Delta.py  # JSON → Delta conversion
├── 003_Example_DropCreate_Parquet_to_Delta.py # Parquet → Delta conversion
├── 004_Example_DropCreate_DataFrame_to_Delta.py # DataFrame → Delta
├── 005_Example_DropCreate_Replace_Existing.py # Schema evolution demo
└── README.md                                # This file
```

## 🚀 Getting Started

### Prerequisites

Make sure you have SparkSneeze installed and set up:

```bash
# From the repo root directory
uv sync --extra dev
```

### Running Examples

All examples should be run from the **repository root directory**, not from within the examples folder:

```bash
# Correct - from repo root
uv run python examples/001_Example_DropCreate_CSV_to_Delta.py

# Incorrect - don't run from examples/ directory
cd examples && python 001_Example_DropCreate_CSV_to_Delta.py  # ❌
```

## 📋 Examples Overview

### 001: CSV to Delta - Basic File Conversion
**File**: `001_Example_DropCreate_CSV_to_Delta.py`

Clean, simple example showing the SparkSneeze golden path.

```bash
uv run python examples/001_Example_DropCreate_CSV_to_Delta.py
```

```python
# Execute using simplified syntax
result = sparksneeze(source_csv, target_delta, strategy=DropCreate()).run(spark)
```

**Demonstrates**: CSV to Delta conversion with minimal code

---

### 002: JSON to Delta - Nested Data Handling
**File**: `002_Example_DropCreate_JSON_to_Delta.py`  

Handles complex nested JSON structures with ease.

```bash
uv run python examples/002_Example_DropCreate_JSON_to_Delta.py
```

**Demonstrates**: Automatic JSON schema inference and nested data preservation

---

### 003: Parquet to Delta - High Performance
**File**: `003_Example_DropCreate_Parquet_to_Delta.py`

Converts high-performance Parquet files to Delta format.

```bash
# First create the sales data
uv run python examples/create_sales_parquet.py

# Then run the conversion example
uv run python examples/003_Example_DropCreate_Parquet_to_Delta.py
```

**Demonstrates**: Parquet to Delta conversion for ACID compliance and time travel

---

### 004: DataFrame to Delta - In-Memory Processing  
**File**: `004_Example_DropCreate_DataFrame_to_Delta.py`

Works with Spark DataFrames created in memory.

```bash
uv run python examples/004_Example_DropCreate_DataFrame_to_Delta.py
```

```python
# Pass DataFrame directly to sparksneeze
result = sparksneeze(analysis_df, target_delta, strategy=DropCreate()).run(spark)
```

**Demonstrates**: DataFrame transformations and persisting processed data

---

### 005: Schema Evolution - Replace Existing
**File**: `005_Example_DropCreate_Replace_Existing.py`

Complete schema replacement with DropCreate.

```bash
uv run python examples/005_Example_DropCreate_Replace_Existing.py
```

**Demonstrates**: Destructive schema evolution - old data completely replaced

## 🔧 Utility Scripts

### create_sales_parquet.py
Generates realistic sales transaction data in Parquet format.

```bash
uv run python examples/create_sales_parquet.py
```

This script creates 500 random sales transactions with:
- Different success rates per salesperson
- Realistic product pricing with fluctuations
- Various payment methods (mostly cash, because trailer park)
- Humorous transaction notes

## 📊 Understanding DropCreate Strategy

The **DropCreate** strategy is demonstrated in all examples. Here's what it does:

### ✅ What DropCreate Does:
1. **Drops** the entire target table/data (if it exists)
2. **Creates** a new table with the source data and schema
3. **Replaces** everything - no merging, no compatibility checks
4. **Preserves** source data structure exactly

### ⚠️  When to Use DropCreate:
- ✅ Complete data refreshes
- ✅ Schema migrations where old data is not needed  
- ✅ Switching to completely different data structures
- ✅ Initial data loads
- ✅ Data lake medallion architecture (bronze → silver → gold)

### ❌ When NOT to Use DropCreate:
- ❌ When you need to preserve existing data
- ❌ When you need to merge or append data
- ❌ When you need incremental updates
- ❌ When downtime is not acceptable

## 🐛 Troubleshooting

### Common Issues:

**1. "Source file not found"**
- Make sure you're running from the repo root directory
- Check that data files exist in `examples/data/`

**2. "No module named 'sparksneeze'"**
- Run `uv sync --extra dev` from repo root
- Make sure you're using `uv run python` to execute scripts

**3. "Parquet file not found" (Example 003)**
- Run `uv run python examples/create_sales_parquet.py` first

**4. Spark startup warnings**
- These are normal and can be ignored (native Hadoop warnings, etc.)

### Automatic Delta Lake Configuration:

SparkSneeze automatically configures Delta Lake support! 🎉

- **Automatic version detection**: Detects your PySpark version and uses the matching Delta Lake version
- **No hardcoded versions**: Works with PySpark 3.4.x, 3.5.x, and 4.0.x automatically  
- **JAR package resolution**: Downloads Delta Lake JARs automatically when needed
- **Zero configuration**: Just run the examples - Delta support is built-in!

The examples use SparkSneeze's built-in Delta configuration, so you don't need to worry about:
- Adding JAR packages manually
- Configuring Spark extensions  
- Version compatibility issues
- Complex Spark session setup

### Getting Help:

```bash
# Check SparkSneeze CLI help
uv run sparksneeze --help

# Run tests to verify installation
uv run pytest tests/ -v
```

## 🎉 What's Next? 

After running these examples, you'll understand:
- How to use the DropCreate strategy
- Different data source types (CSV, JSON, Parquet, DataFrame)
- Schema handling and evolution
- When to use complete data replacement

**Ready for more advanced scenarios?** Check out the other SparkSneeze strategies:
- **Truncate**: Clear target and load source data (with schema evolution)
- **Append**: Add source data to target (with schema evolution)  
- **Upsert**: Insert/update based on keys
- **Historize**: Upsert with validity time tracking

## 🚨 Disclaimer

All data and scenarios in these examples are fictional. No actual trailer park residents were harmed in the creation of this educational content. Any resemblance to real persons, living or dead, or actual events is purely coincidental and probably pretty funny.

Remember: "The way she goes, boys. The way she goes." - Ray