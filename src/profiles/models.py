# ClamUI Profile Models
"""
Data models for scan profile management.
"""

import copy
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ScanProfile:
    """
    Represents a saved scan configuration profile.

    A profile stores all settings needed to configure and execute a scan,
    including target directories/files, exclusion patterns, and scan options.

    Attributes:
        id: Unique identifier (UUID) for the profile
        name: User-visible profile name
        targets: List of directories/files to scan
        exclusions: Dictionary of exclusion settings (paths and patterns to skip)
        created_at: ISO 8601 timestamp when profile was created
        updated_at: ISO 8601 timestamp when profile was last modified
        is_default: Whether this is a built-in profile that cannot be deleted
        description: Optional description of the profile's purpose
        options: Additional scan engine options (depth, file types, etc.)
    """

    id: str
    name: str
    targets: list[str]
    exclusions: dict[str, Any]
    created_at: str
    updated_at: str
    is_default: bool = False
    description: str = ""
    options: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the profile to a dictionary for JSON serialization.

        Returns a deep copy to prevent mutations of the returned dict from
        affecting the original profile object.

        Returns:
            Dictionary representation of the profile
        """
        return {
            "id": self.id,
            "name": self.name,
            "targets": copy.deepcopy(self.targets),
            "exclusions": copy.deepcopy(self.exclusions),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "is_default": self.is_default,
            "description": self.description,
            "options": copy.deepcopy(self.options),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScanProfile":
        """
        Create a ScanProfile from a dictionary.

        Args:
            data: Dictionary with profile attributes

        Returns:
            ScanProfile instance

        Raises:
            KeyError: If required fields are missing
            TypeError: If field types are incorrect
        """
        return cls(
            id=data["id"],
            name=data["name"],
            targets=data.get("targets", []),
            exclusions=data.get("exclusions", {}),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            is_default=data.get("is_default", False),
            description=data.get("description", ""),
            options=data.get("options", {}),
        )
