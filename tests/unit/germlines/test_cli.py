"""
Tests for germlines CLI commands.

Tests the `sadie germlines populate` and `sadie germlines status` CLI commands.
"""

import json
import os
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from sadie.app import sadie


@pytest.fixture
def cli_runner():
    """Create CLI runner for testing."""
    return CliRunner()


class TestGermlinesPopulateHelp:
    """Tests for CLI help and basic functionality."""

    def test_germlines_help(self, cli_runner):
        """Test germlines group help."""
        result = cli_runner.invoke(sadie, ["germlines", "--help"])
        assert result.exit_code == 0
        assert "Germline database management commands" in result.output

    def test_populate_help(self, cli_runner):
        """Test populate command help."""
        result = cli_runner.invoke(sadie, ["germlines", "populate", "--help"])
        assert result.exit_code == 0
        assert "--provider" in result.output
        assert "--species" in result.output
        assert "--force" in result.output
        assert "--dry-run" in result.output

    def test_status_help(self, cli_runner):
        """Test status command help."""
        result = cli_runner.invoke(sadie, ["germlines", "status", "--help"])
        assert result.exit_code == 0
        assert "status" in result.output.lower()


class TestGermlinesPopulateDryRun:
    """Tests for dry-run functionality."""

    def test_populate_dry_run_all(self, cli_runner):
        """Test dry-run mode shows what would be downloaded."""
        result = cli_runner.invoke(sadie, ["germlines", "populate", "--dry-run"])
        assert result.exit_code == 0
        assert "DRY RUN" in result.output
        assert "Would download" in result.output

    def test_populate_dry_run_imgt(self, cli_runner):
        """Test dry-run mode for IMGT provider."""
        result = cli_runner.invoke(sadie, ["germlines", "populate", "--provider", "imgt", "--dry-run"])
        assert result.exit_code == 0
        assert "imgt" in result.output.lower()
        assert "Would download" in result.output

    def test_populate_dry_run_single_species(self, cli_runner):
        """Test dry-run mode for single species."""
        result = cli_runner.invoke(
            sadie,
            ["germlines", "populate", "--provider", "imgt", "--species", "human", "--dry-run"],
        )
        assert result.exit_code == 0
        assert "human" in result.output


class TestGermlinesPopulateFailure:
    @pytest.mark.parametrize(
        "provider_name, species, fetched, imgt_answer, status, exit_code",
        [
            ("imgt", ["human"], ["human"], None, "success", 0),
            ("imgt", ["human", "mouse"], ["human"], None, "partial", 1),
            ("imgt", ["human"], [], None, "failed", 1),
            ("ogrdb", ["human"], [], None, "failed", 1),
            ("vdjbase", ["human"], [], None, "failed", 1),
            ("imgt", ["human", "chimpanzee"], ["human"], "TR-only", "success", 0),
            ("imgt", ["human", "chimpanzee"], ["human"], "network error", "partial", 1),
            ("imgt", ["Humann X"], [], "network error", "failed", 1),
        ],
    )
    def test_populate_with_stale_stamp_reports_what_this_run_fetched(
        self, cli_runner, tmp_path, provider_name, species, fetched, imgt_answer, status, exit_code
    ):
        for sp in set(species) - {"chimpanzee", "Humann X"}:
            stale = tmp_path / sp / "IGHV.fasta"
            stale.parent.mkdir()
            stale.write_text(">IGHV1-2*01\nACGT\n")
            os.utime(stale, (0, 0))
        (tmp_path / "VERSION.json").write_text('{"version": "release-200001"}')

        def fetch(species_list, **kwargs):
            for sp in species_list:
                (tmp_path / sp.lower().replace(" ", "_")).mkdir(exist_ok=True)
                if sp in fetched:
                    (tmp_path / sp / "IGHV.fasta").write_text(">IGHV1-2*01\nACGTACGT\n")

        provider = MagicMock(data_dir=tmp_path)
        provider.download.side_effect = fetch
        with (
            patch("sadie.germlines.cli.get_provider_data_dir", return_value=tmp_path),
            patch("sadie.germlines.cli.get_provider", return_value=provider),
            patch("sadie.germlines.scripts.download_imgt.IMGTDownloader") as imgt,
            patch("sadie.germlines.scripts.download_ogrdb.OGRDBDownloader") as ogrdb,
            patch("sadie.germlines.cli.run_post_download_build") as build,
            patch("sadie.germlines.cli.validate_provider_data", return_value=True) as validate,
            patch("sadie.germlines.cli.logger"),  # live logging closes the CliRunner stream
        ):
            imgt.return_value.download.side_effect = fetch
            imgt._IG_UNAVAILABLE_REASONS = {"tr_only": "TR-only"}
            imgt.return_value.check_ig_unavailable_reason.return_value = f"chimpanzee: {imgt_answer}"
            ogrdb.return_value.download.side_effect = fetch
            ogrdb.return_value.allele_counts = {}
            ogrdb.return_value.get_latest_version_string.return_value = "release-1"
            args = [arg for sp in species for arg in ("-s", sp)]
            result = cli_runner.invoke(sadie, ["germlines", "populate", "-p", provider_name, *args])

        assert result.exit_code == exit_code, result.output
        assert status in result.output
        assert build.called == bool(fetched)
        assert validate.called == (status == "success")
        restamped = json.loads((tmp_path / "VERSION.json").read_text())["version"] != "release-200001"
        assert restamped == (status == "success")
        assert not [d for d in tmp_path.iterdir() if d.is_dir() and not any(d.iterdir())]
        assert sorted(f.name for f in tmp_path.iterdir() if f.is_file()) == ["VERSION.json"]
        if provider_name == "imgt":
            assert imgt.return_value.download.call_args.kwargs == {"force": True}

    @pytest.mark.parametrize(
        "page, reason",
        [
            ('<a href="IG/">IG</a><a href="TR/">TR</a>', "IG data exists"),
            ('<a href="TR/">TR</a>', "TR-only"),
            ("<h1>Service temporarily unavailable</h1>", "could not determine"),
        ],
    )
    def test_imgt_species_is_tr_only_only_when_the_page_lists_tr_without_ig(self, tmp_path, page, reason):
        from sadie.germlines.scripts.download_imgt import IMGTDownloader

        response = MagicMock()
        response.__enter__.return_value.read.return_value = page.encode()
        with patch("sadie.germlines.scripts.download_imgt.urlopen", return_value=response):
            assert reason in IMGTDownloader(output_dir=tmp_path).check_ig_unavailable_reason("Homo_sapiens", "human")

    def test_non_imgt_post_download_build_names_the_rebuild_command(self, capsys):
        from sadie.germlines.cli import run_post_download_build

        run_post_download_build("ogrdb", ["human", "mouse"], MagicMock())

        assert "sadie germlines rebuild -s human -s mouse" in " ".join(capsys.readouterr().out.split())


class TestGermlinesStatus:
    """Tests for status command."""

    def test_status_command(self, cli_runner):
        """Test status command shows table."""
        with patch("sadie.germlines.cli.get_upstream_version_string", return_value="release-offline"):
            result = cli_runner.invoke(sadie, ["germlines", "status"])
        assert result.exit_code == 0
        assert "imgt" in result.output.lower()
        assert "ogrdb" in result.output.lower()
        assert "vdjbase" in result.output.lower()


class TestVersionTracking:
    """Tests for version tracking functionality."""

    def test_get_local_version_missing(self, tmp_path):
        """Test get_local_version returns None when no version file."""
        from sadie.germlines.cli import get_local_version

        with patch("sadie.germlines.cli.get_provider_data_dir", return_value=tmp_path):
            result = get_local_version("imgt")
            assert result is None

    def test_save_version_counts_species_on_disk_and_merges_allele_counts(self, tmp_path):
        from sadie.germlines.cli import get_local_version, save_version

        for sp in ("human", "mouse", "_template"):
            (tmp_path / sp).mkdir()
            (tmp_path / sp / "IGHV.fasta").write_text(">a\nACGT\n")
        (tmp_path / "raw").mkdir()

        with patch("sadie.germlines.cli.get_provider_data_dir", return_value=tmp_path):
            save_version("ogrdb", "release-202601", {"human": {"IGHV": {"written": 1}}})
            save_version("ogrdb", "release-202602", {"mouse": {"IGHV": {"written": 1}}})
            result = get_local_version("ogrdb")

        assert result["version"] == "release-202602"
        assert result["species_count"] == 2
        assert sorted(result["allele_counts"]) == ["human", "mouse"]

    def test_is_up_to_date(self, tmp_path):
        """Test is_up_to_date checks version."""
        from sadie.germlines.cli import (
            get_current_version_string,
            is_up_to_date,
            save_version,
        )

        with patch("sadie.germlines.cli.get_provider_data_dir", return_value=tmp_path):
            assert not is_up_to_date("imgt")

            current = get_current_version_string()
            save_version("imgt", current)

            assert is_up_to_date("imgt")


class TestCheckpointHandling:
    """Tests for checkpoint/resume functionality."""

    def test_checkpoint_save_load(self, tmp_path):
        """Test checkpoint save and load."""
        from sadie.germlines.cli import (
            clear_checkpoint,
            load_checkpoint,
            save_checkpoint,
        )

        with patch("sadie.germlines.cli.get_provider_data_dir", return_value=tmp_path):
            completed = {"human", "mouse", "rat"}
            save_checkpoint("imgt", completed, 10)

            loaded = load_checkpoint("imgt")
            assert loaded == completed

            clear_checkpoint("imgt")
            assert load_checkpoint("imgt") == set()

    def test_checkpoint_empty_on_missing(self, tmp_path):
        """Test checkpoint returns empty set when no checkpoint exists."""
        from sadie.germlines.cli import load_checkpoint

        with patch("sadie.germlines.cli.get_provider_data_dir", return_value=tmp_path):
            result = load_checkpoint("imgt")
            assert result == set()


class TestProviderHelpers:
    """Tests for provider helper functions."""

    def test_get_provider_imgt(self):
        """Test get_provider returns IMGT provider."""
        from sadie.germlines.cli import get_provider

        provider = get_provider("imgt")
        assert provider.name == "imgt"

    def test_get_provider_ogrdb(self):
        """Test get_provider returns OGRDB provider."""
        from sadie.germlines.cli import get_provider

        provider = get_provider("ogrdb")
        assert provider.name == "ogrdb"

    def test_get_provider_vdjbase(self):
        """Test get_provider returns VDJbase provider."""
        from sadie.germlines.cli import get_provider

        provider = get_provider("vdjbase")
        assert provider.name == "vdjbase"

    def test_get_provider_invalid(self):
        """Test get_provider raises for invalid provider."""
        from sadie.germlines.cli import get_provider

        with pytest.raises(ValueError, match="Unknown provider"):
            get_provider("invalid")

    def test_get_all_provider_species_imgt(self):
        """Test get_all_provider_species returns IMGT species."""
        from sadie.germlines.cli import get_all_provider_species

        species = get_all_provider_species("imgt")
        assert "human" in species
        assert "mouse" in species
        assert len(species) > 10

    def test_get_all_provider_species_ogrdb(self):
        """Test get_all_provider_species returns OGRDB species."""
        from sadie.germlines.cli import get_all_provider_species

        species = get_all_provider_species("ogrdb")
        assert "human" in species
        assert "mouse" in species


class TestDataValidation:
    """Tests for data validation."""

    def test_validate_provider_data_empty(self, tmp_path):
        """Test validation fails for empty provider."""
        from sadie.germlines.cli import validate_provider_data

        with patch("sadie.germlines.cli.get_provider") as mock_get:
            mock_provider = MagicMock()
            mock_provider.get_metadata.return_value = MagicMock(species_available=[])
            mock_get.return_value = mock_provider

            result = validate_provider_data("imgt")
            assert result is False


class TestImgtGenedbHeader:
    def test_parse_genedb_header_rejects_sheep_d_region_record_matching_heavy_constant_pattern(self):
        from sadie.germlines.scripts.download_imgt import IMGTDownloader

        sheep_ighd2_header = (
            "NW_014639781|IGHD2*01|Ovis aries_Texel|F|D-REGION|16245..16284|40 nt|1| | | | |40+0=40| | |"
        )
        heavy_constant_pattern = {"H": re.compile(r"^IGH[ADEGM]", re.IGNORECASE)}

        parsed = IMGTDownloader()._parse_genedb_header(sheep_ighd2_header, {"Ovis aries"}, heavy_constant_pattern)

        assert parsed is None
