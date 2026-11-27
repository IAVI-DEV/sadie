"""Tests for build_internal_data script and the internal_data structure.

These tests verify that:
1. build_internal_data creates V-only FASTA files (not symlinks)
2. The BLAST database is built from that file
3. No symlinks exist in internal_data directories
4. GermlineData paths point to the correct locations
"""

import functools
from pathlib import Path

import pytest

from sadie.germlines import get_germlines_base_dir


class TestInternalDataStructure:
    """Tests for the internal_data directory structure."""

    @pytest.fixture
    def internal_data_dir(self) -> Path:
        """Get the internal_data directory."""
        return get_germlines_base_dir() / "igblast" / "Ig" / "internal_data"

    @pytest.fixture
    def database_dir(self) -> Path:
        """Get the database directory."""
        return get_germlines_base_dir() / "igblast" / "database"

    def test_no_symlinks_in_internal_data(self, internal_data_dir: Path) -> None:
        """Test that no symlinks exist in internal_data directories."""
        if not internal_data_dir.exists():
            pytest.skip("internal_data directory not built")

        symlinks_found = []
        for species_dir in internal_data_dir.iterdir():
            if species_dir.is_dir():
                for item in species_dir.iterdir():
                    if item.is_symlink():
                        symlinks_found.append(str(item))

        assert len(symlinks_found) == 0, f"Symlinks found in internal_data: {symlinks_found}"

    def test_combined_fasta_exists_for_human(self, internal_data_dir: Path) -> None:
        """Test that combined FASTA file exists for human."""
        human_internal = internal_data_dir / "human"
        if not human_internal.exists():
            pytest.skip("Human internal_data not built")

        combined_fasta = human_internal / "human_V.fasta"
        assert combined_fasta.exists(), "Combined FASTA should exist"

        # Should NOT have separate D, J, C files in internal_data
        assert not (human_internal / "human_D.fasta").exists(), "Separate D file should not exist in internal_data"
        assert not (human_internal / "human_J.fasta").exists(), "Separate J file should not exist in internal_data"
        assert not (human_internal / "human_C.fasta").exists(), "Separate C file should not exist in internal_data"

    def test_internal_fasta_holds_exactly_the_database_v_genes(
        self, internal_data_dir: Path, database_dir: Path
    ) -> None:
        """D, J and C records in internal_data make igblastn drop J, C and CDR3 on long heavy chains."""

        def headers(fasta: Path) -> set:
            return {line for line in fasta.read_text().splitlines() if line.startswith(">")}

        differing = [
            species.name
            for species in sorted(database_dir.iterdir())
            if species.is_dir()
            if headers(internal_data_dir / species.name / f"{species.name}_V.fasta")
            != headers(species / f"{species.name}_V.fasta")
        ]

        assert differing == []

    def test_blast_database_files_exist(self, internal_data_dir: Path) -> None:
        """Test that BLAST database files are created from combined FASTA."""
        human_internal = internal_data_dir / "human"
        if not human_internal.exists():
            pytest.skip("Human internal_data not built")

        # Check for BLAST database files
        expected_extensions = [".nhr", ".nin", ".nsq"]
        for ext in expected_extensions:
            db_file = human_internal / f"human_V{ext}"
            assert db_file.exists(), f"BLAST database file {db_file.name} should exist"

    def test_ndm_file_exists(self, internal_data_dir: Path) -> None:
        """Test that NDM file is generated correctly."""
        human_internal = internal_data_dir / "human"
        if not human_internal.exists():
            pytest.skip("Human internal_data not built")

        ndm_file = human_internal / "human.ndm.imgt"
        assert ndm_file.exists(), "NDM file should exist"

        # NDM file should have entries
        content = ndm_file.read_text()
        lines = [l for l in content.strip().split("\n") if l]
        assert len(lines) > 0, "NDM file should have entries"


class TestGermlineDataPaths:
    """Tests for GermlineData path configuration."""

    def test_germline_data_paths_point_to_database(self) -> None:
        """Test that V/D/J/C dirs point to the BLAST database dir, not internal_data/.

        With the germlines module enabled (default), paths resolve through
        germlines/igblast/database/.  With the legacy G3 path
        (SADIE_USE_GERMLINES_MODULE=false), they resolve through
        airr/data/germlines/Ig/blastdb/.  Either way they must not point
        into internal_data/.
        """
        from sadie.airr.igblast.germline import GermlineData

        try:
            gd = GermlineData("human")
        except (FileNotFoundError, ValueError) as e:
            pytest.skip(f"Human germline data not available: {e}")

        # Germlines module default: paths use germlines/igblast/database/
        assert "database" in str(gd.v_gene_dir), f"v_gene_dir should use database/, got {gd.v_gene_dir}"
        assert "database" in str(gd.d_gene_dir), f"d_gene_dir should use database/, got {gd.d_gene_dir}"
        assert "database" in str(gd.j_gene_dir), f"j_gene_dir should use database/, got {gd.j_gene_dir}"
        assert "database" in str(gd.c_gene_dir), f"c_gene_dir should use database/, got {gd.c_gene_dir}"
        assert "internal_data" not in str(gd.v_gene_dir), "v_gene_dir must not point into internal_data/"

    def test_germline_data_igdata_points_to_ig(self) -> None:
        """Test that igdata points to Ig/ directory (contains internal_data)."""
        from sadie.airr.igblast.germline import GermlineData

        try:
            gd = GermlineData("human")
        except (FileNotFoundError, ValueError) as e:
            pytest.skip(f"Human germline data not available: {e}")

        # igdata should point to Ig/ (not internal_data directly)
        assert gd.igdata.name == "Ig", f"igdata should point to Ig/, got {gd.igdata}"
        assert (gd.igdata / "internal_data").exists(), "igdata/internal_data should exist"


class TestBuildInternalDataScript:
    """Tests for the build_internal_data script functions."""

    def test_build_combined_fasta_writes_v_genes_only(self, tmp_path: Path) -> None:
        from sadie.germlines.scripts.build_internal_data import build_combined_fasta

        database_dir = tmp_path / "database" / "test"
        database_dir.mkdir(parents=True)
        internal_data_dir = tmp_path / "internal_data" / "test"
        internal_data_dir.mkdir(parents=True)
        (database_dir / "test_V.fasta").write_text(">IGHV1-1*01\nATGC\n>IGHV1-2*01\nGCTA\n>IGHV1-1*01\nATGC\n")
        (database_dir / "test_D.fasta").write_text(">IGHD1-1*01\nAAA\n")
        (database_dir / "test_J.fasta").write_text(">IGHJ1*01\nTTT\n")
        (database_dir / "test_C.fasta").write_text(">IGHA1*01\nCCC\n")

        combined = build_combined_fasta("test", database_dir, internal_data_dir)

        assert combined.read_text() == ">IGHV1-1*01\nATGC\n>IGHV1-2*01\nGCTA\n"

    def test_build_blast_db(self, tmp_path: Path) -> None:
        """Test build_blast_db creates BLAST database files."""
        from sadie.germlines.scripts import build_internal_data
        from sadie.germlines.scripts.build_internal_data import build_blast_db
        from sadie.utility.binaries import find_binary
        from sadie.utility.exception import BinaryNotFoundError

        try:
            find_binary("makeblastdb", Path(build_internal_data.__file__).parent.parent.parent / "reference" / "bin")
        except BinaryNotFoundError:
            pytest.skip("makeblastdb not available")

        # Create test FASTA
        fasta_path = tmp_path / "test.fasta"
        fasta_path.write_text(">seq1\nATGCATGC\n>seq2\nGCTAGCTA\n")

        # Build database
        db_prefix = tmp_path / "test_db"
        result = build_blast_db(fasta_path, db_prefix)

        assert result is True, "build_blast_db should return True on success"

        # Check database files exist
        assert (tmp_path / "test_db.nhr").exists() or (tmp_path / "test_db.nin").exists()

    def test_blast_db_title_is_database_name(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test both germlines makeblastdb callers title the database by name, not by input path."""
        import shutil
        import subprocess

        from sadie.germlines.builders.blast import BlastDBBuilder
        from sadie.germlines.scripts.build_internal_data import build_blast_db

        commands = []
        monkeypatch.setattr(shutil, "which", lambda _: "makeblastdb")
        monkeypatch.setattr(
            subprocess, "run", lambda cmd, **_: commands.append(cmd) or subprocess.CompletedProcess(cmd, 0, "", "")
        )

        build_blast_db(tmp_path / "combined.fasta", tmp_path / "human_V")
        BlastDBBuilder()._run_makeblastdb(tmp_path / "mouse_D.fasta", "D")

        assert [cmd[cmd.index("-title") + 1] for cmd in commands] == ["human_V", "mouse_D"]


@functools.lru_cache(maxsize=None)
def built_ndm_rows(species: str) -> dict:
    from sadie.germlines.scripts.build_internal_data import build_ndm_file

    return {row.split("\t")[0]: row.split("\t", 1)[1] for row in build_ndm_file(species, get_germlines_base_dir())}


@pytest.mark.parametrize(
    "species, allele, expected_bounds",
    [
        pytest.param("rat", "IGHV5-50*01", "1\t75\t76\t99\t100\t150\t151\t174\t175\t288\tVH", id="extra-gap-columns"),
        pytest.param("dog", "IGLV1-100*01", "1\t75\t76\t99\t100\t150\t151\t159\t160\t267\tVL", id="gap-column-in-fwr2"),
        pytest.param("rat", "IGHV1-10*01", "1\t75\t76\t99\t100\t150\t151\t174\t175\t288\tVH", id="missing-trp41"),
        pytest.param("rat", "IGHV1-20*01", "1\t75\t76\t99\t100\t150\t151\t174\t175\t288\tVH", id="missing-cys104"),
        pytest.param("rat", "IGKV2S21*01", "1\t75\t76\t108\t109\t159\t160\t168\t169\t261\tVK", id="cys-after-104"),
        pytest.param("rat", "IGHV10-12*01", "1\t75\t76\t99\t100\t150\t151\t180\t181\t294\tVH", id="y-c-c"),
        pytest.param("macaque", "IGHV10-4V64*01", "1\t75\t76\t99\t100\t150\t151\t177\t178\t291\tVH", id="fwr1-insert"),
        pytest.param(
            "cynomolgus", "IGHV4-117*01_S8168", "1\t72\t73\t99\t100\t150\t151\t171\t172\t285\tVH", id="trp39-not-trp41"
        ),
        pytest.param(
            "macaque", "IGKV0-J3H5*01", "1\t78\t79\t96\t97\t147\t148\t156\t157\t261\tVK", id="cys-without-y-x-c"
        ),
        pytest.param(
            "macaque", "IGLV0-4ZZC*01", "1\t78\t79\t96\t97\t147\t148\t156\t157\t261\tVL", id="no-borrowed-shift"
        ),
    ],
)
def test_build_ndm_file_bounds_follow_the_gap_layout_of_the_alignment(
    species: str, allele: str, expected_bounds: str
) -> None:
    assert built_ndm_rows(species)[allele] == f"{expected_bounds}\t0"


LONG_V_NAME = "IGHV1-18*04_t81a_t90c_a106g_g112t_g113a_c117g_a118c_g119a"
LONG_V_DATABASE_ID = "IGHV1-18*04_t81a_t90c_a106g_g112t_g113a_c117g"


@pytest.mark.parametrize(
    "ungapped_names, gapped_names, expected_row_names",
    [
        pytest.param([LONG_V_NAME], [LONG_V_NAME], [LONG_V_DATABASE_ID], id="name-over-50-chars"),
        pytest.param(
            [f"{LONG_V_NAME}_a190g", LONG_V_NAME],
            [LONG_V_NAME, f"{LONG_V_NAME}_a190g"],
            [f"{LONG_V_DATABASE_ID}_1", LONG_V_DATABASE_ID],
            id="repeat-suffixed-in-ungapped-order",
        ),
    ],
)
def test_build_ndm_file_names_each_row_by_its_blast_database_id(
    tmp_path: Path, ungapped_names: list, gapped_names: list, expected_row_names: list
) -> None:
    from sadie.germlines.scripts.build_internal_data import build_ndm_file

    gapped_v = "CAG" * 33 + "..." + "CAG" * 70
    fastas = {"ungapped": (ungapped_names, gapped_v.replace(".", "")), "gapped": (gapped_names, gapped_v)}
    for layout, (names, seq) in fastas.items():
        fasta = tmp_path / "normalized" / "fake" / layout / "IGHV.fasta"
        fasta.parent.mkdir(parents=True)
        fasta.write_text("".join(f">{name}\n{seq}\n" for name in names))

    assert [row.split("\t")[0] for row in build_ndm_file("fake", tmp_path)] == expected_row_names
