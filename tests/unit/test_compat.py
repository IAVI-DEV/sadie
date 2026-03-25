"""Tests for sadie._compat pandas version detection and compatibility utilities."""

import pandas as pd
import pytest

from sadie._compat import PANDAS_VERSION, NAType, _is_internal_manager


class TestPandasVersion:
    """Tests for PANDAS_VERSION constant."""

    def test_pandas_version_is_tuple(self):
        """PANDAS_VERSION should be a tuple."""
        assert isinstance(PANDAS_VERSION, tuple)

    def test_pandas_version_matches_pd(self):
        """PANDAS_VERSION should match pd.__version__."""
        expected = tuple(int(x) for x in pd.__version__.split(".")[:3])
        assert PANDAS_VERSION == expected

    def test_pandas_version_all_ints(self):
        """All elements of PANDAS_VERSION should be integers."""
        assert all(isinstance(x, int) for x in PANDAS_VERSION)


class TestIsInternalManager:
    """Tests for _is_internal_manager function."""

    def test_dataframe_mgr_is_internal(self):
        """DataFrame._mgr should be recognized as an internal manager."""
        df = pd.DataFrame({"a": [1, 2, 3]})
        assert _is_internal_manager(df._mgr) is True

    def test_series_mgr_is_internal(self):
        """Series._mgr should be recognized as an internal manager."""
        s = pd.Series([1, 2, 3])
        assert _is_internal_manager(s._mgr) is True

    def test_dataframe_is_not_internal(self):
        """A regular DataFrame should NOT be recognized as an internal manager."""
        df = pd.DataFrame({"a": [1, 2, 3]})
        assert _is_internal_manager(df) is False

    def test_dict_is_not_internal(self):
        """A dict should NOT be recognized as an internal manager."""
        assert _is_internal_manager({}) is False

    def test_list_is_not_internal(self):
        """A list should NOT be recognized as an internal manager."""
        assert _is_internal_manager([]) is False

    def test_none_is_not_internal(self):
        """None should NOT be recognized as an internal manager."""
        assert _is_internal_manager(None) is False


class TestNAType:
    """Tests for NAType alias."""

    def test_natype_is_a_type(self):
        """NAType should be a type object (not None)."""
        assert NAType is not None
        assert isinstance(NAType, type)

    def test_natype_matches_pd_na(self):
        """NAType should be the type of pd.NA."""
        assert isinstance(pd.NA, NAType)
