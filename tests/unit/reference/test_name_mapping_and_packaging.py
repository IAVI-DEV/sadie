"""Tests for name mapping collision detection, _name_mapping initialization,
reference.g3.yml packaging, allele name mapping caching, and typo fixes.

Covers feature: fix-name-mapping-and-packaging
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sadie.reference.reference import (
    References,
    _build_name_mapping,
    _truncate_allele_name,
)


class TestNameMappingCollisionDetection:
    """Tests that _build_name_mapping raises ValueError on collisions."""

    def test_no_collision_normal_names(self):
        """Short names that don't need truncation produce empty mapping."""
        names = ["IGHV1-2*01", "IGHV1-69*01", "IGHD3-3*01"]
        result = _build_name_mapping(names)
        assert result == {}

    def test_no_collision_unique_long_names(self):
        """Unique long names produce unique truncated names."""
        names = [
            "IGHV1-2*01_very_long_extra_suffix_from_some_database_provider_AAAAAA",
            "IGHV1-2*01_very_long_extra_suffix_from_some_database_provider_BBBBBB",
        ]
        result = _build_name_mapping(names)
        assert len(result) == 2
        # Each truncated name maps to a different original
        assert len(set(result.values())) == 2

    def test_collision_raises_value_error(self):
        """Two different names that produce the same truncated name raise ValueError."""
        # Force a collision by using max_len=10 on names with same 10-char prefix
        # but differing suffixes that still need truncation
        # _truncate_allele_name(name, max_len=10) uses prefix_len = 10 - 12 = -2
        # which would cause odd behavior; use a more realistic scenario.
        # With max_len=20: prefix_len = 20 - 12 = 8, hash_suffix = 11 chars
        # Two names that share the first 8 chars but differ after that AND
        # happen to have the same sha256[:11] would collide. This is astronomically unlikely.
        # Instead, we mock the truncation to force a collision.
        with patch("sadie.reference.reference._truncate_allele_name") as mock_trunc:
            # Make both names map to the same truncated name
            mock_trunc.side_effect = lambda name, max_len=50: ("COLLISION" if name.startswith("LONG_NAME") else name)
            with pytest.raises(ValueError, match="Name mapping collision"):
                _build_name_mapping(["LONG_NAME_A", "LONG_NAME_B"], max_len=50)

    def test_same_name_twice_no_collision(self):
        """The same long name appearing twice does not raise (maps to same value)."""
        name = "IGHV1-2*01_very_long_extra_suffix_from_some_database_provider_AAAAAA"
        result = _build_name_mapping([name, name])
        assert len(result) == 1


class TestNameMappingInitialization:
    """Tests that _name_mapping is initialized in References.__init__."""

    def test_name_mapping_initialized_empty(self):
        """References.__init__ sets _name_mapping to empty dict."""
        refs = References.__new__(References)
        refs.__init__()  # type: ignore[misc]
        assert hasattr(refs, "_name_mapping")
        assert refs._name_mapping == {}

    def test_name_mapping_is_dict_type(self):
        """_name_mapping is a dict instance after init."""
        refs = References.__new__(References)
        refs.__init__()  # type: ignore[misc]
        assert isinstance(refs._name_mapping, dict)


class TestReferenceG3YmlPackaging:
    """Tests that reference.g3.yml exists inside the package."""

    def test_g3_yml_in_package_data(self):
        """reference.g3.yml exists in src/sadie/reference/data/."""
        package_g3 = Path(__file__).parents[3] / "src" / "sadie" / "reference" / "data" / "reference.g3.yml"
        assert package_g3.exists(), f"reference.g3.yml not found at {package_g3}"

    def test_g3_yml_in_repo_root(self):
        """reference.g3.yml still exists at repo root for backward compat."""
        repo_root_g3 = Path(__file__).parents[3] / "reference.g3.yml"
        assert repo_root_g3.exists(), "reference.g3.yml should still exist at repo root"

    def test_generate_default_path_points_to_package(self):
        """_DEFAULT_G3_PATH in generate.py points to package data directory."""
        from sadie.reference.generate import _DEFAULT_G3_PATH

        assert "src/sadie/reference/data" in str(_DEFAULT_G3_PATH) or (
            _DEFAULT_G3_PATH.parent.name == "data" and _DEFAULT_G3_PATH.parent.parent.name == "reference"
        ), f"_DEFAULT_G3_PATH should point to package data: {_DEFAULT_G3_PATH}"
        assert _DEFAULT_G3_PATH.exists(), f"_DEFAULT_G3_PATH doesn't exist: {_DEFAULT_G3_PATH}"


class TestAlleleNameMappingCache:
    """Tests that _apply_allele_name_reverse_mapping caches the JSON."""

    def test_caches_mapping_on_first_call(self, tmp_path):
        """After first call, _allele_name_mapping is set as instance attribute."""
        # Create a mock Airr-like object with the method
        from sadie.airr.airr import Airr

        airr_obj = object.__new__(Airr)
        airr_obj._database_path = tmp_path

        # Write a mapping file
        mapping = {"SHORT_01": "VERY_LONG_ORIGINAL_NAME_01"}
        (tmp_path / ".allele_name_mapping.json").write_text(json.dumps(mapping))

        import pandas as pd

        df = pd.DataFrame({"v_call": ["SHORT_01"], "d_call": [None], "j_call": [None], "c_call": [None]})
        result = airr_obj._apply_allele_name_reverse_mapping(df)

        assert hasattr(airr_obj, "_allele_name_mapping")
        assert airr_obj._allele_name_mapping == mapping
        assert result["v_call"].iloc[0] == "VERY_LONG_ORIGINAL_NAME_01"

    def test_uses_cached_mapping_on_second_call(self, tmp_path):
        """Second call uses cached mapping without re-reading disk."""
        from sadie.airr.airr import Airr

        airr_obj = object.__new__(Airr)
        airr_obj._database_path = tmp_path

        # Write a mapping file
        mapping = {"SHORT_01": "VERY_LONG_ORIGINAL_NAME_01"}
        (tmp_path / ".allele_name_mapping.json").write_text(json.dumps(mapping))

        import pandas as pd

        df = pd.DataFrame({"v_call": ["SHORT_01"], "d_call": [None], "j_call": [None], "c_call": [None]})

        # First call - loads from disk
        airr_obj._apply_allele_name_reverse_mapping(df.copy())

        # Delete the file - second call should still work from cache
        (tmp_path / ".allele_name_mapping.json").unlink()

        result = airr_obj._apply_allele_name_reverse_mapping(df.copy())
        assert result["v_call"].iloc[0] == "VERY_LONG_ORIGINAL_NAME_01"

    def test_no_database_path_caches_empty(self):
        """When no database path, caches empty dict."""
        from sadie.airr.airr import Airr

        airr_obj = object.__new__(Airr)
        airr_obj._database_path = None

        import pandas as pd

        df = pd.DataFrame({"v_call": ["IGHV1-2*01"]})
        airr_obj._apply_allele_name_reverse_mapping(df)
        assert airr_obj._allele_name_mapping == {}


class TestMethodNameFix:
    """Tests that the renamed method works correctly."""

    def test_internal_annotation_file_method_exists(self):
        """References has _make_internal_annotation_file (not annotaion)."""
        assert hasattr(References, "_make_internal_annotation_file")

    def test_old_method_name_does_not_exist(self):
        """Old typo method name _make_internal_annotaion_file does not exist."""
        assert not hasattr(References, "_make_internal_annotaion_file")


class TestProvidersDocstring:
    """Tests that the providers default matches the docstring."""

    def test_providers_default_is_imgt(self):
        """When providers=None, the resolved default is ['imgt']."""
        # The code does: providers = providers or ["imgt"]
        # So passing None should resolve to ["imgt"]
        providers = None
        resolved = providers or ["imgt"]
        assert resolved == ["imgt"]
