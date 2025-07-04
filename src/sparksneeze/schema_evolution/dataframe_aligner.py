"""DataFrame schema alignment utilities for schema evolution."""

from typing import TYPE_CHECKING, Set, Optional

if TYPE_CHECKING:
    from pyspark.sql import DataFrame
    from pyspark.sql.types import StructType


class DataFrameAligner:
    """Handles DataFrame schema alignment operations."""

    def __init__(self, metadata_fields: Optional[Set[str]] = None, logger=None):
        """Initialize DataFrame aligner.

        Args:
            metadata_fields: Set of metadata field names to exclude from data alignment
            logger: Logger instance for debug/info messages
        """
        self.metadata_fields = metadata_fields or set()
        self.logger = logger

    def align_source_with_target_schema(
        self,
        source_df: "DataFrame",
        target_schema: "StructType",
        auto_shrink: bool = False,
    ) -> "DataFrame":
        """Align source DataFrame schema with evolved target schema.

        Args:
            source_df: Source DataFrame to align
            target_schema: Target schema (including metadata columns)
            auto_shrink: Whether to drop extra columns from source

        Returns:
            DataFrame with schema aligned to target (excluding metadata columns)
        """
        from pyspark.sql.functions import lit, col
        from pyspark.sql.types import StructType

        # Remove metadata columns from target schema to get data-only schema
        target_data_fields = [
            field
            for field in target_schema.fields
            if field.name not in self.metadata_fields
        ]
        target_data_schema = StructType(target_data_fields)

        # Get current source columns
        source_cols = {field.name: field for field in source_df.schema.fields}
        target_cols = {field.name: field for field in target_data_schema.fields}

        # Start with source DataFrame
        aligned_df = source_df

        # Add missing columns (columns in target but not in source) with null values
        missing_in_source = set(target_cols.keys()) - set(source_cols.keys())
        for col_name in missing_in_source:
            target_field = target_cols[col_name]
            if self.logger:
                self.logger.debug(
                    f"Adding missing column '{col_name}' with type {target_field.dataType.simpleString()}"
                )
            aligned_df = aligned_df.withColumn(
                col_name, lit(None).cast(target_field.dataType)
            )

        # Remove extra columns (columns in source but not in target) if auto_shrink enabled
        if auto_shrink:
            extra_in_source = set(source_cols.keys()) - set(target_cols.keys())
            if extra_in_source:
                if self.logger:
                    self.logger.debug(
                        f"Dropping extra columns (auto_shrink=True): {list(extra_in_source)}"
                    )
                remaining_cols = [
                    c for c in aligned_df.columns if c not in extra_in_source
                ]
                aligned_df = aligned_df.select(remaining_cols)

        # Ensure column order and types match target schema exactly
        ordered_columns = []
        for field in target_data_schema.fields:
            col_name = field.name
            if col_name in aligned_df.columns:
                # Cast to target type if needed
                ordered_columns.append(
                    col(col_name).cast(field.dataType).alias(col_name)
                )
            else:
                # This shouldn't happen after adding missing columns, but be safe
                ordered_columns.append(lit(None).cast(field.dataType).alias(col_name))

        # Select columns in target order with correct types
        aligned_df = aligned_df.select(ordered_columns)

        if self.logger:
            self.logger.debug(
                f"Source DataFrame aligned with target schema - columns: {aligned_df.columns}"
            )
        return aligned_df

    def align_dataframe_exactly(
        self, df: "DataFrame", target_schema: "StructType"
    ) -> "DataFrame":
        """Align any DataFrame (including those with metadata) with target schema exactly.

        Args:
            df: DataFrame to align
            target_schema: Complete target schema (including metadata columns)

        Returns:
            DataFrame with schema exactly matching target schema (column order & types)
        """
        from pyspark.sql.functions import lit, col

        # Get current DataFrame columns
        df_cols = {field.name: field for field in df.schema.fields}

        # Build ordered column list matching target schema exactly
        ordered_columns = []
        for field in target_schema.fields:
            col_name = field.name
            target_type = field.dataType

            if col_name in df_cols:
                # Column exists in DataFrame - cast to target type and add
                ordered_columns.append(col(col_name).cast(target_type).alias(col_name))
            else:
                # Column missing in DataFrame - add with null value
                if self.logger:
                    self.logger.debug(
                        f"Adding missing column '{col_name}' with null value and type {target_type.simpleString()}"
                    )
                ordered_columns.append(lit(None).cast(target_type).alias(col_name))

        # Select columns in exact target order with exact target types
        aligned_df = df.select(ordered_columns)

        if self.logger:
            self.logger.debug(
                f"DataFrame fully aligned with target schema - columns: {aligned_df.columns}"
            )
        return aligned_df
