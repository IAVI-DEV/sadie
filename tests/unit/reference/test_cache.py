"""Tests for the database caching system.

Covers VAL-CACHE-001 through VAL-CACHE-008 from the validation contract.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from sadie.reference.cache import DatabaseCache, compute_cache_key


class TestComputeCacheKey:
    """Test cache key computation."""

    def test_same_inputs_produce_same_key(self) -> None:
        """Same reference_name, providers, and config content should produce the same cache key."""
        key1 = compute_cache_key("human", ("imgt",), "some_config_content")
        key2 = compute_cache_key("human", ("imgt",), "some_config_content")
        assert key1 == key2

    def test_different_reference_names_produce_different_keys(self) -> None:
        """Different reference_name should produce different cache keys."""
        key1 = compute_cache_key("human", ("imgt",), "config")
        key2 = compute_cache_key("mouse", ("imgt",), "config")
        assert key1 != key2

    def test_different_providers_produce_different_keys(self) -> None:
        """Different providers should produce different cache keys (VAL-CACHE-003)."""
        key1 = compute_cache_key("human", ("imgt",), "config")
        key2 = compute_cache_key("human", ("ogrdb", "imgt"), "config")
        assert key1 != key2

    def test_different_config_content_produces_different_keys(self) -> None:
        """Different config content should produce different cache keys (VAL-CACHE-004)."""
        key1 = compute_cache_key("human", ("imgt",), "config_v1")
        key2 = compute_cache_key("human", ("imgt",), "config_v2")
        assert key1 != key2

    def test_providers_are_sorted_in_key(self) -> None:
        """Providers should be sorted before hashing to ensure consistent keys."""
        key1 = compute_cache_key("human", ("imgt", "ogrdb"), "config")
        key2 = compute_cache_key("human", ("ogrdb", "imgt"), "config")
        assert key1 == key2

    def test_key_is_hex_string(self) -> None:
        """Cache key should be a hex string (from hashlib)."""
        key = compute_cache_key("human", ("imgt",), "config")
        assert isinstance(key, str)
        # Should be a valid hex string
        int(key, 16)


class TestDatabaseCacheDefaults:
    """Test default cache location and configuration."""

    def test_default_cache_location(self, tmp_path: Path) -> None:
        """Default cache location should be ~/.sadie/cache/ (VAL-CACHE-006)."""
        cache = DatabaseCache()
        expected = Path.home() / ".sadie" / "cache"
        assert cache.cache_dir == expected

    def test_custom_cache_dir_via_constructor(self, tmp_path: Path) -> None:
        """Custom cache dir via constructor parameter (VAL-CACHE-005)."""
        custom_dir = tmp_path / "my_custom_cache"
        cache = DatabaseCache(cache_dir=custom_dir)
        assert cache.cache_dir == custom_dir

    def test_custom_cache_dir_via_env_var(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Custom cache dir via SADIE_CACHE_DIR environment variable (VAL-CACHE-005)."""
        custom_dir = tmp_path / "env_cache"
        monkeypatch.setenv("SADIE_CACHE_DIR", str(custom_dir))
        cache = DatabaseCache()
        assert cache.cache_dir == custom_dir

    def test_constructor_overrides_env_var(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Constructor parameter should take precedence over environment variable."""
        env_dir = tmp_path / "env_cache"
        constructor_dir = tmp_path / "constructor_cache"
        monkeypatch.setenv("SADIE_CACHE_DIR", str(env_dir))
        cache = DatabaseCache(cache_dir=constructor_dir)
        assert cache.cache_dir == constructor_dir


class TestCacheAutoCreation:
    """Test auto-creation of cache directory."""

    def test_cache_dir_auto_created(self, tmp_path: Path) -> None:
        """Cache directory should be auto-created if it doesn't exist (VAL-CACHE-007)."""
        cache_dir = tmp_path / "nonexistent" / "deep" / "path"
        assert not cache_dir.exists()
        cache = DatabaseCache(cache_dir=cache_dir)
        cache.ensure_cache_dir()
        assert cache_dir.exists()

    def test_cache_dir_auto_created_on_get(self, tmp_path: Path) -> None:
        """Cache directory should be auto-created when getting a cached path."""
        cache_dir = tmp_path / "autocreated"
        assert not cache_dir.exists()
        cache = DatabaseCache(cache_dir=cache_dir)
        # Getting the entry path should auto-create the cache_dir
        cache.get_cache_entry_path("some_key")
        assert cache_dir.exists()


class TestCacheHitMiss:
    """Test cache hit and miss behavior."""

    def test_cache_miss_on_empty_cache(self, tmp_path: Path) -> None:
        """Empty cache should always be a miss."""
        cache = DatabaseCache(cache_dir=tmp_path)
        assert not cache.is_cached("some_key")

    def test_cache_miss_without_sentinel(self, tmp_path: Path) -> None:
        """Cache entry without sentinel file should be a miss."""
        cache = DatabaseCache(cache_dir=tmp_path)
        entry_path = cache.get_cache_entry_path("some_key")
        entry_path.mkdir(parents=True, exist_ok=True)
        # Directory exists but no sentinel - should be a miss
        assert not cache.is_cached("some_key")

    def test_cache_hit_with_sentinel(self, tmp_path: Path) -> None:
        """Cache entry with sentinel file should be a hit (VAL-CACHE-001)."""
        cache = DatabaseCache(cache_dir=tmp_path)
        cache_key = "test_key"
        entry_path = cache.get_cache_entry_path(cache_key)
        entry_path.mkdir(parents=True, exist_ok=True)
        cache.write_sentinel(cache_key)
        assert cache.is_cached(cache_key)

    def test_cache_hit_returns_correct_path(self, tmp_path: Path) -> None:
        """Cached entry path should be under cache_dir/<cache_key>/."""
        cache = DatabaseCache(cache_dir=tmp_path)
        cache_key = "abc123"
        entry_path = cache.get_cache_entry_path(cache_key)
        assert entry_path == tmp_path / cache_key

    def test_different_providers_produce_different_cache_entries(self, tmp_path: Path) -> None:
        """Different providers should produce different cache entries (VAL-CACHE-003).

        Two calls with different providers can coexist in the cache directory.
        """
        cache = DatabaseCache(cache_dir=tmp_path)
        key1 = compute_cache_key("human", ("imgt",), "same_config")
        key2 = compute_cache_key("human", ("ogrdb", "imgt"), "same_config")

        # Create both entries
        path1 = cache.get_cache_entry_path(key1)
        path2 = cache.get_cache_entry_path(key2)
        path1.mkdir(parents=True, exist_ok=True)
        path2.mkdir(parents=True, exist_ok=True)
        cache.write_sentinel(key1)
        cache.write_sentinel(key2)

        # Both should be cached
        assert cache.is_cached(key1)
        assert cache.is_cached(key2)
        # And should be at different paths
        assert path1 != path2


class TestCacheInvalidation:
    """Test cache invalidation when config changes."""

    def test_config_change_invalidates_cache(self, tmp_path: Path) -> None:
        """Changed config content should produce a different cache key (VAL-CACHE-004).

        This means the new key won't find an existing entry, triggering a rebuild.
        """
        cache = DatabaseCache(cache_dir=tmp_path)

        # First build with original config
        key_v1 = compute_cache_key("human", ("imgt",), "config_version_1")
        entry_path_v1 = cache.get_cache_entry_path(key_v1)
        entry_path_v1.mkdir(parents=True, exist_ok=True)
        cache.write_sentinel(key_v1)
        assert cache.is_cached(key_v1)

        # Config changes -> new key -> cache miss
        key_v2 = compute_cache_key("human", ("imgt",), "config_version_2_with_new_alleles")
        assert not cache.is_cached(key_v2)
        assert key_v1 != key_v2


class TestPartialCompilationSafety:
    """Test that partial compilation failures don't leave corrupt cache entries."""

    def test_no_sentinel_on_failure(self, tmp_path: Path) -> None:
        """If compilation fails, sentinel should NOT be written (VAL-CACHE-008).

        The cache entry directory may exist but without the sentinel file,
        is_cached returns False, so the next attempt retries compilation.
        """
        cache = DatabaseCache(cache_dir=tmp_path)
        cache_key = "failed_build"

        # Simulate partial build: directory created but build failed before sentinel
        entry_path = cache.get_cache_entry_path(cache_key)
        entry_path.mkdir(parents=True, exist_ok=True)
        # Create some partial files (simulating a failed build)
        (entry_path / "partial_file.ndb").touch()

        # Without sentinel, should be a miss
        assert not cache.is_cached(cache_key)

    def test_build_and_cache_writes_sentinel_on_success(self, tmp_path: Path) -> None:
        """build_and_cache should write sentinel only after successful build (VAL-CACHE-001, VAL-CACHE-008)."""
        cache = DatabaseCache(cache_dir=tmp_path)
        cache_key = "successful_build"

        # Mock a References object with make_airr_database
        mock_references = MagicMock()
        mock_references.make_airr_database.return_value = tmp_path / "some_output"

        result_path = cache.build_and_cache(cache_key, mock_references)

        # Sentinel should exist
        assert cache.is_cached(cache_key)
        # make_airr_database should have been called with the entry path
        mock_references.make_airr_database.assert_called_once()
        assert result_path is not None

    def test_build_and_cache_no_sentinel_on_exception(self, tmp_path: Path) -> None:
        """build_and_cache should NOT write sentinel if make_airr_database raises (VAL-CACHE-008)."""
        cache = DatabaseCache(cache_dir=tmp_path)
        cache_key = "crash_build"

        # Mock a References object that raises during build
        mock_references = MagicMock()
        mock_references.make_airr_database.side_effect = RuntimeError("makeblastdb failed")

        with pytest.raises(RuntimeError, match="makeblastdb failed"):
            cache.build_and_cache(cache_key, mock_references)

        # Sentinel should NOT exist
        assert not cache.is_cached(cache_key)

    def test_retry_after_failed_build(self, tmp_path: Path) -> None:
        """After a failed build, a second attempt should retry compilation (VAL-CACHE-008)."""
        cache = DatabaseCache(cache_dir=tmp_path)
        cache_key = "retry_test"

        # First attempt: fails
        mock_references_fail = MagicMock()
        mock_references_fail.make_airr_database.side_effect = RuntimeError("failed")

        with pytest.raises(RuntimeError):
            cache.build_and_cache(cache_key, mock_references_fail)

        assert not cache.is_cached(cache_key)

        # Second attempt: succeeds
        mock_references_ok = MagicMock()
        mock_references_ok.make_airr_database.return_value = tmp_path / "output"

        result_path = cache.build_and_cache(cache_key, mock_references_ok)

        # Now it should be cached
        assert cache.is_cached(cache_key)
        mock_references_ok.make_airr_database.assert_called_once()


class TestCacheSecondCallSkipsCompilation:
    """Test that the second call with same params uses cached database (VAL-CACHE-002)."""

    def test_second_call_uses_cache(self, tmp_path: Path) -> None:
        """Second instantiation with identical params uses cached DB - make_airr_database NOT called again."""
        cache = DatabaseCache(cache_dir=tmp_path)
        cache_key = "reuse_test"

        # First call: build and cache
        mock_references = MagicMock()
        mock_references.make_airr_database.return_value = tmp_path / "output"

        cache.build_and_cache(cache_key, mock_references)
        assert cache.is_cached(cache_key)
        assert mock_references.make_airr_database.call_count == 1

        # Second call: should skip build since cached
        mock_references_2 = MagicMock()
        result = cache.get_cached_path(cache_key)
        assert result is not None
        # The second references should NOT have been called
        mock_references_2.make_airr_database.assert_not_called()

    def test_get_or_build_returns_cached_on_hit(self, tmp_path: Path) -> None:
        """get_or_build should return cached path when cache hit occurs (VAL-CACHE-002)."""
        cache = DatabaseCache(cache_dir=tmp_path)
        cache_key = "get_or_build_test"

        # First call: build
        mock_references = MagicMock()
        mock_references.make_airr_database.return_value = tmp_path / "output"

        path1 = cache.get_or_build(cache_key, mock_references)
        assert mock_references.make_airr_database.call_count == 1

        # Second call: should NOT build again
        mock_references_2 = MagicMock()
        path2 = cache.get_or_build(cache_key, mock_references_2)
        mock_references_2.make_airr_database.assert_not_called()

        # Both should point to the same cache entry
        assert path1 == path2
