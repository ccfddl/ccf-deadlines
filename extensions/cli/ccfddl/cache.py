"""Cache management for CCFDDL CLI.

Provides local caching of conference data to enable offline usage
and reduce network requests.
"""

import hashlib
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

DEFAULT_CACHE_DIR = Path.home() / ".cache" / "ccfddl"
DEFAULT_CACHE_EXPIRY_HOURS = 24


class CacheManager:
    """Manages local cache of conference data."""

    def __init__(
        self,
        cache_dir: Path | str | None = None,
        expiry_hours: int = DEFAULT_CACHE_EXPIRY_HOURS,
    ):
        """Initialize cache manager.

        Args:
            cache_dir: Directory to store cache files. Defaults to ~/.cache/ccfddl
            expiry_hours: Hours until cache expires. Defaults to 24.
        """
        self.cache_dir = Path(cache_dir) if cache_dir else DEFAULT_CACHE_DIR
        self.expiry_hours = expiry_hours
        self._ensure_cache_dir()

    def _ensure_cache_dir(self) -> None:
        """Create cache directory if it doesn't exist."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, key: str) -> Path:
        """Get cache file path for a key."""
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.json"

    def _get_metadata_path(self, key: str) -> Path:
        """Get metadata file path for a key."""
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.meta"

    def get(self, key: str) -> Optional[Any]:
        """Get cached data if exists and not expired.

        Args:
            key: Cache key (typically URL)

        Returns:
            Cached data if valid, None otherwise
        """
        cache_path = self._get_cache_path(key)
        meta_path = self._get_metadata_path(key)

        if not cache_path.exists() or not meta_path.exists():
            return None

        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)

            cached_time = datetime.fromisoformat(metadata["timestamp"])
            if datetime.now() - cached_time > timedelta(hours=self.expiry_hours):
                return None

            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)

        except (json.JSONDecodeError, KeyError, ValueError):
            return None

    def set(self, key: str, data: Any) -> None:
        """Store data in cache.

        Args:
            key: Cache key (typically URL)
            data: Data to cache
        """
        cache_path = self._get_cache_path(key)
        meta_path = self._get_metadata_path(key)

        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        metadata = {
            "key": key,
            "timestamp": datetime.now().isoformat(),
        }
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f)

    def clear(self) -> None:
        """Clear all cached data."""
        for file_path in self.cache_dir.iterdir():
            if file_path.is_file():
                file_path.unlink()

    def get_cache_size(self) -> int:
        """Get total cache size in bytes."""
        total = 0
        for file_path in self.cache_dir.iterdir():
            if file_path.is_file():
                total += file_path.stat().st_size
        return total

    def is_cache_valid(self, key: str) -> bool:
        """Check if cached data exists and is not expired.

        Args:
            key: Cache key

        Returns:
            True if valid cache exists
        """
        return self.get(key) is not None


def get_default_cache() -> CacheManager:
    """Get default cache manager instance."""
    return CacheManager()
