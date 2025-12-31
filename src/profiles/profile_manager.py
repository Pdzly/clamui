# ClamUI Profile Manager Module
"""
Profile manager module for ClamUI providing scan profile lifecycle management.
Centralizes all profile operations including CRUD, validation, and import/export.
"""

import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .models import ScanProfile
from .profile_storage import ProfileStorage


class ProfileManager:
    """
    Manager for scan profile lifecycle and operations.

    Provides methods for creating, reading, updating, and deleting
    scan profiles. Uses ProfileStorage for persistence.
    """

    def __init__(self, config_dir: Path):
        """
        Initialize the ProfileManager.

        Args:
            config_dir: Directory for storing profile data.
                       Will be created if it doesn't exist.
        """
        self._config_dir = Path(config_dir)
        self._storage = ProfileStorage(self._config_dir / "profiles.json")

        # Thread lock for safe concurrent access
        self._lock = threading.Lock()

        # In-memory cache of profiles
        self._profiles: dict[str, ScanProfile] = {}

        # Load profiles on initialization
        self._load()

    def _load(self) -> None:
        """Load profiles from storage into memory."""
        with self._lock:
            profiles = self._storage.load_profiles()
            self._profiles = {p.id: p for p in profiles}

    def _save(self) -> bool:
        """
        Save all profiles to storage.

        Returns:
            True if saved successfully, False otherwise
        """
        with self._lock:
            profiles = list(self._profiles.values())
        return self._storage.save_profiles(profiles)

    def _generate_id(self) -> str:
        """Generate a unique profile ID."""
        return str(uuid.uuid4())

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO 8601 format."""
        return datetime.now(timezone.utc).isoformat()

    def create_profile(
        self,
        name: str,
        targets: list[str],
        exclusions: dict[str, Any],
        description: str = "",
        options: Optional[dict[str, Any]] = None,
        is_default: bool = False,
    ) -> ScanProfile:
        """
        Create and save a new profile.

        Args:
            name: User-visible profile name
            targets: List of directories/files to scan
            exclusions: Dictionary of exclusion settings
            description: Optional description of the profile
            options: Optional scan engine options
            is_default: Whether this is a built-in profile

        Returns:
            The newly created ScanProfile

        Raises:
            ValueError: If validation fails
        """
        timestamp = self._get_timestamp()

        profile = ScanProfile(
            id=self._generate_id(),
            name=name,
            targets=list(targets),
            exclusions=dict(exclusions) if exclusions else {},
            created_at=timestamp,
            updated_at=timestamp,
            is_default=is_default,
            description=description,
            options=dict(options) if options else {},
        )

        with self._lock:
            self._profiles[profile.id] = profile

        self._save()
        return profile

    def get_profile(self, profile_id: str) -> Optional[ScanProfile]:
        """
        Retrieve a profile by ID.

        Args:
            profile_id: The unique identifier of the profile

        Returns:
            The ScanProfile if found, None otherwise
        """
        with self._lock:
            return self._profiles.get(profile_id)

    def get_profile_by_name(self, name: str) -> Optional[ScanProfile]:
        """
        Retrieve a profile by name.

        Args:
            name: The profile name to search for

        Returns:
            The ScanProfile if found, None otherwise
        """
        with self._lock:
            for profile in self._profiles.values():
                if profile.name == name:
                    return profile
        return None

    def update_profile(self, profile_id: str, **updates: Any) -> Optional[ScanProfile]:
        """
        Update an existing profile.

        Args:
            profile_id: The unique identifier of the profile to update
            **updates: Keyword arguments for fields to update
                      (name, targets, exclusions, description, options)

        Returns:
            The updated ScanProfile if found, None otherwise

        Raises:
            ValueError: If validation fails or trying to change protected fields
        """
        with self._lock:
            profile = self._profiles.get(profile_id)
            if profile is None:
                return None

            # Create updated profile with new values
            updated_profile = ScanProfile(
                id=profile.id,
                name=updates.get("name", profile.name),
                targets=updates.get("targets", profile.targets),
                exclusions=updates.get("exclusions", profile.exclusions),
                created_at=profile.created_at,
                updated_at=self._get_timestamp(),
                is_default=profile.is_default,  # Cannot change is_default
                description=updates.get("description", profile.description),
                options=updates.get("options", profile.options),
            )

            self._profiles[profile_id] = updated_profile

        self._save()
        return updated_profile

    def delete_profile(self, profile_id: str) -> bool:
        """
        Delete a profile.

        Cannot delete default profiles.

        Args:
            profile_id: The unique identifier of the profile to delete

        Returns:
            True if deleted successfully, False if not found or is default

        Raises:
            ValueError: If attempting to delete a default profile
        """
        with self._lock:
            profile = self._profiles.get(profile_id)
            if profile is None:
                return False

            if profile.is_default:
                raise ValueError("Cannot delete default profile")

            del self._profiles[profile_id]

        self._save()
        return True

    def list_profiles(self) -> list[ScanProfile]:
        """
        Get all available profiles.

        Returns:
            List of all ScanProfile instances, sorted by name
        """
        with self._lock:
            profiles = list(self._profiles.values())
        return sorted(profiles, key=lambda p: p.name.lower())

    def get_all_profiles(self) -> dict[str, ScanProfile]:
        """
        Get a copy of all profiles as a dictionary.

        Returns:
            Dictionary mapping profile IDs to ScanProfile instances
        """
        with self._lock:
            return dict(self._profiles)

    def profile_exists(self, profile_id: str) -> bool:
        """
        Check if a profile exists.

        Args:
            profile_id: The unique identifier to check

        Returns:
            True if profile exists, False otherwise
        """
        with self._lock:
            return profile_id in self._profiles

    def name_exists(self, name: str, exclude_id: Optional[str] = None) -> bool:
        """
        Check if a profile name already exists.

        Args:
            name: The name to check
            exclude_id: Optional profile ID to exclude from check
                       (useful when updating a profile's name)

        Returns:
            True if name exists (excluding the specified ID), False otherwise
        """
        with self._lock:
            for profile in self._profiles.values():
                if profile.name == name and profile.id != exclude_id:
                    return True
        return False

    def reload(self) -> None:
        """Reload profiles from storage, discarding in-memory changes."""
        self._load()
