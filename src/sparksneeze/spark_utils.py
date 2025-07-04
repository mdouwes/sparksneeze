"""Spark session utilities for automatic Delta Lake configuration."""

import os
import pyspark
from pyspark.sql import SparkSession
from typing import Optional, Dict


def get_delta_spark_package() -> str:
    """Get the appropriate delta-spark package for the current PySpark version.

    Returns:
        str: Maven coordinates for delta-spark package

    Raises:
        ValueError: If PySpark version is not supported
    """
    pyspark_version = pyspark.__version__

    # Map PySpark versions to compatible Delta Lake versions
    version_map = {
        "4.0.0": "io.delta:delta-spark_2.13:4.0.0",
        "3.5.3": "io.delta:delta-spark_2.13:3.2.1",
        "3.5.2": "io.delta:delta-spark_2.13:3.2.1",
        "3.5.1": "io.delta:delta-spark_2.13:3.2.1",
        "3.5.0": "io.delta:delta-spark_2.13:3.2.0",
        "3.4.3": "io.delta:delta-spark_2.13:3.1.0",
        "3.4.2": "io.delta:delta-spark_2.13:3.1.0",
        "3.4.1": "io.delta:delta-spark_2.13:3.1.0",
        "3.4.0": "io.delta:delta-spark_2.13:3.0.0",
    }

    if pyspark_version in version_map:
        return version_map[pyspark_version]

    # For newer versions, try the latest known mapping
    major_minor = ".".join(pyspark_version.split(".")[:2])
    if major_minor == "4.0":
        return "io.delta:delta-spark_2.13:4.0.0"
    elif major_minor == "3.5":
        return "io.delta:delta-spark_2.13:3.2.1"
    elif major_minor == "3.4":
        return "io.delta:delta-spark_2.13:3.1.0"

    raise ValueError(
        f"Unsupported PySpark version: {pyspark_version}. "
        f"Supported versions: {', '.join(version_map.keys())}"
    )


def create_spark_session_with_delta(
    app_name: str = "SparkSneeze",
    master: Optional[str] = None,
    additional_configs: Optional[Dict[str, str]] = None,
) -> SparkSession:
    """Create a Spark session with Delta Lake support automatically configured.

    Args:
        app_name: Spark application name
        master: Spark master URL (defaults to SPARK_MASTER env var or local[*])
        additional_configs: Additional Spark configurations

    Returns:
        SparkSession: Configured Spark session with Delta support

    Raises:
        ValueError: If PySpark version is not supported
    """
    # Set master from environment variable or default
    if master is None:
        master = os.getenv("SPARK_MASTER", "local[*]")

    delta_package = get_delta_spark_package()

    builder = (
        SparkSession.builder.appName(app_name)
        .master(master)
        .config("spark.jars.packages", delta_package)
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config(
            "spark.sql.catalog.spark_catalog",
            "org.apache.spark.sql.delta.catalog.DeltaCatalog",
        )
    )

    # Add any additional configurations
    if additional_configs:
        for key, value in additional_configs.items():
            builder = builder.config(key, value)

    return builder.getOrCreate()
