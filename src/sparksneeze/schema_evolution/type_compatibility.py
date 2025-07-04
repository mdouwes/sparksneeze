"""Type compatibility checking for schema evolution."""

from typing import TYPE_CHECKING, Dict, Any, List

if TYPE_CHECKING:
    from pyspark.sql.types import StructType, DataType
    from pyspark.sql import DataFrame
    from ..data_targets import DataTarget


class TypeCompatibilityChecker:
    """Handles type compatibility analysis and resolution for schema evolution."""

    def __init__(self, logger=None):
        """Initialize type compatibility checker.

        Args:
            logger: Logger instance for debug/info messages
        """
        self.logger = logger

    def check_type_compatibility(
        self, source_schema: "StructType", target_schema: "StructType"
    ) -> Dict[str, Any]:
        """Check type compatibility between source and target schemas.

        Args:
            source_schema: Source DataFrame schema
            target_schema: Target schema to compare against

        Returns:
            Dict containing compatibility analysis results
        """

        compatibility: Dict = {
            "compatible_columns": [],
            "source_evolution_needed": [],
            "target_evolution_needed": [],
            "incompatible_columns": [],
        }

        # Create lookup maps
        source_cols = {field.name: field for field in source_schema.fields}
        target_cols = {field.name: field for field in target_schema.fields}

        # Check common columns for type compatibility
        common_cols = set(source_cols.keys()) & set(target_cols.keys())

        for col_name in common_cols:
            source_field = source_cols[col_name]
            target_field = target_cols[col_name]
            source_type = source_field.dataType
            target_type = target_field.dataType

            if source_type == target_type:
                compatibility["compatible_columns"].append(col_name)
            elif self.can_cast_safely(source_type, target_type):
                # Source can be cast to target type
                compatibility["source_evolution_needed"].append(
                    {
                        "column": col_name,
                        "from_type": source_type,
                        "to_type": target_type,
                    }
                )
            elif self.can_cast_safely(target_type, source_type):
                # Target should be evolved to source type (less restrictive)
                compatibility["target_evolution_needed"].append(
                    {
                        "column": col_name,
                        "from_type": target_type,
                        "to_type": source_type,
                    }
                )
            else:
                # Incompatible - convert both to string
                compatibility["incompatible_columns"].append(
                    {
                        "column": col_name,
                        "source_type": source_type,
                        "target_type": target_type,
                    }
                )

        return compatibility

    def can_cast_safely(self, from_type: "DataType", to_type: "DataType") -> bool:
        """Check if one type can be safely cast to another.

        Args:
            from_type: Source data type
            to_type: Target data type

        Returns:
            True if casting is safe, False otherwise
        """
        from pyspark.sql.types import (
            StringType,
            IntegerType,
            LongType,
            FloatType,
            DoubleType,
            DateType,
            TimestampType,
        )

        # String can accept anything
        if isinstance(to_type, StringType):
            return True

        # Numeric type promotions
        if isinstance(from_type, IntegerType) and isinstance(
            to_type, (LongType, FloatType, DoubleType)
        ):
            return True
        if isinstance(from_type, LongType) and isinstance(
            to_type, (FloatType, DoubleType)
        ):
            return True
        if isinstance(from_type, FloatType) and isinstance(to_type, DoubleType):
            return True

        # Date/timestamp compatibility
        if isinstance(from_type, DateType) and isinstance(to_type, TimestampType):
            return True

        return False

    def evolve_source_types(
        self, source_df: "DataFrame", evolution_needed: List[Dict]
    ) -> "DataFrame":
        """Evolve source DataFrame types to match target.

        Args:
            source_df: Source DataFrame to evolve
            evolution_needed: List of type evolution requirements

        Returns:
            DataFrame with evolved types
        """
        from pyspark.sql.functions import col

        evolved_df = source_df

        for evolution in evolution_needed:
            column_name = evolution["column"]
            from_type = evolution["from_type"]
            to_type = evolution["to_type"]

            if self.logger:
                self.logger.info(
                    f"Evolving source column '{column_name}' from {from_type.simpleString()} to {to_type.simpleString()}"
                )
            evolved_df = evolved_df.withColumn(
                column_name, col(column_name).cast(to_type)
            )

        return evolved_df

    def evolve_target_types(
        self, target: "DataTarget", evolution_needed: List[Dict]
    ) -> None:
        """Evolve target schema types to match source.

        Args:
            target: Target to evolve
            evolution_needed: List of type evolution requirements
        """
        if not target.supports_type_evolution():
            if self.logger:
                self.logger.warning(
                    f"Target {target} doesn't support type evolution, skipping target type changes"
                )
            return

        for evolution in evolution_needed:
            column_name = evolution["column"]
            from_type = evolution["from_type"]
            to_type = evolution["to_type"]

            if self.logger:
                self.logger.info(
                    f"Evolving target column '{column_name}' from {from_type.simpleString()} to {to_type.simpleString()}"
                )
            try:
                target.alter_column_type(column_name, to_type)
            except Exception as e:
                if self.logger:
                    self.logger.warning(
                        f"Failed to evolve target column '{column_name}': {str(e)}"
                    )

    def resolve_type_conflicts(
        self,
        source_df: "DataFrame",
        target: "DataTarget",
        incompatible_columns: List[Dict],
    ) -> "DataFrame":
        """Handle incompatible types by converting both to string.

        Args:
            source_df: Source DataFrame
            target: Target to potentially modify
            incompatible_columns: List of incompatible column definitions

        Returns:
            DataFrame with resolved type conflicts
        """
        from pyspark.sql.functions import col
        from pyspark.sql.types import StringType

        evolved_df = source_df

        for incompatible in incompatible_columns:
            column_name = incompatible["column"]
            source_type = incompatible["source_type"]
            target_type = incompatible["target_type"]

            if self.logger:
                self.logger.warning(
                    f"Incompatible types for column '{column_name}': source={source_type.simpleString()}, target={target_type.simpleString()}. Converting both to StringType"
                )

            # Convert source column to string
            evolved_df = evolved_df.withColumn(
                column_name, col(column_name).cast(StringType())
            )

            # Convert target column to string
            if target.supports_type_evolution():
                try:
                    target.alter_column_type(column_name, StringType())
                except Exception as e:
                    if self.logger:
                        self.logger.warning(
                            f"Failed to evolve target column '{column_name}' to string: {str(e)}"
                        )

        return evolved_df
