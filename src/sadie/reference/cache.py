"""Database caching system for compiled IgBLAST databases.

Caches compiled IgBLAST databases to avoid recompilation on repeated use.
Cache keys are computed from (reference_name, sorted providers, config content hash).

Usage
-----
    from sadie.reference.cache import DatabaseCache, compute_cache_key

    cache = DatabaseCache()  # uses ~/.sadie/cache/ by default
    cache_key = compute_cache_key("human", ("imgt", "ogrdb"), yaml_content)

    if cache.is_cached(cache_key):
        db_path = cache.get_cached_path(cache_key)
    else:
        db_path = cache.build_and_cache(cache_key, references_obj)

Environment Variables
---------------------
    SADIE_CACHE_DIR : str, optional
        Override the default cache directory (~/.sadie/cache/).
"""

from __future__ import annotations

import hashlib
import logging
import os
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Tuple

if TYPE_CHECKING:
    from sadie.reference.reference import References

logger = logging.getLogger(__name__)

# Sentinel file name written after a successful compilation
_SENTINEL_FILENAME = ".sadie_cache_complete"

# Default cache directory
_DEFAULT_CACHE_DIR = Path.home() / ".sadie" / "cache"


def compute_cache_key(
    reference_name: str,
    providers: Tuple[str, ...],
    config_content: str,
) -> str:
    """Compute a deterministic cache key from reference parameters.

    The key is a SHA-256 hex digest of the combined inputs. Providers are
    sorted before hashing to ensure that ``("imgt", "ogrdb")`` and
    ``("ogrdb", "imgt")`` produce the same key.

    Parameters
    ----------
    reference_name : str
        The reference name (e.g., ``"human"``, ``"mouse"``).
    providers : tuple of str
        Provider names (e.g., ``("imgt",)``, ``("ogrdb", "imgt")``).
    config_content : str
        The raw content of the reference YAML config used for building.

    Returns
    -------
    str
        A hex digest string suitable for use as a directory name.
    """
    sorted_providers = tuple(sorted(providers))
    hasher = hashlib.sha256()
    hasher.update(reference_name.encode("utf-8"))
    hasher.update(str(sorted_providers).encode("utf-8"))
    hasher.update(config_content.encode("utf-8"))
    return hasher.hexdigest()


class DatabaseCache:
    """Manages a local cache of compiled IgBLAST databases.

    Parameters
    ----------
    cache_dir : Path or str, optional
        Override the cache directory. If ``None``, the directory is determined
        by the ``SADIE_CACHE_DIR`` environment variable, falling back to
        ``~/.sadie/cache/``.

    Examples
    --------
    >>> cache = DatabaseCache()
    >>> key = compute_cache_key("human", ("imgt",), yaml_text)
    >>> path = cache.get_or_build(key, references)
    """

    def __init__(self, cache_dir: Optional[Path | str] = None) -> None:
        if cache_dir is not None:
            self._cache_dir = Path(cache_dir)
        else:
            env_dir = os.environ.get("SADIE_CACHE_DIR")
            if env_dir:
                self._cache_dir = Path(env_dir)
            else:
                self._cache_dir = _DEFAULT_CACHE_DIR

    @property
    def cache_dir(self) -> Path:
        """The root cache directory."""
        return self._cache_dir

    def ensure_cache_dir(self) -> None:
        """Create the cache directory if it does not exist."""
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def get_cache_entry_path(self, cache_key: str) -> Path:
        """Return the directory path for a given cache key.

        Auto-creates the root cache directory if missing.

        Parameters
        ----------
        cache_key : str
            The cache key (hex digest).

        Returns
        -------
        Path
            Directory path: ``<cache_dir>/<cache_key>/``
        """
        self.ensure_cache_dir()
        return self._cache_dir / cache_key

    def is_cached(self, cache_key: str) -> bool:
        """Check whether a valid cached database exists for *cache_key*.

        A cache entry is valid only if the entry directory exists **and**
        contains the sentinel file written after a successful compilation.

        Parameters
        ----------
        cache_key : str
            The cache key (hex digest).

        Returns
        -------
        bool
            ``True`` if a valid cache entry exists, ``False`` otherwise.
        """
        entry_path = self._cache_dir / cache_key
        sentinel = entry_path / _SENTINEL_FILENAME
        return sentinel.is_file()

    def get_cached_path(self, cache_key: str) -> Optional[Path]:
        """Return the cached database path if a valid entry exists.

        Parameters
        ----------
        cache_key : str
            The cache key (hex digest).

        Returns
        -------
        Path or None
            The entry directory path if cached, ``None`` otherwise.
        """
        if self.is_cached(cache_key):
            return self._cache_dir / cache_key
        return None

    def write_sentinel(self, cache_key: str) -> None:
        """Write the sentinel file marking a cache entry as complete.

        Parameters
        ----------
        cache_key : str
            The cache key (hex digest).
        """
        entry_path = self._cache_dir / cache_key
        sentinel = entry_path / _SENTINEL_FILENAME
        sentinel.touch()
        logger.debug(f"Wrote cache sentinel for key {cache_key}")

    def build_and_cache(self, cache_key: str, references: References) -> Path:
        """Build the IgBLAST database and store it in the cache.

        Delegates to ``references.make_airr_database()`` with the cache entry
        directory as the output path. A sentinel file is written **only** after
        a successful build. If the build raises, the sentinel is not written
        and the entry remains invalid so that subsequent calls retry.

        Parameters
        ----------
        cache_key : str
            The cache key (hex digest).
        references : References
            A populated ``References`` object ready to build.

        Returns
        -------
        Path
            The cache entry directory containing the compiled database.

        Raises
        ------
        Exception
            Re-raises any exception from ``make_airr_database``.
        """
        entry_path = self.get_cache_entry_path(cache_key)
        entry_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"Building IgBLAST database into cache: {entry_path}")

        # If a previous failed attempt left files, clean them out
        sentinel = entry_path / _SENTINEL_FILENAME
        if sentinel.exists():
            sentinel.unlink()

        try:
            references.make_airr_database(entry_path)
        except Exception:
            logger.error(f"Database build failed for cache key {cache_key}; entry remains invalid")
            raise

        # Only mark complete after successful build
        self.write_sentinel(cache_key)
        logger.info(f"Cached database for key {cache_key} at {entry_path}")
        return entry_path

    def get_or_build(self, cache_key: str, references: References) -> Path:
        """Return a cached database path, building if necessary.

        On cache hit, returns the existing path immediately without calling
        ``make_airr_database``. On cache miss, builds and caches the database.

        Parameters
        ----------
        cache_key : str
            The cache key (hex digest).
        references : References
            A populated ``References`` object (used only on cache miss).

        Returns
        -------
        Path
            Path to the database directory.
        """
        cached = self.get_cached_path(cache_key)
        if cached is not None:
            logger.info(f"Cache hit for key {cache_key}: {cached}")
            return cached

        logger.info(f"Cache miss for key {cache_key}, building...")
        return self.build_and_cache(cache_key, references)

    def clear(self) -> None:
        """Remove all cached entries.

        Deletes the entire cache directory and its contents.
        """
        if self._cache_dir.exists():
            shutil.rmtree(self._cache_dir)
            logger.info(f"Cleared cache at {self._cache_dir}")
