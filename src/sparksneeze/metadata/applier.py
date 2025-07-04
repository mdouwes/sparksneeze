"""MetadataApplier class for adding metadata to DataFrames."""

from datetime import datetime
from typing import List, Optional
from pyspark.sql import DataFrame
from pyspark.sql.functions import lit, col
from pyspark.sql.types import TimestampType, BooleanType, StringType, StructType

from .config import MetadataConfig
from .utils import create_system_info_json, get_hash_columns, create_row_hash_column


class MetadataApplier:
    """Applies standardized metadata to DataFrames for all SparkSneeze strategies."""

    def __init__(self, config: Optional[MetadataConfig] = None):
        """Initialize the metadata applier.

        Args:
            config: Metadata configuration. Uses default if None.
        """
        self.config = config or MetadataConfig()

    def apply_metadata(
        self,
        df: DataFrame,
        strategy_name: str,
        key_columns: Optional[List[str]] = None,
        valid_from: Optional[datetime] = None,
        valid_to: Optional[datetime] = None,
        active: bool = True,
        additional_system_info: Optional[dict] = None,
        evolution_info: Optional[dict] = None,
    ) -> DataFrame:
        """Apply all metadata fields to a DataFrame.

        Args:
            df: Source DataFrame to add metadata to
            strategy_name: Name of the strategy being executed
            key_columns: Key columns to exclude from hashing
            valid_from: Valid from timestamp (uses config default if None)
            valid_to: Valid to timestamp (uses config default if None)
            active: Active flag value
            additional_system_info: Additional info for system metadata JSON
            evolution_info: Schema evolution information to include in system metadata

        Returns:
            DataFrame with all metadata fields added
        """
        # Get effective timestamps (single call for consistency across all rows)
        effective_valid_from = self.config.get_effective_valid_from(valid_from)
        effective_valid_to = self.config.get_effective_valid_to(valid_to)

        # Merge evolution info into additional system info
        combined_system_info = additional_system_info or {}
        if evolution_info:
            combined_system_info.update(evolution_info)

        # Create system info JSON
        system_info_json = create_system_info_json(
            strategy_name=strategy_name, additional_info=combined_system_info
        )

        # Add row hash first
        df_with_hash = self._add_row_hash(df, key_columns)

        # Add all metadata columns efficiently with select
        result_df = df_with_hash.select(
            "*",
            lit(effective_valid_from)
            .cast(TimestampType())
            .alias(self.config.prefixed_valid_from),
            lit(effective_valid_to)
            .cast(TimestampType())
            .alias(self.config.prefixed_valid_to),
            lit(active).cast(BooleanType()).alias(self.config.prefixed_active),
            col("_temp_hash").cast(StringType()).alias(self.config.prefixed_row_hash),
            lit(system_info_json)
            .cast(StringType())
            .alias(self.config.prefixed_system_info),
        ).drop(
            "_temp_hash"
        )  # Remove temporary hash column

        return result_df

    def _add_row_hash(
        self, df: DataFrame, key_columns: Optional[List[str]] = None
    ) -> DataFrame:
        """Add row hash to DataFrame.

        Args:
            df: DataFrame to add hash to
            key_columns: Key columns to exclude from hashing

        Returns:
            DataFrame with temporary hash column added
        """
        # Determine which columns to hash
        if self.config.hash_columns is not None:
            # Use explicitly configured columns
            hash_columns = self.config.hash_columns
        else:
            # Auto-determine: exclude metadata and key columns
            hash_columns = get_hash_columns(
                df=df,
                key_columns=key_columns,
                metadata_fields=self.config.all_metadata_fields,
            )

        return create_row_hash_column(df, hash_columns)

    def is_metadata_field(self, field_name: str) -> bool:
        """Check if a field name is a metadata field.

        Args:
            field_name: Field name to check

        Returns:
            True if field is a metadata field
        """
        return field_name in self.config.all_metadata_fields

    def get_non_metadata_columns(self, df: DataFrame) -> List[str]:
        """Get all non-metadata columns from a DataFrame.

        Args:
            df: DataFrame to analyze

        Returns:
            List of non-metadata column names
        """
        return [col for col in df.columns if not self.is_metadata_field(col)]

    def has_metadata(self, df: DataFrame) -> bool:
        """Check if DataFrame already has metadata fields.

        Args:
            df: DataFrame to check

        Returns:
            True if DataFrame has any metadata fields
        """
        df_columns = set(df.columns)
        metadata_fields = set(self.config.all_metadata_fields)
        return bool(df_columns.intersection(metadata_fields))

    def get_schema_with_metadata(self, schema: "StructType") -> "StructType":
        """Get schema with metadata fields added.

        Args:
            schema: Original schema to add metadata to

        Returns:
            StructType with metadata fields added
        """
        from pyspark.sql.types import (
            StructType,
            StructField,
            TimestampType,
            BooleanType,
            StringType,
        )

        # Start with original schema fields
        fields = list(schema.fields)

        # Add metadata fields (metadata fields are not nullable)
        fields.extend(
            [
                StructField(self.config.prefixed_valid_from, TimestampType(), False),
                StructField(self.config.prefixed_valid_to, TimestampType(), False),
                StructField(self.config.prefixed_active, BooleanType(), False),
                StructField(self.config.prefixed_row_hash, StringType(), False),
                StructField(self.config.prefixed_system_info, StringType(), False),
            ]
        )

        return StructType(fields)

    def has_metadata_schema(self, schema: "StructType") -> bool:
        """Check if schema already has metadata fields.

        Args:
            schema: Schema to check

        Returns:
            True if schema has any metadata fields
        """
        schema_columns = set(field.name for field in schema.fields)
        metadata_fields = set(self.config.all_metadata_fields)
        return bool(schema_columns.intersection(metadata_fields))
