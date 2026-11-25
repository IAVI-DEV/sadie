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


ALIASES = (
    b"alias\tcurrent\treason\nIGKV-AAAA\tIGKV0-AAAA*00\trenamed\nIGKV-ZZZZ\tIGKV0-ZZZZ*00\trenamed\n"
    b"IGKV1-1*i01\tIGKV1-1*01\trevised\nIGKV1-9*i01\t\tretired\n"
)
RENAMED = "OGRDB mouse label IGKV-AAAA is now IGKV0-AAAA*00; using IGKV0-AAAA*00"
NOT_READ = "OGRDB alias file <tmp>/ogrdb/mouse/aliases.tsv not read ({}); no aliases used"


@pytest.mark.parametrize(
    "providers, aliases, asked_name, expected_gene, expected_warnings",
    [
        (["ogrdb"], ALIASES, "IGKV0-AAAA*00", ("IGKV0-AAAA*00", "ogrdb"), []),
        (["ogrdb"], ALIASES, "IGKV-AAAA", ("IGKV0-AAAA*00", "ogrdb"), [RENAMED]),
        (
            ["ogrdb"],
            ALIASES,
            "IGKV-ZZZZ",
            None,
            ["OGRDB mouse label IGKV-ZZZZ not resolved: IGKV0-ZZZZ*00 not found"],
        ),
        (
            ["ogrdb"],
            ALIASES,
            "IGKV1-1*i01",
            None,
            ["OGRDB mouse label IGKV1-1*i01 not resolved: revised, current release IGKV1-1*01"],
        ),
        (
            ["ogrdb"],
            ALIASES,
            "IGKV1-9*i01",
            None,
            ["OGRDB mouse label IGKV1-9*i01 not resolved: retired, current release none"],
        ),
        (["ogrdb"], ALIASES, "IGKV9-9*01", None, []),
        (["vdjbase"], ALIASES, "IGKV-AAAA", None, []),
        (None, ALIASES, "IGKV-AAAA", ("IGKV0-AAAA*00", "ogrdb"), [RENAMED]),
        (["ogrdb"], None, "IGKV-AAAA", None, []),
        (["ogrdb"], b"name\tto\nIGKV-AAAA\tIGKV0-AAAA*00\n", "IGKV-AAAA", None, [NOT_READ.format("KeyError")]),
        (["ogrdb"], b"\xff\xfe\n", "IGKV-AAAA", None, [NOT_READ.format("UnicodeDecodeError")]),
        (["ogrdb"], "directory", "IGKV-AAAA", None, [NOT_READ.format("IsADirectoryError")]),
    ],
    ids=[
        "current_name",
        "renamed_label",
        "renamed_label_current_name_absent",
        "revised_label",
        "retired_label",
        "unknown_name",
        "no_ogrdb_provider",
        "default_providers_take_current_name_from_ogrdb_only",
        "no_alias_file",
        "alias_file_without_alias_column",
        "alias_file_not_utf8",
        "alias_file_is_a_directory",
    ],
)
def test_get_gene_by_name_resolves_old_ogrdb_label_only_when_sequence_is_unchanged(
    tmp_path, caplog, providers, aliases, asked_name, expected_gene, expected_warnings
):
    from sadie.germlines.manager import GermlineManager

    for provider, sequence in [("ogrdb", "GACATTGTGATGACC"), ("vdjbase", "GACATTGTGATGACCA")]:
        (tmp_path / provider / "mouse").mkdir(parents=True)
        (tmp_path / provider / "mouse" / "IGKV.fasta").write_text(f">IGKV0-AAAA*00\n{sequence}\n")
    alias_file = tmp_path / "ogrdb" / "mouse" / "aliases.tsv"
    if aliases == "directory":
        alias_file.mkdir()
    elif aliases:
        alias_file.write_bytes(aliases)

    gene = GermlineManager(providers=providers, data_dir=tmp_path).get_gene_by_name(asked_name, "mouse")

    assert ((gene.name, gene.source) if gene else None) == expected_gene
    assert [
        r.getMessage().replace(str(tmp_path), "<tmp>")
        for r in caplog.records
        if r.name in ("sadie.germlines.manager", "sadie.germlines.aliases")
    ] == expected_warnings


# TODO: Add more tests
# - test_fetch_genes()
# - test_priority_deduplication()
# - test_novel_genes_included()
# - test_get_gene_by_name()
