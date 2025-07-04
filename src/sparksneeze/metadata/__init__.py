"""Metadata module for SparkSneeze.

This module provides automatic metadata enrichment for all SparkSneeze strategies,
adding tracking fields like row hashes, validity periods, and system information.
"""

from .config import MetadataConfig
from .applier import MetadataApplier

__all__ = ["MetadataConfig", "MetadataApplier"]
