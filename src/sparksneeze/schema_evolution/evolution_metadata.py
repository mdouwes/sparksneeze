"""Schema evolution metadata tracking utilities."""

from typing import TYPE_CHECKING, Dict, Any
from datetime import datetime

if TYPE_CHECKING:
    pass


class SchemaEvolutionMetadata:
    """Handles creation and tracking of schema evolution metadata."""

    def __init__(self, logger=None):
        """Initialize schema evolution metadata tracker.

        Args:
            logger: Logger instance for debug/info messages
        """
        self.logger = logger

    def create_evolution_metadata(
        self, compatibility: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create metadata tracking schema evolution.

        Args:
            compatibility: Compatibility analysis results from TypeCompatibilityChecker

        Returns:
            Dict containing evolution metadata
        """
        evolution_details = {}

        if compatibility["source_evolution_needed"]:
            evolution_details["source_columns_evolved"] = [
                f"{ev['column']}: {ev['from_type'].simpleString()}->{ev['to_type'].simpleString()}"
                for ev in compatibility["source_evolution_needed"]
            ]

        if compatibility["target_evolution_needed"]:
            evolution_details["target_columns_evolved"] = [
                f"{ev['column']}: {ev['from_type'].simpleString()}->{ev['to_type'].simpleString()}"
                for ev in compatibility["target_evolution_needed"]
            ]

        if compatibility["incompatible_columns"]:
            evolution_details["incompatible_columns_converted"] = [
                f"{inc['column']}: {inc['source_type'].simpleString()},{inc['target_type'].simpleString()}->string"
                for inc in compatibility["incompatible_columns"]
            ]

        has_evolution = any(
            [
                compatibility["source_evolution_needed"],
                compatibility["target_evolution_needed"],
                compatibility["incompatible_columns"],
            ]
        )

        return {
            "schema_evolved": has_evolution,
            "last_evolution_timestamp": datetime.now().isoformat(),
            "evolution_details": evolution_details,
        }

    def get_evolution_summary(self, evolution_metadata: Dict[str, Any]) -> str:
        """Get human-readable summary of schema evolution.

        Args:
            evolution_metadata: Evolution metadata dict

        Returns:
            Human-readable evolution summary
        """
        if not evolution_metadata.get("schema_evolved", False):
            return "No schema evolution performed"

        details = evolution_metadata.get("evolution_details", {})
        summary_parts = []

        if "source_columns_evolved" in details:
            summary_parts.append(
                f"Source columns evolved: {len(details['source_columns_evolved'])}"
            )

        if "target_columns_evolved" in details:
            summary_parts.append(
                f"Target columns evolved: {len(details['target_columns_evolved'])}"
            )

        if "incompatible_columns_converted" in details:
            summary_parts.append(
                f"Incompatible columns converted: {len(details['incompatible_columns_converted'])}"
            )

        return (
            "; ".join(summary_parts) if summary_parts else "Schema evolution performed"
        )
