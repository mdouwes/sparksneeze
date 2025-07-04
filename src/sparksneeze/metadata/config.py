"""Configuration classes for metadata handling."""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class MetadataConfig:
    """Configuration for metadata fields added to DataFrames.

    Attributes:
        prefix: Prefix for all metadata column names (default: "_META")
        valid_from_field: Name of the valid from timestamp field
        valid_to_field: Name of the valid to timestamp field
        active_field: Name of the active boolean field
        row_hash_field: Name of the row hash field
        system_info_field: Name of the system info JSON field
        default_valid_from: Default valid from timestamp (uses current time if None)
        default_valid_to: Default valid to timestamp (uses 2999-12-31 if None)
        hash_columns: Columns to include in hash (excludes metadata/key columns if None)
    """

    prefix: str = "_META"
    valid_from_field: str = "valid_from"
    valid_to_field: str = "valid_to"
    active_field: str = "active"
    row_hash_field: str = "row_hash"
    system_info_field: str = "system_info"
    default_valid_from: Optional[datetime] = None
    default_valid_to: Optional[datetime] = None
    hash_columns: Optional[List[str]] = None

    @property
    def prefixed_valid_from(self) -> str:
        """Get the prefixed valid from field name."""
        return f"{self.prefix}_{self.valid_from_field}"

    @property
    def prefixed_valid_to(self) -> str:
        """Get the prefixed valid to field name."""
        return f"{self.prefix}_{self.valid_to_field}"

    @property
    def prefixed_active(self) -> str:
        """Get the prefixed active field name."""
        return f"{self.prefix}_{self.active_field}"

    @property
    def prefixed_row_hash(self) -> str:
        """Get the prefixed row hash field name."""
        return f"{self.prefix}_{self.row_hash_field}"

    @property
    def prefixed_system_info(self) -> str:
        """Get the prefixed system info field name."""
        return f"{self.prefix}_{self.system_info_field}"

    @property
    def all_metadata_fields(self) -> List[str]:
        """Get all metadata field names with prefixes."""
        return [
            self.prefixed_valid_from,
            self.prefixed_valid_to,
            self.prefixed_active,
            self.prefixed_row_hash,
            self.prefixed_system_info,
        ]

    def get_effective_valid_from(self, override: Optional[datetime] = None) -> datetime:
        """Get the effective valid from datetime, using override or default."""
        if override is not None:
            return override
        if self.default_valid_from is not None:
            return self.default_valid_from
        return datetime.now()

    def get_effective_valid_to(self, override: Optional[datetime] = None) -> datetime:
        """Get the effective valid to datetime, using override or default."""
        if override is not None:
            return override
        if self.default_valid_to is not None:
            return self.default_valid_to
        return datetime(2999, 12, 31, 23, 59, 59)
