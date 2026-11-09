from pathlib import Path

import pytest

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


def test_format_count_report_marks_row_with_unexplained_loss_as_mismatch(two_stage_germlines):
    report = format_count_report(*run_check(two_stage_germlines))

    assert "MISMATCH sources->normalized" in report
    assert "rows matching end to end: 0/1; unexplained findings: 1" in report


def test_check_allele_counts_on_committed_ogrdb_species_reports_every_file():
    rows, findings = check_allele_counts()

    print(format_count_report(rows, findings))

    assert {row["species"] for row in rows} >= {"human", "mouse"}
    assert all(row["src"] == row["kept"] + row["by_higher"] + row["collapsed"] for row in rows)
