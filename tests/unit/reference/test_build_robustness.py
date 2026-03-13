"""Tests for reference build robustness fixes.

Issue 1: V genes with missing IMGT position annotations should be skipped with a warning,
         not cause a ValueError.
Issue 2: Long allele names (>50 chars, common in VDJbase) should be truncated/hashed for
         BLAST DB compatibility, with a reverse mapping maintained.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Dict, List
from unittest.mock import patch

import pandas as pd
import pytest
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord

from sadie.reference.reference import Reference, References


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_g3_dict(
    gene: str,
    species: str = "human",
    source: str = "imgt",
    sequence: str = "ATGCATGCATGC",
    gene_segment: str = "V",
    label: str = "V-REGION",
    with_imgt_positions: bool = True,
) -> Dict:
    """Create a minimal G3-format dict for testing."""
    d: Dict = {
        "_id": f"{source}_{species}_{gene}",
        "source": source,
        "common": species,
        "gene": gene,
        "label": label,
        "gene_segment": gene_segment,
        "receptor": "Ig",
        "sequence": sequence,
        "latin": "Homo sapiens",
        "gene_curation_source": source,
        "chimera": False,
    }

    imgt: Dict = {
        "sequence_gapped": sequence,
        "sequence_gapped_aa": None,
        "cdr3": None,
        "cdr3_aa": None,
        "fwr4": None,
        "fwr4_aa": None,
        "cdr3_start": None,
        "cdr3_end": None,
        "fwr4_start": None,
        "fwr4_end": None,
        "reading_frame": None,
        "ignored": None,
        "not_implemented": None,
        "expression": None,
        "expression_match": None,
        "remainder": None,
        "imgt_numbering": None,
        "sequence": sequence,
        "imgt_functional": None,
        "contrived_functional": None,
    }

    if with_imgt_positions:
        imgt.update(
            {
                "fwr1": "ATG",
                "fwr1_aa": "M",
                "fwr1_start": 0,
                "fwr1_end": 2,
                "cdr1": "CAT",
                "cdr1_aa": "H",
                "cdr1_start": 3,
                "cdr1_end": 5,
                "fwr2": "GCA",
                "fwr2_aa": "A",
                "fwr2_start": 6,
                "fwr2_end": 8,
                "cdr2": "TGC",
                "cdr2_aa": "C",
                "cdr2_start": 9,
                "cdr2_end": 11,
                "fwr3": "ATG",
                "fwr3_aa": "M",
                "fwr3_start": 12,
                "fwr3_end": 14,
            }
        )
    else:
        imgt.update(
            {
                "fwr1": None,
                "fwr1_aa": None,
                "fwr1_start": None,
                "fwr1_end": None,
                "cdr1": None,
                "cdr1_aa": None,
                "cdr1_start": None,
                "cdr1_end": None,
                "fwr2": None,
                "fwr2_aa": None,
                "fwr2_start": None,
                "fwr2_end": None,
                "cdr2": None,
                "cdr2_aa": None,
                "cdr2_start": None,
                "cdr2_end": None,
                "fwr3": None,
                "fwr3_aa": None,
                "fwr3_start": None,
                "fwr3_end": None,
            }
        )

    # Flatten imgt. prefix
    for k, v in imgt.items():
        d[f"imgt.{k}"] = v

    return d


def _make_d_gene_dict(gene: str = "IGHD3-3*01", species: str = "human") -> Dict:
    """Create a D-region gene dict."""
    return _make_g3_dict(
        gene=gene,
        species=species,
        sequence="GTATTACTATGGTTCGGGGAGT",
        gene_segment="D",
        label="D-REGION",
        with_imgt_positions=True,
    )


def _make_j_gene_dict(gene: str = "IGHJ6*01", species: str = "human") -> Dict:
    """Create a J-region gene dict."""
    d = _make_g3_dict(
        gene=gene,
        species=species,
        sequence="ATTACTACTACTACTACGGTATGGACGTCTGG",
        gene_segment="J",
        label="J-REGION",
        with_imgt_positions=True,
    )
    d["imgt.reading_frame"] = 1
    d["imgt.remainder"] = 2
    d["imgt.cdr3_end"] = 10
    return d


# ---------------------------------------------------------------------------
# Issue 1: Missing IMGT V-region positions
# ---------------------------------------------------------------------------


class TestMissingVRegionPositions:
    """V genes with missing IMGT positions should be skipped, not crash."""

    def test_missing_positions_skipped_with_warning(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Genes with missing IMGT position annotations are skipped with a warning log."""
        v_good = _make_g3_dict("IGHV1-69*01", with_imgt_positions=True)
        v_bad = _make_g3_dict("IGHV1-BAD*01", with_imgt_positions=False)
        d_gene = _make_d_gene_dict()
        j_gene = _make_j_gene_dict()

        ref = Reference(use_germlines=True)
        ref.data = [v_good, v_bad, d_gene, j_gene]

        refs = References()
        refs.add_reference("test", ref)

        with caplog.at_level(logging.WARNING, logger="Reference"):
            # Should NOT raise ValueError
            refs.make_airr_database(tmp_path)

        # Warning about skipped gene should appear
        assert any("IGHV1-BAD*01" in record.message for record in caplog.records)
        assert any(
            "skipping" in record.message.lower() or "skip" in record.message.lower() for record in caplog.records
        )

    def test_good_v_genes_still_in_blast_db(self, tmp_path: Path) -> None:
        """Good V genes are written to the BLAST database even when bad ones are skipped."""
        v_good = _make_g3_dict("IGHV1-69*01", with_imgt_positions=True)
        v_bad = _make_g3_dict("IGHV1-BAD*01", with_imgt_positions=False)
        d_gene = _make_d_gene_dict()
        j_gene = _make_j_gene_dict()

        ref = Reference(use_germlines=True)
        ref.data = [v_good, v_bad, d_gene, j_gene]

        refs = References()
        refs.add_reference("test", ref)
        refs.make_airr_database(tmp_path)

        # The V FASTA should contain the good gene
        v_fasta = tmp_path / "Ig" / "blastdb" / "test" / "test_V.fasta"
        assert v_fasta.exists()
        content = v_fasta.read_text()
        assert "IGHV1-69*01" in content
        # The bad gene should NOT be in the BLAST DB
        assert "IGHV1-BAD*01" not in content

    def test_all_v_missing_raises_error(self, tmp_path: Path) -> None:
        """If ALL V genes are missing positions, we still need at least some V genes."""
        v_bad1 = _make_g3_dict("IGHV1-BAD*01", with_imgt_positions=False)
        v_bad2 = _make_g3_dict("IGHV1-BAD*02", with_imgt_positions=False)
        d_gene = _make_d_gene_dict()
        j_gene = _make_j_gene_dict()

        ref = Reference(use_germlines=True)
        ref.data = [v_bad1, v_bad2, d_gene, j_gene]

        refs = References()
        refs.add_reference("test", ref)

        # This SHOULD still work (V genes are skipped, but D and J are there),
        # though the blast DB for V will be empty. The pipeline writes what it can.
        # The actual error will come from IgBLAST at runtime if V is needed.
        with pytest.raises(ValueError, match="No valid V genes"):
            refs.make_airr_database(tmp_path)


# ---------------------------------------------------------------------------
# Issue 2: Long allele names
# ---------------------------------------------------------------------------


class TestLongAlleleNames:
    """VDJbase-style long allele names should be truncated for BLAST compatibility."""

    LONG_NAME = "IGHV1-18*04_g107c_a110t_g112a_g119c_g126c_c134t_a144g_g147a_g153a_a162c_g164t"
    SHORT_NAME = "IGHV1-69*01"

    def test_long_name_truncated_in_blast_fasta(self, tmp_path: Path) -> None:
        """Gene names longer than 50 chars are truncated in BLAST DB FASTA."""
        assert len(self.LONG_NAME) > 50

        v_long = _make_g3_dict(self.LONG_NAME, with_imgt_positions=True)
        v_short = _make_g3_dict(self.SHORT_NAME, with_imgt_positions=True)
        d_gene = _make_d_gene_dict()
        j_gene = _make_j_gene_dict()

        ref = Reference(use_germlines=True)
        ref.data = [v_long, v_short, d_gene, j_gene]

        refs = References()
        refs.add_reference("test", ref)
        refs.make_airr_database(tmp_path)

        # Check FASTA file for V genes
        v_fasta = tmp_path / "Ig" / "blastdb" / "test" / "test_V.fasta"
        assert v_fasta.exists()
        content = v_fasta.read_text()

        # The full long name should NOT appear as a FASTA header
        for line in content.split("\n"):
            if line.startswith(">"):
                name = line[1:].strip()
                assert len(name) <= 50, f"FASTA header too long: {name} ({len(name)} chars)"

        # Short name should still be present as-is
        assert self.SHORT_NAME in content

    def test_name_mapping_file_created(self, tmp_path: Path) -> None:
        """A name mapping JSON file is created when long names are truncated."""
        v_long = _make_g3_dict(self.LONG_NAME, with_imgt_positions=True)
        v_short = _make_g3_dict(self.SHORT_NAME, with_imgt_positions=True)
        d_gene = _make_d_gene_dict()
        j_gene = _make_j_gene_dict()

        ref = Reference(use_germlines=True)
        ref.data = [v_long, v_short, d_gene, j_gene]

        refs = References()
        refs.add_reference("test", ref)
        refs.make_airr_database(tmp_path)

        # Name mapping file should exist
        mapping_file = tmp_path / ".allele_name_mapping.json"
        assert mapping_file.exists()

        mapping = json.loads(mapping_file.read_text())
        # The mapping should contain the long name
        assert self.LONG_NAME in mapping.values()

    def test_short_names_not_truncated(self, tmp_path: Path) -> None:
        """Gene names under 50 chars should not be truncated."""
        assert len(self.SHORT_NAME) <= 50

        v_short = _make_g3_dict(self.SHORT_NAME, with_imgt_positions=True)
        d_gene = _make_d_gene_dict()
        j_gene = _make_j_gene_dict()

        ref = Reference(use_germlines=True)
        ref.data = [v_short, d_gene, j_gene]

        refs = References()
        refs.add_reference("test", ref)
        refs.make_airr_database(tmp_path)

        # Check FASTA directly
        v_fasta = tmp_path / "Ig" / "blastdb" / "test" / "test_V.fasta"
        content = v_fasta.read_text()
        assert f">{self.SHORT_NAME}" in content

    def test_truncated_names_are_unique(self, tmp_path: Path) -> None:
        """Different long names produce different truncated names."""
        long1 = "IGHV1-18*04_g107c_a110t_g112a_g119c_g126c_c134t_a144g_g147a"
        long2 = "IGHV1-18*04_g107c_a110t_g112a_g119c_g126c_c134t_a144g_g147c"
        assert len(long1) > 50
        assert len(long2) > 50

        v1 = _make_g3_dict(long1, with_imgt_positions=True)
        v2 = _make_g3_dict(long2, with_imgt_positions=True)
        d_gene = _make_d_gene_dict()
        j_gene = _make_j_gene_dict()

        ref = Reference(use_germlines=True)
        ref.data = [v1, v2, d_gene, j_gene]

        refs = References()
        refs.add_reference("test", ref)
        refs.make_airr_database(tmp_path)

        v_fasta = tmp_path / "Ig" / "blastdb" / "test" / "test_V.fasta"
        content = v_fasta.read_text()

        # Extract headers
        headers = [line[1:].strip() for line in content.split("\n") if line.startswith(">")]
        assert len(headers) == len(set(headers)), "Truncated names must be unique"

    def test_internal_data_also_truncated(self, tmp_path: Path) -> None:
        """Internal data FASTA files also have truncated names."""
        v_long = _make_g3_dict(self.LONG_NAME, with_imgt_positions=True)
        v_short = _make_g3_dict(self.SHORT_NAME, with_imgt_positions=True)
        d_gene = _make_d_gene_dict()
        j_gene = _make_j_gene_dict()

        ref = Reference(use_germlines=True)
        ref.data = [v_long, v_short, d_gene, j_gene]

        refs = References()
        refs.add_reference("test", ref)
        refs.make_airr_database(tmp_path)

        # Internal data FASTA
        internal_fasta = tmp_path / "Ig" / "internal_data" / "test" / "test_V.fasta"
        assert internal_fasta.exists()
        content = internal_fasta.read_text()

        for line in content.split("\n"):
            if line.startswith(">"):
                name = line[1:].strip()
                assert len(name) <= 50, f"Internal FASTA header too long: {name} ({len(name)} chars)"
