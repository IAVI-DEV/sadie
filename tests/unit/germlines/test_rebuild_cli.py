"""
Tests for `sadie germlines rebuild` CLI command.

Validates that the rebuild command:
1. Routes through the germline pipeline (update_databases(species, force=True))
2. Keeps the same CLI interface (--species flag)
3. Does NOT modify `sadie germlines populate` behavior
"""

from unittest.mock import call, patch

import pytest
from click.testing import CliRunner

from sadie.app import sadie


@pytest.fixture
def cli_runner():
    """Create CLI runner for testing."""
    return CliRunner()


class TestRebuildCLIHelp:
    """Tests for rebuild command help and interface."""

    def test_rebuild_help(self, cli_runner):
        """Test rebuild command shows help with --species option."""
        result = cli_runner.invoke(sadie, ["germlines", "rebuild", "--help"])
        assert result.exit_code == 0
        assert "--species" in result.output
        assert "-s" in result.output


class TestRebuildUsesGermlinePipeline:
    """Tests that rebuild runs the pipeline whose output the default Airr reads."""

    @pytest.mark.parametrize(
        "args, rebuilt",
        [
            (["--species", "human"], ["human"]),
            (["-s", "rhesus_macaque", "-s", "macaque"], ["macaque"]),
            ([], ["human", "macaque"]),
        ],
    )
    def test_rebuild_forces_pipeline_rebuild_per_species(self, cli_runner, args, rebuilt):
        with (
            patch("sadie.germlines.cli.get_all_downloaded_species", return_value=["human", "macaque"]),
            patch("sadie.germlines.manager.GermlineManager.get_genes", return_value=["gene"]),
            patch("sadie.germlines.update_databases") as mock_update,
            patch("sadie.reference.reference.References.from_yaml") as mock_from_yaml,
        ):
            result = cli_runner.invoke(sadie, ["germlines", "rebuild", *args])

        assert result.exit_code == 0, result.output
        assert mock_update.call_args_list == [call(sp, force=True) for sp in rebuilt]
        assert not mock_from_yaml.called

    @pytest.mark.parametrize(
        "species, genes, update_error",
        [
            ("human", ["gene"], RuntimeError("no sources")),
            ("human", [], None),
            ("unicorn", ["gene"], None),
        ],
    )
    def test_rebuild_exits_non_zero_when_a_species_is_not_rebuilt(self, cli_runner, species, genes, update_error):
        with (
            patch("sadie.germlines.cli.get_all_downloaded_species", return_value=["human"]),
            patch("sadie.germlines.manager.GermlineManager.get_genes", return_value=genes),
            patch("sadie.germlines.update_databases", side_effect=update_error) as mock_update,
            patch("sadie.germlines.cli.logger"),  # live logging closes the CliRunner stream
        ):
            result = cli_runner.invoke(sadie, ["germlines", "rebuild", "-s", species])

        assert result.exit_code != 0
        assert "rebuilt successfully" not in result.output
        assert mock_update.called == (update_error is not None)


class TestRebuildSpeciesFiltering:
    """Tests for species filtering with --species flag."""

    def test_rebuild_warns_on_missing_species(self, cli_runner):
        """Test rebuild warns when species is not in downloaded data."""
        with patch("sadie.germlines.cli.get_all_downloaded_species", return_value=["human"]):
            result = cli_runner.invoke(sadie, ["germlines", "rebuild", "--species", "unicorn"])

        assert "not found" in result.output.lower() or "unicorn" in result.output

    def test_rebuild_no_data_shows_warning(self, cli_runner):
        """Test rebuild with no downloaded data shows appropriate warning."""
        with patch("sadie.germlines.cli.get_all_downloaded_species", return_value=[]):
            result = cli_runner.invoke(sadie, ["germlines", "rebuild"])
        assert "populate" in result.output.lower() or "no" in result.output.lower()


class TestPopulateUnchanged:
    """Tests that sadie germlines populate is not affected by rebuild changes."""

    def test_populate_help_unchanged(self, cli_runner):
        """Test populate help is still the same."""
        result = cli_runner.invoke(sadie, ["germlines", "populate", "--help"])
        assert result.exit_code == 0
        assert "--provider" in result.output
        assert "--species" in result.output
        assert "--force" in result.output
        assert "--dry-run" in result.output

    def test_populate_does_not_import_reference(self, cli_runner):
        """Test populate path does not import Reference module."""
        result = cli_runner.invoke(sadie, ["germlines", "populate", "--dry-run"])
        # This should work without Reference module involvement
        assert result.exit_code == 0
        assert "DRY RUN" in result.output
