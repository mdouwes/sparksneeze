"""Simple, clean logging for SparkSneeze.

This module provides a streamlined logging system with:
- Clean console output with colored [OK]/[ERROR]/[WARN]/[INFO] prefixes
- Minimal log volume - only essential messages
- Optional JSON file logging

Usage:
    >>> from sparksneeze.logging import get_logger, setup_logging
    >>>
    >>> # Setup logging (typically done in CLI)
    >>> setup_logging(level="INFO")
    >>>
    >>> # Get logger for your module
    >>> logger = get_logger(__name__)
    >>> logger.info("Starting operation")
    >>> logger.success("Operation completed successfully")
    >>> logger.error("Operation failed")
"""

from .logger import get_logger, setup_logging, SparkSneezeLogger

__all__ = [
    "get_logger",
    "setup_logging",
    "SparkSneezeLogger",
]
