import argparse
import sys
from typing import Optional
from datetime import datetime

from .core import sparksneeze
from .strategy import DropCreate, Truncate, Append, Upsert, Historize
from .logging import setup_logging, get_logger


def str_to_bool(value: str) -> bool:
    """Convert string to boolean."""
    if not isinstance(value, str):
        raise argparse.ArgumentTypeError(f"Expected string, got {type(value).__name__}")

    value_lower = value.lower().strip()
    if value_lower in ("true", "1", "yes", "on"):
        return True
    elif value_lower in ("false", "0", "no", "off"):
        return False
    else:
        raise argparse.ArgumentTypeError(f"Boolean value expected, got '{value}'")


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        prog="sparksneeze",
        description="Spark data processing with strategy-based operations",
    )

    # Import version from package
    from . import __version__

    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )

    # Logging options
    logging_group = parser.add_mutually_exclusive_group()
    logging_group.add_argument(
        "--quiet", "-q", action="store_true", help="Suppress all output except errors"
    )
    logging_group.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output (INFO level)",
    )
    logging_group.add_argument(
        "--debug", action="store_true", help="Enable debug output (DEBUG level)"
    )

    parser.add_argument(
        "--log-file", type=str, help="Path to log file for persistent logging"
    )

    # Required positional arguments
    parser.add_argument("source_entity", help="Source data entity (DataFrame or path)")

    parser.add_argument("target_entity", help="Target data entity (path)")

    # Required strategy argument
    parser.add_argument(
        "--strategy",
        required=True,
        choices=["DropCreate", "Truncate", "Append", "Upsert", "Historize"],
        help="Strategy to use for data processing",
    )

    # Strategy-specific optional arguments
    parser.add_argument(
        "--auto_expand",
        type=str_to_bool,
        help="Automatically add new columns to the target_entity (for Truncate, Append, Upsert, Historize)",
    )

    parser.add_argument(
        "--auto_shrink",
        type=str_to_bool,
        help="Automatically remove nonexistent columns from the target_entity (for Truncate, Append, Upsert, Historize)",
    )

    parser.add_argument(
        "--key",
        help="The key(s) that will be used for Upsert/Historize (comma-separated for multiple keys)",
    )

    parser.add_argument(
        "--valid_from",
        help="The datetime value for the start of record validity (for Historize)",
    )

    parser.add_argument(
        "--valid_to",
        help="The datetime value for the end of record validity (for Historize)",
    )

    parser.add_argument(
        "--prefix", help="The prefix to use for metadata columns (for Historize)"
    )

    return parser


def create_strategy_instance(args):
    """Create strategy instance based on parsed arguments."""
    strategy_name = args.strategy

    if strategy_name == "DropCreate":
        return DropCreate()

    elif strategy_name == "Truncate":
        kwargs = {}
        if args.auto_expand is not None:
            kwargs["auto_expand"] = args.auto_expand
        if args.auto_shrink is not None:
            kwargs["auto_shrink"] = args.auto_shrink
        return Truncate(**kwargs)

    elif strategy_name == "Append":
        kwargs = {}
        if args.auto_expand is not None:
            kwargs["auto_expand"] = args.auto_expand
        if args.auto_shrink is not None:
            kwargs["auto_shrink"] = args.auto_shrink
        return Append(**kwargs)

    elif strategy_name == "Upsert":
        if not args.key:
            raise ValueError(
                "Upsert strategy requires --key argument. "
                "Specify a single key (--key user_id) or multiple keys (--key user_id,version)"
            )

        keys = [k.strip() for k in args.key.split(",")]
        # Validate key format
        for key in keys:
            if not key or not key.replace("_", "").replace("-", "").isalnum():
                raise ValueError(
                    f"Invalid key format: '{key}'. Keys should be valid column names."
                )

        if len(keys) == 1:
            keys = keys[0]

        kwargs = {"key": keys}
        if args.auto_expand is not None:
            kwargs["auto_expand"] = args.auto_expand
        if args.auto_shrink is not None:
            kwargs["auto_shrink"] = args.auto_shrink
        return Upsert(key=keys, **{k: v for k, v in kwargs.items() if k != "key"})

    elif strategy_name == "Historize":
        if not args.key:
            raise ValueError(
                "Historize strategy requires --key argument. "
                "Specify a single key (--key user_id) or multiple keys (--key user_id,version)"
            )

        keys = [k.strip() for k in args.key.split(",")]
        # Validate key format
        for key in keys:
            if not key or not key.replace("_", "").replace("-", "").isalnum():
                raise ValueError(
                    f"Invalid key format: '{key}'. Keys should be valid column names."
                )

        if len(keys) == 1:
            keys = keys[0]

        kwargs = {"key": keys}
        if args.auto_expand is not None:
            kwargs["auto_expand"] = args.auto_expand
        if args.auto_shrink is not None:
            kwargs["auto_shrink"] = args.auto_shrink
        if args.valid_from:
            try:
                kwargs["valid_from"] = datetime.strptime(
                    args.valid_from, "%Y-%m-%d %H:%M:%S"
                )
            except ValueError:
                try:
                    kwargs["valid_from"] = datetime.strptime(
                        args.valid_from, "%Y-%m-%d"
                    )
                except ValueError:
                    raise ValueError(
                        f"Invalid valid_from format: '{args.valid_from}'. "
                        f"Expected formats: 'YYYY-MM-DD HH:MM:SS' or 'YYYY-MM-DD'. "
                        f"Example: '2024-01-01' or '2024-01-01 10:30:00'"
                    )
        if args.valid_to:
            try:
                kwargs["valid_to"] = datetime.strptime(
                    args.valid_to, "%Y-%m-%d %H:%M:%S"
                )
            except ValueError:
                try:
                    kwargs["valid_to"] = datetime.strptime(args.valid_to, "%Y-%m-%d")
                except ValueError:
                    raise ValueError(
                        f"Invalid valid_to format: '{args.valid_to}'. "
                        f"Expected formats: 'YYYY-MM-DD HH:MM:SS' or 'YYYY-MM-DD'. "
                        f"Example: '2024-12-31' or '2024-12-31 23:59:59'"
                    )

        # Handle metadata configuration with custom prefix
        if args.prefix:
            from .metadata import MetadataConfig

            metadata_config = MetadataConfig(prefix=args.prefix)
            kwargs["metadata_config"] = metadata_config

        return Historize(key=keys, **{k: v for k, v in kwargs.items() if k != "key"})

    else:
        raise ValueError(f"Unknown strategy: {strategy_name}")


def main(args: Optional[list[str]] = None) -> int:
    """Main entry point for the CLI."""
    parser = create_parser()

    try:
        parsed_args = parser.parse_args(args)
    except SystemExit as e:
        return e.code

    # Determine log level
    if parsed_args.debug:
        log_level = "DEBUG"
    elif parsed_args.verbose:
        log_level = "INFO"
    else:
        log_level = "WARNING"

    # Setup logging system
    setup_logging(
        level=log_level, file_path=parsed_args.log_file, quiet=parsed_args.quiet
    )

    # Progress tracking is now handled internally by strategies

    # Get logger for CLI
    logger = get_logger("sparksneeze.cli")

    try:
        # Log CLI startup info
        logger.info("SparkSneeze CLI started")

        # Create strategy instance
        strategy = create_strategy_instance(parsed_args)

        # Create and run sparksneeze runner
        runner = sparksneeze(
            parsed_args.source_entity, parsed_args.target_entity, strategy
        )

        # Strategy execution (logging handled by strategy itself)
        result = runner.run()

        if result and result.success:
            return 0
        else:
            logger.error(
                f"Strategy execution failed: {result.message if result else 'No result returned'}"
            )
            return 1

    except Exception as e:
        logger.error(f"CLI execution failed: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
