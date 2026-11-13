"""Tests for the central species registry (issue #26)."""

import pytest

from sadie.germlines.registry import SpeciesRegistry


def test_no_duplicate_canonical_names_in_aliases_values():
    # Every alias value must itself not appear as an alias key
    slugs = set(SpeciesRegistry.ALIASES.values())
    for slug in slugs:
        assert slug not in SpeciesRegistry.ALIASES, (
            f"Slug '{slug}' appears as both an alias value and an alias key — "
            "it would create an ambiguous two-step lookup"
        )


def test_all_aliases_resolve_uniquely():
    seen: dict[str, str] = {}
    for alias, slug in SpeciesRegistry.ALIASES.items():
        assert alias not in seen, f"Alias '{alias}' resolves to both '{seen[alias]}' and '{slug}'"
        seen[alias] = slug


def test_normalize_returns_slug_for_known_alias():
    assert SpeciesRegistry.normalize("rhesus_macaque") == "macaque"


def test_normalize_returns_input_unchanged_for_canonical_slug():
    assert SpeciesRegistry.normalize("macaque") == "macaque"
    assert SpeciesRegistry.normalize("human") == "human"


def test_normalize_returns_input_unchanged_for_unknown_name():
    assert SpeciesRegistry.normalize("unknown_species") == "unknown_species"


def test_all_imgt_reverse_entries_round_trip():
    for slug, imgt_name in SpeciesRegistry.TO_IMGT.items():
        recovered = SpeciesRegistry.FROM_IMGT.get(imgt_name)
        assert recovered == slug, (
            f"TO_IMGT['{slug}'] = '{imgt_name}' but FROM_IMGT['{imgt_name}'] = '{recovered}'"
        )


def test_all_ogrdb_entries_round_trip():
    for ogrdb_name, slug in SpeciesRegistry.FROM_OGRDB.items():
        recovered = SpeciesRegistry.TO_OGRDB.get(slug)
        assert recovered == ogrdb_name, (
            f"FROM_OGRDB['{ogrdb_name}'] = '{slug}' but TO_OGRDB['{slug}'] = '{recovered}'"
        )


def test_all_vdjbase_entries_round_trip():
    for slug, api_name in SpeciesRegistry.TO_VDJBASE.items():
        recovered = SpeciesRegistry.FROM_VDJBASE.get(api_name)
        assert recovered == slug, (
            f"TO_VDJBASE['{slug}'] = '{api_name}' but FROM_VDJBASE['{api_name}'] = '{recovered}'"
        )


def test_all_taxonomy_entries_round_trip():
    for slug, taxon_id in SpeciesRegistry.TAXONOMY_IDS.items():
        recovered = SpeciesRegistry.FROM_TAXON.get(taxon_id)
        assert recovered == slug, (
            f"TAXONOMY_IDS['{slug}'] = '{taxon_id}' but FROM_TAXON['{taxon_id}'] = '{recovered}'"
        )


def test_macaque_aliases_all_resolve_to_macaque():
    for alias in ("rhesus_macaque", "rhesus_monkey", "rhesus"):
        assert SpeciesRegistry.normalize(alias) == "macaque", (
            f"Expected '{alias}' to normalize to 'macaque'"
        )


def test_macaque_imgt_name_is_macaca_mulatta():
    assert SpeciesRegistry.TO_IMGT["macaque"] == "Macaca_mulatta"


def test_macaque_latin_name_is_macaca_mulatta():
    assert SpeciesRegistry.TO_LATIN["macaque"] == "Macaca_mulatta"


def test_macaque_taxonomy_id():
    assert SpeciesRegistry.TAXONOMY_IDS["macaque"] == "9544"


@pytest.mark.parametrize("alias,expected", [
    ("rhesus_macaque", "macaque"),
    ("rhesus_monkey", "macaque"),
    ("cynomolgus_monkey", "cynomolgus"),
    ("homo_sapiens", "human"),
    ("mus_musculus", "mouse"),
    ("sus_scrofa", "pig"),
])
def test_known_aliases_resolve_to_expected_slug(alias, expected):
    assert SpeciesRegistry.normalize(alias) == expected
