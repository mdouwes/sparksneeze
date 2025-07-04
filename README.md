<div align="center">

<img src="assets/banner/banner-medium.webp" alt="SparkSneeze Banner" />

**A Python library for data warehouse transformations using Apache Spark with a strategy-based approach.**

[🌐 Documentation](https://sparksneeze.readthedocs.io/) • [💬 Discussions](https://github.com/mdouwes/sparksneeze/discussions)

<p align="center">
<a href="https://pypi.org/project/sparksneeze"><img alt="PyPI" src="https://img.shields.io/pypi/v/sparksneeze.svg?style=flat-square"></a>
<a href="https://pypi.org/project/sparksneeze"><img alt="PyPI - Python Version" src="https://img.shields.io/pypi/pyversions/sparksneeze?style=flat-square"></a>
<a href="https://github.com/mdouwes/sparksneeze/actions"><img alt="GitHub Workflow Status" src="https://img.shields.io/github/actions/workflow/status/mdouwes/sparksneeze/ci.yml?style=flat-square"></a>
<a href="https://codecov.io/gh/mdouwes/sparksneeze"><img alt="Codecov" src="https://img.shields.io/codecov/c/github/mdouwes/sparksneeze?style=flat-square"></a>
<a href="https://github.com/mdouwes/sparksneeze/blob/main/LICENSE"><img alt="GitHub" src="https://img.shields.io/github/license/mdouwes/sparksneeze?style=flat-square"></a>
</p>

</div>

---

## About

> *"Sneezingly fast data warehouse transformations! Bless you! 🤧"*

SparkSneeze provides a **strategy-based approach** to common data warehouse operations using Apache Spark. Whether you need to drop and recreate tables, append new data, perform upserts, or implement slowly changing dimensions, SparkSneeze handles the complexity while automatically enriching your data with standardized metadata and applies schema evolution.

**Key Features:**
- 🎯 **Five powerful strategies**: DropCreate, Truncate, Append, Upsert, and Historize
- 🔄 **Automatic schema evolution** with configurable expand/shrink options
- ⚡ **Spark-optimized** for high-performance data processing
- 🔧 **Highly configurable** metadata and processing options

It is still in early development, it is not recommended using it in any kind of production environment.

## Installation

Install using pip:

```bash
pip install sparksneeze
```

Or using uv:

```bash
uv add sparksneeze
```

For development with all optional dependencies:

```bash
uv add sparksneeze[dev]
```

## Usage

### Python Library

**sparksneeze** uses a strategy pattern to handle different data transformation approaches. The main entry point is the `sparksneeze()` factory function.

#### Basic Usage

```python
from sparksneeze import sparksneeze
from sparksneeze.strategy import DropCreate, Append, Upsert

# Create a DataFrame (or use existing one)
# df = spark.createDataFrame([...])

# DropCreate: Replace target completely with source data
result = sparksneeze(df, "my_delta_table", DropCreate()).run()
print(f"Success: {result.success}, Message: {result.message}")

# Append: Add source data to target
result = sparksneeze(df, "my_delta_table", Append()).run()

# Upsert: Insert new and update existing records by key
result = sparksneeze(df, "my_delta_table", Upsert(key="id")).run()
```

#### Advanced Usage with Custom Spark Session

```python
from pyspark.sql import SparkSession
from sparksneeze import sparksneeze
from sparksneeze.strategy import Truncate, Historize

# Use your existing Spark session
spark = SparkSession.builder.appName("MyApp").getOrCreate()

# Truncate: Clear target and load source data
strategy = Truncate(auto_expand=True, auto_shrink=False)
result = sparksneeze(df, "target_table", strategy).run(spark_session=spark)

# Historize: Track changes over time with validity periods
strategy = Historize(key=["user_id"], prefix="HIST_")
result = sparksneeze(df, "target_table", strategy).run(spark_session=spark)
```

#### Available Strategies

- **DropCreate**: Remove target and recreate with source schema
- **Truncate**: Clear target and load source data (with schema evolution)
- **Append**: Add source data to target (with schema evolution)
- **Upsert**: Insert/update based on keys (with schema evolution)
- **Historize**: Upsert with validity time tracking metadata

#### Automatic Metadata Enrichment

All strategies automatically add standardized metadata fields to track data lineage, validity, and changes:

```python
from sparksneeze import sparksneeze
from sparksneeze.strategy import DropCreate

# Automatic metadata added to every record
result = sparksneeze(df, "my_table", DropCreate()).run()

# Results in columns like:
# _META_valid_from    - Record validity start timestamp
# _META_valid_to      - Record validity end timestamp  
# _META_active        - Active record indicator (True/False)
# _META_row_hash      - Hash of data columns (excludes keys/metadata)
# _META_system_info   - JSON with strategy, version, timestamp info
```

#### Custom Metadata Configuration

```python
from sparksneeze.metadata import MetadataConfig
from sparksneeze.strategy import Upsert

# Customize metadata fields and behavior
config = MetadataConfig(
    prefix="_AUDIT",                    # Custom prefix instead of _META
    hash_columns=["name", "email"]      # Only hash specific columns
)

# Use with any strategy
strategy = Upsert(key="user_id", metadata_config=config)
result = sparksneeze(df, "users_table", strategy).run()

# Key columns (user_id) automatically excluded from hash
```

#### Schema Evolution

Most strategies support automatic schema evolution:

```python
from sparksneeze.strategy import Append

# Automatically add new columns from source
strategy = Append(auto_expand=True, auto_shrink=False)

# Also remove columns not in source
strategy = Append(auto_expand=True, auto_shrink=True)
```

### Command Line Interface

The CLI provides access to all strategies with their specific parameters.

#### Basic Commands

```bash
# Show help
sparksneeze --help

# Show version
sparksneeze --version

# Basic usage pattern
sparksneeze source_path target_path --strategy StrategyName [options]
```

#### Strategy Examples

```bash
# DropCreate: Replace target completely
sparksneeze /path/to/source.parquet my_table --strategy DropCreate

# Append with schema evolution
sparksneeze source.parquet target_table --strategy Append --auto_expand true

# Upsert by key
sparksneeze source.parquet target_table --strategy Upsert --key user_id

# Historize with multiple keys and custom prefix
sparksneeze source.parquet target_table --strategy Historize \
  --key user_id,version --prefix HIST_ --auto_expand true

# Enable verbose output
sparksneeze source.parquet target_table --strategy DropCreate --verbose
```

#### Available Strategy Options

- `--auto_expand true/false`: Add new columns from source (Truncate, Append, Upsert, Historize)
- `--auto_shrink true/false`: Remove columns not in source (Truncate, Append, Upsert, Historize)  
- `--key column_name`: Single key for Upsert/Historize
- `--key col1,col2`: Multiple keys for Upsert/Historize
- `--valid_from "YYYY-MM-DD"`: Start date for Historize validity
- `--valid_to "YYYY-MM-DD"`: End date for Historize validity
- `--prefix "PREFIX_"`: Metadata column prefix for Historize

## Development

### Setup

1. Clone the repository:
```bash
git clone <your-repo-url>
cd sparksneeze
```

2. Install development dependencies:
```bash
uv sync --extra dev
```

### Running in Development

#### CLI Development

```bash
# Run CLI directly
uv run sparksneeze --help

# Run with Python module syntax
uv run python -m sparksneeze.cli --help
```

#### Testing

Run the full test suite:

```bash
uv run pytest
```

Run tests with coverage:

```bash
uv run pytest --cov=sparksneeze --cov-report=html
```

Run specific test files:

```bash
uv run pytest tests/test_core.py
uv run pytest tests/test_cli.py
```

Run tests with verbose output:

```bash
uv run pytest -v
```

Mark and run specific test types:

```bash
# Run only fast tests (exclude slow ones)
uv run pytest -m "not slow"
```

#### Code Quality

Format code:

```bash
uv run black src tests
```

Lint code:

```bash
uv run ruff check src tests
```

### Documentation

Build documentation locally:

```bash
cd docs
uv run sphinx-build -b html . _build/html
```

Or using make:

```bash
cd docs
make html
```

View documentation:

```bash
# Open docs/_build/html/index.html in your browser
```

#### ReadTheDocs Setup

This project is configured for ReadTheDocs with:
- `.readthedocs.yaml` configuration file
- Sphinx documentation in `docs/` directory
- Auto-generated API documentation
- Support for both RST and Markdown files

To publish on ReadTheDocs:
1. Push your code to a Git repository
2. Connect your repository to ReadTheDocs
3. Documentation will be automatically built and deployed

### Building and Distribution

Build the package:

```bash
uv build
```

The built packages will be in the `dist/` directory.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## License

MIT License - see LICENSE file for details.