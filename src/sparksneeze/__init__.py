from .cli import main
from .core import sparksneeze, SparkSneezeRunner
from . import strategy
from . import metadata
from .data_sources import DataSource, DataFrameSource, PathSource, TableSource
from .data_targets import DataTarget
from .enums import WriteMode, DataFormat

try:
    from importlib.metadata import version

    __version__ = version("sparksneeze")
except ImportError:
    # Fallback for older Python versions or development installs
    __version__ = "0.1.2"
__all__ = [
    "main",
    "sparksneeze",
    "SparkSneezeRunner",
    "strategy",
    "metadata",
    "DataSource",
    "DataTarget",
    "DataFrameSource",
    "PathSource",
    "TableSource",
    "WriteMode",
    "DataFormat",
]
