from pathlib import Path

import pytest

from sadie.germlines.scripts.download_ogrdb import _extract_insert_blocks
from sadie.germlines.scripts.validate import check_allele_counts, format_count_report


def write_fasta(path: Path, records: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(f">{header}\n{seq}\n" for header, seq in records.items()))


@pytest.fixture
def two_stage_germlines(tmp_path):
    write_fasta(
        tmp_path / "sources/ogrdb/fake/IGHV.fasta",
        {"IGHV1-1*01": "ACGTACGTAC", "IGHV1-2*01": "GGGGCCCCAA", "IGHV1-3*01": "TTTTAAAACC"},
    )
    write_fasta(
        tmp_path / "normalized/fake/ungapped/IGHV.fasta",
        {"IGHV1-1*01 source=ogrdb": "ACGTACGTAC", "IGHV1-2*01 source=vdjbase": "GGGGCCCCAA"},
    )
    write_fasta(
        tmp_path / "normalized/fake/gapped/IGHV.fasta",
        {"IGHV1-1*01 source=ogrdb": "ACGT.ACGTAC", "IGHV1-2*01 source=vdjbase": "GGGG.CCCCAA"},
    )
    (tmp_path / "reference.yml").write_text("fake:\n  ogrdb:\n    fake:\n    - IGHV1-1*01\n")
    return tmp_path


def run_check(germlines_dir: Path):
    return check_allele_counts(germlines_dir, reference_yml=germlines_dir / "reference.yml")


def test_check_allele_counts_classifies_name_held_by_higher_provider_as_expected(two_stage_germlines):
    _, findings = run_check(two_stage_germlines)

    expected_names = [f["names"] for f in findings if f["kind"] == "EXPECTED"]

    assert expected_names == [["IGHV1-2*01 (name held by vdjbase)"]]


def test_check_allele_counts_flags_lost_allele_as_unexplained(two_stage_germlines):
    rows, findings = run_check(two_stage_germlines)

    unexplained_names = [f["names"] for f in findings if f["kind"] == "UNEXPLAINED"]

    assert unexplained_names == [["IGHV1-3*01"]]
    assert rows[0]["ok"] is False


def test_check_allele_counts_row_accounts_for_every_source_allele(two_stage_germlines):
    rows, _ = run_check(two_stage_germlines)

    row = rows[0]

    assert (row["file"], row["src"], row["kept"], row["by_higher"], row["collapsed"], row["norm"]) == (
        "IGHV",
        3,
        1,
        1,
        0,
        2,
    )


def test_check_allele_counts_passes_when_every_source_allele_is_accounted_for(two_stage_germlines):
    write_fasta(
        two_stage_germlines / "sources/ogrdb/fake/IGHV.fasta", {"IGHV1-1*01": "ACGTACGTAC", "IGHV1-2*01": "GGGGCCCCAA"}
    )

    rows, findings = run_check(two_stage_germlines)

    assert rows[0]["ok"] is True
    assert [f for f in findings if f["kind"] == "UNEXPLAINED"] == []


def test_check_allele_counts_flags_reference_yml_name_without_source_record(two_stage_germlines):
    (two_stage_germlines / "reference.yml").write_text("fake:\n  ogrdb:\n    fake:\n    - IGHV9-9*01\n")

    _, findings = run_check(two_stage_germlines)

    reference_findings = [f for f in findings if f["stage"] == "reference.yml->sources"]

    assert [f["names"] for f in reference_findings] == [["IGHV9-9*01"]]


def test_check_allele_counts_flags_constant_gene_filed_in_d_segment_file(two_stage_germlines):
    write_fasta(two_stage_germlines / "sources/ogrdb/fake/IGHD.fasta", {"IGHD1-1*01": "GGTATAGC", "IGHD*02": "A" * 400})
    write_fasta(two_stage_germlines / "normalized/fake/ungapped/IGHD.fasta", {"IGHD1-1*01 source=ogrdb": "GGTATAGC"})

    _, findings = run_check(two_stage_germlines)

    misrouted = [f for f in findings if f["stage"] == "sources routing"]

    assert [(f["file"], f["kind"], f["names"]) for f in misrouted] == [("IGHD", "UNEXPLAINED", ["IGHD*02"])]


def test_format_count_report_marks_row_with_unexplained_loss_as_mismatch(two_stage_germlines):
    report = format_count_report(*run_check(two_stage_germlines))

    assert "MISMATCH sources->normalized" in report
    assert "rows matching end to end: 0/1; unexplained findings: 1" in report


def test_check_allele_counts_on_committed_ogrdb_species_reports_every_file():
    rows, findings = check_allele_counts()

    print(format_count_report(rows, findings))

    assert {row["species"] for row in rows} >= {"human", "macaque", "mouse"}
    assert all(row["src"] == row["kept"] + row["by_higher"] + row["collapsed"] for row in rows)


# --- issue #19 "Done when" fixture tests ---


def test_a45b8ac5_scenario_ighd_with_igd_constants_all_flagged(two_stage_germlines):
    """Simulates a45b8ac5: IGHD.fasta contained 20 IgD constant records alongside
    real D-REGION alleles.  Every IgD constant (name pattern IGHD*0x) must be
    flagged UNEXPLAINED at sources routing because _segment() routes them to 'C',
    not 'D'."""
    # 2 real D-REGION alleles + 20 IgD constant alleles (mimicking a45b8ac5)
    d_records: dict[str, str] = {f"IGHD{i}-1*01": "GGTATAGC" for i in range(1, 3)}
    igd_constants: dict[str, str] = {f"IGHD*{i:02d}": "A" * 1200 for i in range(1, 21)}
    write_fasta(two_stage_germlines / "sources/ogrdb/fake/IGHD.fasta", {**d_records, **igd_constants})
    write_fasta(
        two_stage_germlines / "normalized/fake/ungapped/IGHD.fasta",
        {f"IGHD{i}-1*01 source=ogrdb": "GGTATAGC" for i in range(1, 3)},
    )

    _, findings = run_check(two_stage_germlines)

    misrouted = [f for f in findings if f["stage"] == "sources routing" and f["file"] == "IGHD"]
    assert len(misrouted) == 1
    assert misrouted[0]["kind"] == "UNEXPLAINED"
    # All 20 IgD constant names must be flagged, none silently dropped
    assert set(misrouted[0]["names"]) == set(igd_constants.keys())


def test_extract_insert_blocks_semicolon_inside_quoted_field_does_not_truncate():
    """Semicolons inside quoted string fields must not terminate the INSERT block
    (issue #19: the old (.*?); regex stopped at the first ';' in the content)."""
    dump = (
        "INSERT INTO `gene_description` VALUES\n"
        "(1, 'IGHV1-2*01', 'desc; with semicolon', 'ATCG'),\n"
        "(2, 'IGHV1-3*01', 'normal desc', 'GCTA');"
        "\nSOME OTHER CONTENT;"
    )

    blocks = _extract_insert_blocks(dump, "gene_description")

    assert len(blocks) == 1, f"Expected 1 block, got {len(blocks)}"
    block = blocks[0]
    # Both rows must appear in the extracted block
    assert "IGHV1-2*01" in block
    assert "IGHV1-3*01" in block


def test_extract_insert_blocks_multiple_statements_each_extracted():
    """Multiple INSERT blocks in one dump file are all extracted."""
    dump = (
        "INSERT INTO `gene_description` VALUES (1, 'IGHV1-1*01', 'ACGT');\n"
        "INSERT INTO `gene_description` VALUES (2, 'IGHV1-2*01', 'GCTA');"
    )

    blocks = _extract_insert_blocks(dump, "gene_description")

    assert len(blocks) == 2


def test_extract_insert_blocks_unrelated_table_not_included():
    """INSERT blocks for other tables are not returned."""
    dump = (
        "INSERT INTO `other_table` VALUES (1, 'x; y');\n"
        "INSERT INTO `gene_description` VALUES (1, 'IGHV1-1*01', 'ACGT');"
    )

    blocks = _extract_insert_blocks(dump, "gene_description")

    assert len(blocks) == 1
    assert "IGHV1-1*01" in blocks[0]
