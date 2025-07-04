"""Strategy classes for sparksneeze operations."""

from .base import BaseStrategy, SparkSneezeResult
from .drop_create import DropCreate
from .truncate import Truncate
from .append import Append
from .upsert import Upsert
from .historize import Historize

__all__ = [
    "BaseStrategy",
    "SparkSneezeResult",
    "DropCreate",
    "Truncate",
    "Append",
    "Upsert",
    "Historize",
]
