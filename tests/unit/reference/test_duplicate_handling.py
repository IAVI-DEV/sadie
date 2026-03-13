"""Tests for duplicate allele name handling across providers in References.from_yaml().

Covers VAL-DUP-001, VAL-DUP-002, VAL-DUP-003 from the validation contract.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

import pytest
import yaml


@pytest.fixture
def yaml_dir(tmp_path: Path) -> Path:
    """Provide a temp directory for writing test YAML fixtures."""
    return tmp_path


def _write_yaml(path: Path, data: Dict[str, Any]) -> Path:
    """Helper to write a YAML dict to a file and return its path.

    Uses sort_keys=False to preserve insertion order of providers,
    which is critical for first-come-first-serve semantics.
    """
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    return path


class TestDuplicateAlleleHandling:
    """Tests for first-come-first-serve duplicate allele handling in References.from_yaml().

    Provider/species combos known to work:
      - imgt → human, mouse
      - ogrdb → human, mouse
      - vdjbase → human (no mouse)
      - custom → mouse (no human)
    """

    def test_duplicate_allele_first_provider_wins(self, yaml_dir: Path) -> None:
        """VAL-DUP-002: When the same allele name appears under two providers,
        the allele from the provider listed first is kept and the duplicate is silently skipped.

        We use ogrdb and imgt for human (both valid providers).
        """
        from sadie.reference.reference import References

        # YAML with same alleles in both ogrdb and imgt providers
        # ogrdb listed first, so ogrdb's version should win
        yaml_data = {
            "test_ref": {
                "ogrdb": {
                    "human": [
                        "IGHV1-2*02",
                        "IGKV1-33*01",
                        "IGKJ3*01",
                        "IGHJ2*01",
                        "IGHD3-10*01",
                    ]
                },
                "imgt": {
                    "human": [
                        "IGHV1-2*02",  # duplicate - should be skipped
                        "IGKV1-33*01",  # duplicate - should be skipped
                        "IGLV2-11*01",  # unique to imgt - should be kept
                        "IGLJ1*01",  # unique to imgt - should be kept
                    ]
                },
            }
        }
        yaml_path = _write_yaml(yaml_dir / "dup_first_wins.yml", yaml_data)

        # Should NOT raise - VAL-DUP-001
        refs = References.from_yaml(yaml_path, use_germlines=True)

        # Verify references were created successfully
        assert "test_ref" in refs.references

        # Get the underlying data and check gene names
        ref = refs.references["test_ref"]
        gene_names = [entry["gene"] for entry in ref.data]

        # Duplicated alleles should appear exactly once
        assert gene_names.count("IGHV1-2*02") == 1
        assert gene_names.count("IGKV1-33*01") == 1

        # Unique alleles from imgt should still be present
        assert "IGLV2-11*01" in gene_names
        assert "IGLJ1*01" in gene_names

        # First provider's version should be kept - verify source is 'ogrdb'
        for entry in ref.data:
            if entry["gene"] == "IGHV1-2*02":
                assert entry["source"] == "ogrdb", "First provider (ogrdb) should win for IGHV1-2*02"
                break

    def test_unique_alleles_preserved(self, yaml_dir: Path) -> None:
        """VAL-DUP-003: Alleles unique to each provider are all included,
        even when there is no overlap at all.
        """
        from sadie.reference.reference import References

        # Two providers with completely unique alleles (no overlap)
        yaml_data = {
            "test_ref": {
                "imgt": {
                    "human": [
                        "IGHV1-2*02",
                        "IGKV1-33*01",
                        "IGKJ3*01",
                        "IGHJ2*01",
                        "IGHD3-10*01",
                    ]
                },
                "ogrdb": {
                    "human": [
                        "IGHV1-69*01",
                        "IGHD3-16*02",
                    ]
                },
            }
        }
        yaml_path = _write_yaml(yaml_dir / "all_unique.yml", yaml_data)

        refs = References.from_yaml(yaml_path, use_germlines=True)
        ref = refs.references["test_ref"]
        gene_names = [entry["gene"] for entry in ref.data]

        # All alleles from imgt should be present
        assert "IGHV1-2*02" in gene_names
        assert "IGKV1-33*01" in gene_names
        assert "IGKJ3*01" in gene_names
        assert "IGHJ2*01" in gene_names
        assert "IGHD3-10*01" in gene_names

        # All alleles from ogrdb should be present
        assert "IGHV1-69*01" in gene_names
        assert "IGHD3-16*02" in gene_names

        # Total count = 5 + 2 = 7
        assert len(gene_names) == 7

    def test_mixed_overlap_dedup(self, yaml_dir: Path) -> None:
        """Mixed scenario: some alleles overlap across providers, some are unique.

        Verifies that:
        - Overlapping alleles are deduped (first provider wins)
        - Unique alleles from all providers are preserved
        - Total count is correct
        """
        from sadie.reference.reference import References

        yaml_data = {
            "test_ref": {
                "ogrdb": {
                    "human": [
                        "IGHV1-2*02",  # shared with imgt
                        "IGHV1-69*01",  # unique to ogrdb
                        "IGHD3-10*01",  # shared with imgt
                    ]
                },
                "imgt": {
                    "human": [
                        "IGHV1-2*02",  # duplicate - should be skipped
                        "IGKV1-33*01",  # unique to imgt
                        "IGKJ3*01",  # unique to imgt
                        "IGHJ2*01",  # unique to imgt
                        "IGHD3-10*01",  # duplicate - should be skipped
                    ]
                },
            }
        }
        yaml_path = _write_yaml(yaml_dir / "mixed_overlap.yml", yaml_data)

        refs = References.from_yaml(yaml_path, use_germlines=True)
        ref = refs.references["test_ref"]
        gene_names = [entry["gene"] for entry in ref.data]

        # Shared alleles: first provider (ogrdb) wins
        assert gene_names.count("IGHV1-2*02") == 1
        assert gene_names.count("IGHD3-10*01") == 1

        # Verify ogrdb version was kept for shared alleles
        for entry in ref.data:
            if entry["gene"] == "IGHV1-2*02":
                assert entry["source"] == "ogrdb", "ogrdb should win for IGHV1-2*02 (listed first)"
                break

        # Unique alleles preserved
        assert "IGHV1-69*01" in gene_names  # ogrdb unique
        assert "IGKV1-33*01" in gene_names  # imgt unique
        assert "IGKJ3*01" in gene_names  # imgt unique
        assert "IGHJ2*01" in gene_names  # imgt unique

        # 3 from ogrdb + 3 unique from imgt = 6 total (2 duplicates removed)
        assert len(gene_names) == 6

    def test_duplicate_skipped_logs_debug_message(self, yaml_dir: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Verify that when a duplicate allele is skipped, a debug message is logged."""
        from sadie.reference.reference import References

        yaml_data = {
            "test_ref": {
                "ogrdb": {
                    "human": [
                        "IGHV1-2*02",
                        "IGHJ2*01",
                        "IGHD3-10*01",
                    ]
                },
                "imgt": {
                    "human": [
                        "IGHV1-2*02",  # duplicate
                        "IGKV1-33*01",  # unique
                    ]
                },
            }
        }
        yaml_path = _write_yaml(yaml_dir / "dup_logging.yml", yaml_data)

        with caplog.at_level(logging.DEBUG, logger="Reference"):
            refs = References.from_yaml(yaml_path, use_germlines=True)

        # Check that a debug message about skipping was logged
        dup_messages = [r for r in caplog.records if "duplicate" in r.message.lower() or "skip" in r.message.lower()]
        assert len(dup_messages) > 0, "Expected a debug log message about skipping duplicate alleles"

    def test_no_error_on_cross_provider_duplicates(self, yaml_dir: Path) -> None:
        """VAL-DUP-001: Loading a reference YAML with same allele name under multiple providers
        does not raise an error.
        """
        from sadie.reference.reference import References

        yaml_data = {
            "test_ref": {
                "imgt": {
                    "human": [
                        "IGHV1-2*02",
                        "IGHJ2*01",
                        "IGHD3-10*01",
                    ]
                },
                "ogrdb": {
                    "human": [
                        "IGHV1-2*02",  # same allele as imgt
                    ]
                },
            }
        }
        yaml_path = _write_yaml(yaml_dir / "no_error_dup.yml", yaml_data)

        # This should complete without raising any exception
        refs = References.from_yaml(yaml_path, use_germlines=True)
        assert refs is not None
        assert "test_ref" in refs.references
