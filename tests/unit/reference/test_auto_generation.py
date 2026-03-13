"""Tests for reference YAML auto-generation logic.

Tests verifying:
- Species coverage matches downloaded germline data
- Curated IMGT filtering for species in reference.g3.yml
- Full IMGT inclusion for uncurated species
- Full OGRDB inclusion for species with OGRDB data
- Full VDJbase inclusion for species with VDJbase data
- Generated YAML is loadable by References.from_yaml()

Fulfills validation contract assertions:
- VAL-GEN-001: Generate produces valid YAML for all downloaded species
- VAL-GEN-002: Curated IMGT alleles for species in reference.g3.yml
- VAL-GEN-003: All IMGT alleles for uncurated species
- VAL-GEN-004: All OGRDB alleles included
- VAL-GEN-005: All VDJbase alleles included
"""

import tempfile
from pathlib import Path

import pytest
import yaml

from sadie.germlines.manager import GermlineManager
from sadie.reference.generate import generate_reference_yaml, get_g3_curated_species


# ── Helpers ──────────────────────────────────────────────────────────────────


def _get_all_imgt_alleles_for_species(species: str) -> set[str]:
    """Get all IMGT allele names for a species using the GermlineManager."""
    manager = GermlineManager(providers=["imgt"])
    alleles: set[str] = set()
    for segment in ["V", "D", "J", "C"]:
        for chain in ["H", "K", "L"]:
            genes = manager.get_genes(species, segment, chain, functional_only=False)
            alleles.update(g.name for g in genes)
    return alleles


def _get_all_ogrdb_alleles_for_species(species: str) -> set[str]:
    """Get all OGRDB allele names for a species."""
    manager = GermlineManager(providers=["ogrdb"])
    alleles: set[str] = set()
    for segment in ["V", "D", "J", "C"]:
        for chain in ["H", "K", "L"]:
            genes = manager.get_genes(species, segment, chain, functional_only=False)
            alleles.update(g.name for g in genes)
    return alleles


def _get_all_vdjbase_alleles_for_species(species: str) -> set[str]:
    """Get all VDJbase allele names for a species."""
    manager = GermlineManager(providers=["vdjbase"])
    alleles: set[str] = set()
    for segment in ["V", "D", "J", "C"]:
        for chain in ["H", "K", "L"]:
            genes = manager.get_genes(species, segment, chain, functional_only=False)
            alleles.update(g.name for g in genes)
    return alleles


# ── Tests ────────────────────────────────────────────────────────────────────


class TestGetG3CuratedSpecies:
    """Test the g3 curated species extraction."""

    def test_returns_species_set(self) -> None:
        """g3 curated species returns a dict of reference_name → species set."""
        g3_path = Path(__file__).parents[3] / "reference.g3.yml"
        if not g3_path.exists():
            pytest.skip("reference.g3.yml not found")

        result = get_g3_curated_species(g3_path)
        # Should be a dict mapping reference_name → {provider → {species → [alleles]}}
        assert isinstance(result, dict)
        # human, mouse, dog, clk should be present as reference names
        assert "human" in result
        assert "mouse" in result
        assert "dog" in result
        assert "clk" in result

    def test_curated_species_have_imgt_alleles(self) -> None:
        """Each curated species entry should contain imgt alleles."""
        g3_path = Path(__file__).parents[3] / "reference.g3.yml"
        if not g3_path.exists():
            pytest.skip("reference.g3.yml not found")

        result = get_g3_curated_species(g3_path)
        # The 'human' reference name should have imgt → human → [alleles]
        assert "imgt" in result["human"]
        assert "human" in result["human"]["imgt"]
        assert len(result["human"]["imgt"]["human"]) > 0


class TestGenerateReferenceYaml:
    """Test the main generate_reference_yaml function."""

    def test_produces_valid_yaml_dict(self) -> None:
        """VAL-GEN-001: Generation produces a valid YAML-serializable dict."""
        result = generate_reference_yaml()
        assert isinstance(result, dict)
        assert len(result) > 0

        # Should be serializable as YAML
        yaml_str = yaml.dump(result, default_flow_style=False)
        reloaded = yaml.safe_load(yaml_str)
        assert reloaded == result

    def test_species_coverage_matches_imgt(self) -> None:
        """VAL-GEN-001: Generated config covers all downloaded species."""
        result = generate_reference_yaml()

        # Get all species with IMGT data
        imgt_manager = GermlineManager(providers=["imgt"])
        imgt_species = set(imgt_manager.get_available_species())

        # Every species with IMGT data should appear as a reference name
        # (either directly or as part of a chimeric reference)
        ref_names = set(result.keys())

        # All IMGT species should be covered somewhere in the output
        for species in imgt_species:
            found = False
            for name in ref_names:
                for source in result[name]:
                    if species in result[name][source]:
                        found = True
                        break
                if found:
                    break
            assert found, f"Species '{species}' not found in generated reference YAML"

    def test_curated_imgt_filtering_for_human(self) -> None:
        """VAL-GEN-002: For species in reference.g3.yml, only curated IMGT alleles included."""
        g3_path = Path(__file__).parents[3] / "reference.g3.yml"
        if not g3_path.exists():
            pytest.skip("reference.g3.yml not found")

        result = generate_reference_yaml(g3_yaml_path=g3_path)

        # Load the g3 baseline to get the curated human IMGT alleles
        with open(g3_path) as f:
            g3_data = yaml.safe_load(f)

        # Human should exist in the result
        assert "human" in result
        assert "imgt" in result["human"]
        assert "human" in result["human"]["imgt"]

        # The IMGT alleles for human should match the g3 curated list exactly
        generated_imgt_human = set(result["human"]["imgt"]["human"])
        g3_imgt_human = set(g3_data["human"]["imgt"]["human"])
        assert generated_imgt_human == g3_imgt_human, (
            f"Generated IMGT human alleles should match g3 curated list. "
            f"Extra: {generated_imgt_human - g3_imgt_human}, "
            f"Missing: {g3_imgt_human - generated_imgt_human}"
        )

    def test_all_imgt_alleles_for_uncurated_species(self) -> None:
        """VAL-GEN-003: For species NOT in reference.g3.yml, ALL IMGT alleles included."""
        g3_path = Path(__file__).parents[3] / "reference.g3.yml"
        if not g3_path.exists():
            pytest.skip("reference.g3.yml not found")

        result = generate_reference_yaml(g3_yaml_path=g3_path)

        # Get g3 curated reference names
        with open(g3_path) as f:
            g3_data = yaml.safe_load(f)
        g3_ref_names = set(g3_data.keys())

        # Find a species that is NOT a reference name in g3
        # We know IMGT has many more species than g3 covers
        imgt_manager = GermlineManager(providers=["imgt"])
        all_imgt_species = set(imgt_manager.get_available_species())

        # Species that exist in IMGT but are NOT reference names in g3
        uncurated_species = all_imgt_species - g3_ref_names
        # Also remove species that appear as sub-species in g3 references
        g3_species_used = set()
        for name in g3_data:
            for source in g3_data[name]:
                for species in g3_data[name][source]:
                    g3_species_used.add(species)
        uncurated_species -= g3_species_used

        if not uncurated_species:
            pytest.skip("No uncurated species found")

        # Pick one uncurated species to test
        test_species = sorted(uncurated_species)[0]

        # The uncurated species should have ALL its IMGT alleles included
        all_imgt_alleles = _get_all_imgt_alleles_for_species(test_species)

        if not all_imgt_alleles:
            pytest.skip(f"No IMGT alleles found for {test_species}")

        assert test_species in result, f"Uncurated species '{test_species}' missing from generated YAML"
        assert "imgt" in result[test_species], f"No IMGT section for uncurated species '{test_species}'"
        assert test_species in result[test_species]["imgt"], f"No species key for '{test_species}'"

        generated_alleles = set(result[test_species]["imgt"][test_species])
        assert generated_alleles == all_imgt_alleles, (
            f"Uncurated species '{test_species}' should include ALL IMGT alleles. "
            f"Missing: {all_imgt_alleles - generated_alleles}"
        )

    def test_all_ogrdb_alleles_included(self) -> None:
        """VAL-GEN-004: ALL OGRDB alleles included for species with OGRDB data."""
        result = generate_reference_yaml()

        ogrdb_manager = GermlineManager(providers=["ogrdb"])
        ogrdb_species = ogrdb_manager.get_available_species()

        for species in ogrdb_species:
            all_ogrdb_alleles = _get_all_ogrdb_alleles_for_species(species)
            if not all_ogrdb_alleles:
                continue

            # Find the reference name that contains this species
            found_ref = None
            for ref_name in result:
                if "ogrdb" in result[ref_name] and species in result[ref_name].get("ogrdb", {}):
                    found_ref = ref_name
                    break

            assert found_ref is not None, f"No reference entry with OGRDB data for species '{species}'"

            generated_ogrdb = set(result[found_ref]["ogrdb"][species])
            assert generated_ogrdb == all_ogrdb_alleles, (
                f"OGRDB alleles for '{species}' incomplete. "
                f"Missing: {all_ogrdb_alleles - generated_ogrdb}"
            )

    def test_all_vdjbase_alleles_included(self) -> None:
        """VAL-GEN-005: ALL VDJbase alleles included for species with VDJbase data."""
        result = generate_reference_yaml()

        vdjbase_manager = GermlineManager(providers=["vdjbase"])
        vdjbase_species = vdjbase_manager.get_available_species()

        for species in vdjbase_species:
            all_vdjbase_alleles = _get_all_vdjbase_alleles_for_species(species)
            if not all_vdjbase_alleles:
                continue

            # Find the reference name that contains this species
            found_ref = None
            for ref_name in result:
                if "vdjbase" in result[ref_name] and species in result[ref_name].get("vdjbase", {}):
                    found_ref = ref_name
                    break

            assert found_ref is not None, f"No reference entry with VDJbase data for species '{species}'"

            generated_vdjbase = set(result[found_ref]["vdjbase"][species])
            assert generated_vdjbase == all_vdjbase_alleles, (
                f"VDJbase alleles for '{species}' incomplete. "
                f"Missing: {all_vdjbase_alleles - generated_vdjbase}"
            )

    def test_output_loadable_by_references_from_yaml(self) -> None:
        """VAL-GEN-001: Generated YAML is loadable by References.from_yaml()."""
        result = generate_reference_yaml()

        # Write to a temp file and try to load it
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(result, f, default_flow_style=False)
            temp_path = Path(f.name)

        try:
            from sadie.reference.yaml import YamlRef

            yaml_ref = YamlRef(temp_path)
            names = yaml_ref.get_names()
            assert len(names) > 0, "Should have at least one reference name"
        finally:
            temp_path.unlink()

    def test_curated_species_preserved_from_g3(self) -> None:
        """Curated species from g3 (clk, se09 etc) are preserved with their structure."""
        g3_path = Path(__file__).parents[3] / "reference.g3.yml"
        if not g3_path.exists():
            pytest.skip("reference.g3.yml not found")

        result = generate_reference_yaml(g3_yaml_path=g3_path)

        with open(g3_path) as f:
            g3_data = yaml.safe_load(f)

        # clk is a chimeric reference (human + mouse IMGT alleles)
        if "clk" in g3_data:
            assert "clk" in result
            assert "imgt" in result["clk"]
            # clk should retain the exact curated IMGT alleles from g3
            for species in g3_data["clk"]["imgt"]:
                assert species in result["clk"]["imgt"]
                g3_alleles = set(g3_data["clk"]["imgt"][species])
                gen_alleles = set(result["clk"]["imgt"][species])
                assert gen_alleles == g3_alleles

    def test_custom_g3_yaml_path(self) -> None:
        """Test passing custom g3 YAML path."""
        # Create a minimal g3 YAML
        minimal_g3 = {
            "test_ref": {
                "imgt": {
                    "human": ["IGHV1-2*02", "IGHJ6*01"]
                }
            }
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(minimal_g3, f, default_flow_style=False)
            g3_path = Path(f.name)

        try:
            result = generate_reference_yaml(g3_yaml_path=g3_path)
            # test_ref should be in the result with only the curated alleles
            assert "test_ref" in result
            assert "imgt" in result["test_ref"]
            assert "human" in result["test_ref"]["imgt"]
            assert set(result["test_ref"]["imgt"]["human"]) == {"IGHV1-2*02", "IGHJ6*01"}
        finally:
            g3_path.unlink()

    def test_output_yaml_format_structure(self) -> None:
        """Output follows the format: name → provider → species → [allele_list]."""
        result = generate_reference_yaml()

        for name, providers in result.items():
            assert isinstance(name, str), f"Reference name should be str, got {type(name)}"
            assert isinstance(providers, dict), f"Providers should be dict for '{name}'"

            for provider, species_dict in providers.items():
                assert isinstance(provider, str), f"Provider should be str"
                assert provider in ("imgt", "ogrdb", "vdjbase", "custom"), (
                    f"Unknown provider '{provider}'"
                )
                assert isinstance(species_dict, dict), f"Species dict should be dict"

                for species, alleles in species_dict.items():
                    assert isinstance(species, str), f"Species should be str"
                    assert isinstance(alleles, list), f"Alleles should be list"
                    for allele in alleles:
                        assert isinstance(allele, str), f"Each allele should be str"
