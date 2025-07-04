"""Main schema evolution handler orchestrating all schema evolution operations."""

from typing import TYPE_CHECKING, Optional, Set, Dict, Any, List

if TYPE_CHECKING:
    from pyspark.sql import DataFrame
    from pyspark.sql.types import StructType, StructField
    from ..data_targets import DataTarget

from .type_compatibility import TypeCompatibilityChecker
from .dataframe_aligner import DataFrameAligner
from .evolution_metadata import SchemaEvolutionMetadata


class SchemaEvolutionHandler:
    """Main orchestrator for schema evolution operations."""

    def __init__(
        self,
        auto_expand: bool = True,
        auto_shrink: bool = False,
        metadata_fields: Optional[Set[str]] = None,
        logger=None,
    ):
        """Initialize schema evolution handler.

        Args:
            auto_expand: Whether to automatically add new columns to target
            auto_shrink: Whether to automatically remove columns from target
            metadata_fields: Set of metadata field names to handle specially
            logger: Logger instance for debug/info messages
        """
        self.auto_expand = auto_expand
        self.auto_shrink = auto_shrink
        self.metadata_fields = metadata_fields or set()
        self.logger = logger

        # Initialize component classes
        self.type_checker = TypeCompatibilityChecker(logger=logger)
        self.aligner = DataFrameAligner(metadata_fields=metadata_fields, logger=logger)
        self.metadata_tracker = SchemaEvolutionMetadata(logger=logger)

    def evolve_schema(
        self, source_df: "DataFrame", target: "DataTarget"
    ) -> tuple["DataFrame", Dict[str, Any]]:
        """Perform complete schema evolution process.

        Args:
            source_df: Source DataFrame
            target: Target to evolve

        Returns:
            Tuple of (evolved_source_df, evolution_metadata)
        """
        # Handle target existence - create if needed
        if not target.exists():
            if self.logger:
                self.logger.info(
                    "Target doesn't exist, will be created with source schema + metadata"
                )
            # Return source as-is since target will be created with proper schema
            return source_df, {"schema_evolved": False}

        # Get target schema for comparison
        target_schema = target.get_schema()
        if target_schema is None:
            raise ValueError("Could not get target schema")

        # Remove metadata columns from target schema for comparison
        target_data_schema_fields = [
            field
            for field in target_schema.fields
            if field.name not in self.metadata_fields
        ]

        evolved_df = source_df
        evolution_info = {"schema_evolved": False}

        if target_data_schema_fields:
            from pyspark.sql.types import StructType

            target_data_schema = StructType(target_data_schema_fields)

            # Check type compatibility
            compatibility = self.type_checker.check_type_compatibility(
                source_df.schema, target_data_schema
            )

            # Perform source evolution
            if compatibility["source_evolution_needed"]:
                evolved_df = self.type_checker.evolve_source_types(
                    evolved_df, compatibility["source_evolution_needed"]
                )

            # Perform target evolution
            if compatibility["target_evolution_needed"]:
                self.type_checker.evolve_target_types(
                    target, compatibility["target_evolution_needed"]
                )

            # Handle incompatible types
            if compatibility["incompatible_columns"]:
                evolved_df = self.type_checker.resolve_type_conflicts(
                    evolved_df, target, compatibility["incompatible_columns"]
                )

            # Create evolution metadata
            evolution_info = self.metadata_tracker.create_evolution_metadata(
                compatibility
            )

        # Handle schema expansion/shrinkage
        if self.auto_expand:
            self.add_missing_columns(target, evolved_df.schema)

        if self.auto_shrink:
            self.remove_extra_columns(target, evolved_df.schema)

        return evolved_df, evolution_info

    def add_missing_columns(
        self, target: "DataTarget", source_schema: "StructType"
    ) -> None:
        """Add columns from source that don't exist in target.

        Args:
            target: Target to add columns to
            source_schema: Source schema containing new columns
        """
        if not target.supports_schema_evolution():
            return

        if not target.exists():
            return

        target_schema = target.get_schema()
        if target_schema is None:
            return

        target_cols = {field.name for field in target_schema.fields}
        source_cols = {field.name: field for field in source_schema.fields}

        missing_cols = set(source_cols.keys()) - target_cols

        if missing_cols:
            columns_to_add = [source_cols[col_name] for col_name in missing_cols]
            if self.logger:
                self.logger.info(f"Adding new columns to target: {list(missing_cols)}")
            target.add_columns(columns_to_add)

    def remove_extra_columns(
        self, target: "DataTarget", source_schema: "StructType"
    ) -> None:
        """Remove columns from target that don't exist in source.

        Args:
            target: Target to remove columns from
            source_schema: Source schema to compare against
        """
        if not target.supports_schema_evolution():
            return

        if not target.exists():
            return

        target_schema = target.get_schema()
        if target_schema is None:
            return

        # Don't remove metadata columns
        target_cols = {
            field.name
            for field in target_schema.fields
            if field.name not in self.metadata_fields
        }
        source_cols = {field.name for field in source_schema.fields}

        extra_cols = target_cols - source_cols

        if extra_cols:
            if self.logger:
                self.logger.info(f"Removing columns from target: {list(extra_cols)}")
            target.drop_columns(list(extra_cols))

    def ensure_metadata_columns(
        self, target: "DataTarget", metadata_fields: List["StructField"]
    ) -> None:
        """Ensure target has metadata columns if it exists and doesn't have them.

        Args:
            target: Target to check/modify
            metadata_fields: List of metadata fields to add
        """
        if not target.exists():
            return

        target_schema = target.get_schema()
        if target_schema is None:
            return

        # Check if target already has all metadata columns
        target_field_names = {field.name for field in target_schema.fields}
        metadata_field_names = {field.name for field in metadata_fields}

        missing_metadata = metadata_field_names - target_field_names

        if missing_metadata:
            if target.supports_schema_evolution():
                # Add metadata columns to target
                fields_to_add = [
                    field for field in metadata_fields if field.name in missing_metadata
                ]
                if self.logger:
                    self.logger.info(
                        f"Adding metadata columns to existing target: {[f.name for f in fields_to_add]}"
                    )
                target.add_columns(fields_to_add)
            else:
                # Target doesn't support schema evolution
                raise NotImplementedError(
                    f"Target {target} exists without metadata columns but doesn't support schema evolution. "
                    f"Cannot add metadata columns to target."
                )

    def align_with_target(
        self,
        df: "DataFrame",
        target_schema: "StructType",
        include_metadata: bool = False,
    ) -> "DataFrame":
        """Align DataFrame with target schema.

        Args:
            df: DataFrame to align
            target_schema: Target schema to align with
            include_metadata: Whether to include metadata columns in alignment

        Returns:
            Aligned DataFrame
        """
        if include_metadata:
            return self.aligner.align_dataframe_exactly(df, target_schema)
        else:
            return self.aligner.align_source_with_target_schema(
                df, target_schema, self.auto_shrink
            )
