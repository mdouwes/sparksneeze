"""Simple, clean logging implementation for SparkSneeze."""

import json
import logging
import sys
import threading
from pathlib import Path
from typing import Any, Optional, Union


class SimpleFormatter(logging.Formatter):
    """Clean formatter with colored status prefixes."""

    # Terminal color codes
    COLORS = {
        "OK": "\033[92m",  # Green
        "ERROR": "\033[91m",  # Red
        "WARN": "\033[93m",  # Yellow
        "INFO": "\033[94m",  # Blue
        "DEBUG": "\033[90m",  # Gray
        "RESET": "\033[0m",  # Reset
    }

    def __init__(self, use_colors: bool = True):
        super().__init__()
        self.use_colors = use_colors and sys.stderr.isatty()

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colored prefix."""
        message = record.getMessage()

        # Determine prefix based on level and message content
        if hasattr(record, "is_success") and record.is_success:
            prefix = "OK"
        elif record.levelname == "ERROR":
            prefix = "ERROR"
        elif record.levelname == "WARNING":
            prefix = "WARN"
        elif record.levelname == "INFO":
            prefix = "INFO"
        elif record.levelname == "DEBUG":
            prefix = "DEBUG"
        else:
            prefix = record.levelname

        # Apply colors if enabled
        if self.use_colors and prefix in self.COLORS:
            colored_prefix = f"{self.COLORS[prefix]}[{prefix}]{self.COLORS['RESET']}"
        else:
            colored_prefix = f"[{prefix}]"

        return f"{colored_prefix} {message}"


class JSONFormatter(logging.Formatter):
    """JSON formatter for file logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, default=str, separators=(",", ":"))


class SparkSneezeLogger:
    """Simple logger wrapper with success() method."""

    def __init__(self, logger: logging.Logger):
        self._logger = logger

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message."""
        self._logger.debug(message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message."""
        self._logger.info(message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message."""
        self._logger.warning(message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message."""
        self._logger.error(message, **kwargs)

    def success(self, message: str, **kwargs: Any) -> None:
        """Log success message (formatted as [OK])."""
        # Create a custom log record with success flag
        record = self._logger.makeRecord(
            self._logger.name, logging.INFO, "", 0, message, (), None
        )
        record.is_success = True
        self._logger.handle(record)


class LoggerFactory:
    """Factory for creating and configuring loggers."""

    _configured = False
    _log_level = "WARNING"
    _file_path: Optional[Path] = None
    _lock = threading.Lock()

    @classmethod
    def configure(
        cls,
        level: str = "WARNING",
        file_path: Optional[Union[str, Path]] = None,
        quiet: bool = False,
    ) -> None:
        """Configure the logging system.

        Args:
            level: Logging level (DEBUG, INFO, WARNING, ERROR)
            file_path: Optional path for JSON file logging
            quiet: If True, only log errors to console
        """
        with cls._lock:
            if cls._configured:
                return

            cls._log_level = "ERROR" if quiet else level.upper()
            cls._file_path = Path(file_path) if file_path else None

            # Configure root logger
            root_logger = logging.getLogger()

            # Remove existing handlers
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)

            # Set root level to DEBUG so handlers can filter
            root_logger.setLevel(logging.DEBUG)

            # Console handler with colored formatter
            console_handler = logging.StreamHandler(sys.stderr)
            console_handler.setFormatter(SimpleFormatter())
            console_handler.setLevel(getattr(logging, cls._log_level))
            root_logger.addHandler(console_handler)

            # File handler with JSON formatter (if specified)
            if cls._file_path:
                cls._file_path.parent.mkdir(parents=True, exist_ok=True)
                file_handler = logging.FileHandler(cls._file_path)
                file_handler.setFormatter(JSONFormatter())
                file_handler.setLevel(logging.DEBUG)  # File gets all levels
                root_logger.addHandler(file_handler)

            cls._configured = True

    @classmethod
    def get_logger(cls, name: str) -> SparkSneezeLogger:
        """Get a logger instance.

        Args:
            name: Logger name (typically module name)

        Returns:
            SparkSneezeLogger: Configured logger instance
        """
        if not cls._configured:
            cls.configure()

        stdlib_logger = logging.getLogger(name)
        return SparkSneezeLogger(stdlib_logger)


def get_logger(name: str) -> SparkSneezeLogger:
    """Get a logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        SparkSneezeLogger: Configured logger instance
    """
    return LoggerFactory.get_logger(name)


def setup_logging(
    level: str = "WARNING",
    file_path: Optional[Union[str, Path]] = None,
    quiet: bool = False,
) -> None:
    """Setup logging configuration.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        file_path: Optional path for JSON file logging
        quiet: If True, only log errors to console
    """
    LoggerFactory.configure(level=level, file_path=file_path, quiet=quiet)
