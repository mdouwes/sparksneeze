"""Schema evolution utilities for sparksneeze strategies."""

from .type_compatibility import TypeCompatibilityChecker
from .dataframe_aligner import DataFrameAligner
from .evolution_metadata import SchemaEvolutionMetadata
from .evolution_handler import SchemaEvolutionHandler

__all__ = [
    "TypeCompatibilityChecker",
    "DataFrameAligner",
    "SchemaEvolutionMetadata",
    "SchemaEvolutionHandler",
]
