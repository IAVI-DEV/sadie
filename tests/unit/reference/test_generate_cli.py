"""Tests for the `sadie reference generate` CLI command.

Verifies that the CLI command:
1. Uses the new auto-generation logic (generate_reference_yaml)
2. Writes output to a configurable path
3. Prints a summary of species and allele counts
4. Supports --force to overwrite existing files
5. Exits with code 0 on success

Fulfills validation contract assertions:
- VAL-CLI-003: reference generate produces correct output
- VAL-GEN-001: Generate produces valid YAML for all downloaded species
- VAL-CLEAN-001: Old reference.yml deleted from repo root
- VAL-CLEAN-002: reference.g3.yml preserved
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from sadie import app


@pytest.fixture
def runner() -> CliRunner:
    """Provide a Click test runner."""
    return CliRunner()


class TestReferenceGenerateCLI:
    """Tests for the `sadie reference generate` CLI command."""

    def test_help_output(self, runner: CliRunner) -> None:
        """CLI --help returns usage info and exits 0."""
        result = runner.invoke(app.sadie, ["reference", "generate", "--help"])
        assert result.exit_code == 0
        assert "generate" in result.output.lower()
        assert "--output" in result.output or "-o" in result.output
        assert "--force" in result.output

    def test_generate_produces_yaml(self, runner: CliRunner, tmp_path: Path) -> None:
        """VAL-CLI-003: `sadie reference generate` produces a valid reference YAML."""
        output_file = tmp_path / "test_reference.yml"
        result = runner.invoke(
            app.sadie,
            ["reference", "generate", "--output", str(output_file)],
            catch_exceptions=False,
        )
        assert result.exit_code == 0, f"CLI failed with output:\n{result.output}"
        assert output_file.exists(), "Output YAML file should be created"

        # Verify it's valid YAML
        with open(output_file) as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict)
        assert len(data) > 0, "Generated YAML should have at least one reference"

    def test_generate_yaml_structure(self, runner: CliRunner, tmp_path: Path) -> None:
        """Generated YAML follows the expected format: name → provider → species → [alleles]."""
        output_file = tmp_path / "test_structure.yml"
        result = runner.invoke(
            app.sadie,
            ["reference", "generate", "--output", str(output_file)],
            catch_exceptions=False,
        )
        assert result.exit_code == 0

        with open(output_file) as f:
            data = yaml.safe_load(f)

        for name, providers in data.items():
            assert isinstance(providers, dict), f"Providers for '{name}' should be dict"
            for provider, species_dict in providers.items():
                assert provider in ("imgt", "ogrdb", "vdjbase", "custom"), f"Unknown provider '{provider}'"
                assert isinstance(species_dict, dict)
                for species, alleles in species_dict.items():
                    assert isinstance(alleles, list), f"Alleles should be a list for {name}/{provider}/{species}"

    def test_generate_contains_human(self, runner: CliRunner, tmp_path: Path) -> None:
        """Generated YAML contains human reference (known curated species)."""
        output_file = tmp_path / "test_human.yml"
        result = runner.invoke(
            app.sadie,
            ["reference", "generate", "--output", str(output_file)],
            catch_exceptions=False,
        )
        assert result.exit_code == 0

        with open(output_file) as f:
            data = yaml.safe_load(f)

        assert "human" in data, "Generated YAML should contain 'human' reference"
        assert "imgt" in data["human"], "Human reference should have IMGT provider"

    def test_generate_prints_summary(self, runner: CliRunner, tmp_path: Path) -> None:
        """CLI prints a summary of species and allele counts on success."""
        output_file = tmp_path / "test_summary.yml"
        result = runner.invoke(
            app.sadie,
            ["reference", "generate", "--output", str(output_file)],
            catch_exceptions=False,
        )
        assert result.exit_code == 0

        # Should print summary information
        output_lower = result.output.lower()
        assert (
            "reference" in output_lower or "species" in output_lower or "allele" in output_lower
        ), f"Expected summary output about references/species/alleles, got:\n{result.output}"

    def test_generate_refuses_overwrite_without_force(self, runner: CliRunner, tmp_path: Path) -> None:
        """CLI refuses to overwrite existing file without --force."""
        output_file = tmp_path / "existing.yml"
        output_file.write_text("existing content\n")

        result = runner.invoke(
            app.sadie,
            ["reference", "generate", "--output", str(output_file)],
        )
        # Should fail because file exists and --force not given
        assert result.exit_code != 0, "Should refuse to overwrite without --force"

    def test_generate_force_overwrites(self, runner: CliRunner, tmp_path: Path) -> None:
        """CLI with --force overwrites existing file."""
        output_file = tmp_path / "existing.yml"
        output_file.write_text("old content\n")

        result = runner.invoke(
            app.sadie,
            ["reference", "generate", "--force", "--output", str(output_file)],
            catch_exceptions=False,
        )
        assert result.exit_code == 0, f"CLI with --force should succeed, got:\n{result.output}"
        assert output_file.exists()

        # Verify content was overwritten
        with open(output_file) as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict), "Overwritten file should contain valid YAML"

    def test_generate_default_output_path(self, runner: CliRunner) -> None:
        """Default output path is src/sadie/reference/data/reference.yml or similar."""
        result = runner.invoke(app.sadie, ["reference", "generate", "--help"])
        assert result.exit_code == 0
        # Check that the help text mentions a default path
        assert "reference.yml" in result.output or "default" in result.output.lower()

    def test_generate_loadable_by_references(self, runner: CliRunner, tmp_path: Path) -> None:
        """VAL-GEN-001: Generated YAML is loadable by References.from_yaml()."""
        output_file = tmp_path / "loadable.yml"
        result = runner.invoke(
            app.sadie,
            ["reference", "generate", "--output", str(output_file)],
            catch_exceptions=False,
        )
        assert result.exit_code == 0

        from sadie.reference.yaml import YamlRef

        yaml_ref = YamlRef(output_file)
        names = yaml_ref.get_names()
        assert len(names) > 0, "Should have at least one reference name"


class TestReferenceG3YmlPreserved:
    """Tests that reference.g3.yml is preserved (VAL-CLEAN-002)."""

    def test_g3_yml_exists(self) -> None:
        """reference.g3.yml still exists at repo root."""
        g3_path = Path(__file__).parents[3] / "reference.g3.yml"
        assert g3_path.exists(), "reference.g3.yml should still exist at repo root"

    def test_g3_yml_loadable(self) -> None:
        """reference.g3.yml is valid YAML."""
        g3_path = Path(__file__).parents[3] / "reference.g3.yml"
        if not g3_path.exists():
            pytest.skip("reference.g3.yml not found")

        with open(g3_path) as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict)
        assert "human" in data


class TestOldReferenceYmlDeleted:
    """Tests that old manual reference.yml is deleted (VAL-CLEAN-001)."""

    def test_no_reference_yml_at_repo_root(self) -> None:
        """Old reference.yml (or symlink) should not exist at the repo root."""
        repo_root = Path(__file__).parents[3]
        ref_path = repo_root / "reference.yml"
        assert not ref_path.exists(), (
            f"reference.yml should be deleted from repo root. " f"Found: {ref_path} (symlink={ref_path.is_symlink()})"
        )
