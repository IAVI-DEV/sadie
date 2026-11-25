"""
Tests for GermlineManager
==========================

Tests priority-based germline database management.
"""

from pathlib import Path

import pytest

# TODO: Implement tests after data is populated


def test_manager_initialization():
    """Test manager can be initialized."""
    from sadie.germlines.manager import GermlineManager

    manager = GermlineManager(providers=["imgt"])
    assert manager is not None
    assert len(manager.providers) == 1


def test_manager_default_providers():
    """Test default provider order."""
    from sadie.germlines.manager import GermlineManager

    manager = GermlineManager()
    # Priority: vdjbase > ogrdb > imgt > custom (data quality prioritized)
    assert manager.provider_names == ["vdjbase", "ogrdb", "imgt", "custom"]


def test_manager_custom_providers():
    """Test custom provider order."""
    from sadie.germlines.manager import GermlineManager

    manager = GermlineManager(providers=["ogrdb", "imgt"])
    assert manager.provider_names == ["ogrdb", "imgt"]


@pytest.mark.parametrize("source", ["imgt", "ogrdb", "custom"])
def test_validate_species_with_rhesus_macaque_accepts_macaque_data(source):
    from sadie.germlines.manager import GermlineManager

    GermlineManager(providers=[source]).validate_species(source, "rhesus_macaque")


@pytest.mark.parametrize(
    "asked_name, expected_gene, expected_warnings",
    [
        ("IGKV0-AAAA*00", "IGKV0-AAAA*00", []),
        (
            "IGKV-AAAA",
            "IGKV0-AAAA*00",
            ["OGRDB mouse label IGKV-AAAA is now IGKV0-AAAA*00 (same sequence); using IGKV0-AAAA*00"],
        ),
        ("IGKV1-1*i01", None, ["OGRDB mouse label IGKV1-1*i01 not resolved: revised, current release IGKV1-1*01"]),
        ("IGKV1-9*i01", None, ["OGRDB mouse label IGKV1-9*i01 not resolved: retired, current release none"]),
        ("IGKV9-9*01", None, []),
    ],
    ids=["current_name", "renamed_label", "revised_label", "retired_label", "unknown_name"],
)
def test_get_gene_by_name_resolves_old_ogrdb_label_only_when_sequence_is_unchanged(
    tmp_path, caplog, asked_name, expected_gene, expected_warnings
):
    from sadie.germlines.manager import GermlineManager

    species_dir = tmp_path / "ogrdb" / "mouse"
    species_dir.mkdir(parents=True)
    (species_dir / "IGKV.fasta").write_text(">IGKV0-AAAA*00\nGACATTGTGATGACC\n")
    (species_dir / "aliases.tsv").write_text(
        "alias\tcurrent\treason\nIGKV-AAAA\tIGKV0-AAAA*00\trenamed\n"
        "IGKV1-1*i01\tIGKV1-1*01\trevised\nIGKV1-9*i01\t\tretired\n"
    )

    gene = GermlineManager(providers=["ogrdb"], data_dir=tmp_path).get_gene_by_name(asked_name, "mouse")

    assert (gene.name if gene else None) == expected_gene
    assert [r.getMessage() for r in caplog.records if r.name == "sadie.germlines.aliases"] == expected_warnings


# TODO: Add more tests
# - test_fetch_genes()
# - test_priority_deduplication()
# - test_novel_genes_included()
# - test_get_gene_by_name()
