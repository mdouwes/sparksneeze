import logging


def pytest_addoption(parser):
    parser.addoption(
        "--verbose-dataframes",
        action="store_true",
        default=False,
        help="Show dataframes during test execution",
    )


def pytest_configure(config):
    """Configure logging to suppress py4j debug messages."""
    logging.getLogger("py4j.clientserver").setLevel(logging.WARNING)
