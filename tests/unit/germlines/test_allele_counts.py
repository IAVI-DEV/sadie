import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from sadie.germlines.cli import germlines
from sadie.germlines.scripts.download_ogrdb import (
    OGRDBDownloader,
    _extract_insert_blocks,
)
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


@pytest.mark.parametrize(
    "blastdbcmd_path, db_fasta_built, row_ok",
    [(None, False, True), ("/usr/bin/blastdbcmd", False, True), ("/usr/bin/blastdbcmd", True, False)],
)
def test_check_allele_counts_passes_when_every_source_allele_is_accounted_for(
    two_stage_germlines, monkeypatch, blastdbcmd_path, db_fasta_built, row_ok
):
    monkeypatch.setattr("sadie.germlines.scripts.validate.shutil.which", lambda _: blastdbcmd_path)
    write_fasta(
        two_stage_germlines / "sources/ogrdb/fake/IGHV.fasta", {"IGHV1-1*01": "ACGTACGTAC", "IGHV1-2*01": "GGGGCCCCAA"}
    )
    if db_fasta_built:
        write_fasta(
            two_stage_germlines / "igblast/database/fake/fake_V.fasta",
            {"IGHV1-1*01": "ACGTACGTAC", "IGHV1-2*01": "GGGGCCCCAA"},
        )

    rows, findings = run_check(two_stage_germlines)

    assert rows[0]["ok"] is row_ok
    assert ([f for f in findings if f["kind"] == "UNEXPLAINED"] == []) is row_ok


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


def test_germlines_status_exits_nonzero_on_mismatch_row_without_findings(two_stage_germlines, monkeypatch):
    rows, _ = run_check(two_stage_germlines)
    rows[0]["ok"] = False
    monkeypatch.setattr("sadie.germlines.scripts.validate.check_allele_counts", lambda: (rows, []))

    result = CliRunner().invoke(germlines, ["status"])

    assert "unexplained findings: 0" in result.output
    assert result.exit_code == 1


def test_check_allele_counts_on_committed_ogrdb_species_reports_every_file():
    rows, findings = check_allele_counts()

    print(format_count_report(rows, findings))

    assert {row["species"] for row in rows} >= {"human", "macaque", "mouse"}
    assert all(row["src"] == row["kept"] + row["by_higher"] + row["collapsed"] for row in rows)
    assert [f["species"] for f in findings if f["stage"] == "ndm.imgt FWR3 end"] == []


@pytest.mark.parametrize("fwr3_end, flagged", [(6, []), (9, [["IGHV1-1*01"]])])
def test_check_allele_counts_flags_species_whose_fwr3_ends_miss_second_cys(two_stage_germlines, fwr3_end, flagged):
    write_fasta(two_stage_germlines / "normalized/fake/ungapped/IGHV.fasta", {"IGHV1-1*01 source=ogrdb": "AAATGTAAA"})
    ndm = two_stage_germlines / "igblast/Ig/internal_data/fake/fake.ndm.imgt"
    ndm.parent.mkdir(parents=True)
    ndm.write_text(f"IGHV1-1*01\t1\t1\t1\t1\t1\t1\t1\t1\t1\t{fwr3_end}\tVH\t0\n")

    _, findings = run_check(two_stage_germlines)

    assert [f["names"] for f in findings if f["stage"] == "ndm.imgt FWR3 end"] == flagged


@pytest.mark.parametrize("partial_gapped_v", ["." * 78 + "CAG" * 78, "CAG" * 60], ids=["fwr1-all-gaps", "ends-in-cdr2"])
def test_check_allele_counts_expects_no_ndm_row_only_for_partial_v_allele(two_stage_germlines, partial_gapped_v):
    gapped_v = {"IGHV1-1*01 source=ogrdb": partial_gapped_v, "IGHV1-2*01 source=vdjbase": "CAG" * 104}
    write_fasta(two_stage_germlines / "normalized/fake/gapped/IGHV.fasta", gapped_v)
    write_fasta(two_stage_germlines / "igblast/database/fake/fake_V.fasta", {"IGHV1-1*01": "CAG", "IGHV1-2*01": "CAG"})
    ndm = two_stage_germlines / "igblast/Ig/internal_data/fake/fake.ndm.imgt"
    ndm.parent.mkdir(parents=True)
    ndm.write_text("")

    _, findings = run_check(two_stage_germlines)

    ndm_findings = [(f["kind"], f["names"]) for f in findings if f["stage"] == "database V->ndm.imgt"]
    assert ndm_findings == [("EXPECTED", ["IGHV1-1*01"]), ("UNEXPLAINED", ["IGHV1-2*01"])]


@pytest.mark.parametrize(
    "release, api_count, expected_findings",
    [
        ("release-23947887", 4, [("EXPECTED", ["IGKV0-KA5D*00", "IGKV0-YKPT*00"])]),
        ("release-23947887", 5, [("EXPECTED", ["IGKV0-KA5D*00", "IGKV0-YKPT*00"]), ("UNEXPLAINED", ["1 records"])]),
        ("release-1", 4, [("UNEXPLAINED", ["2 records"])]),
    ],
    ids=["listed-names-cover-the-shortfall", "shortfall-beyond-listed-names", "another-release-guard"],
)
def test_check_allele_counts_expects_api_shortfall_only_from_listed_repeated_names(
    tmp_path, release, api_count, expected_findings
):
    write_fasta(tmp_path / "sources/ogrdb/mouse/IGKV.fasta", {"IGKV0-KA5D*00": "ACGT", "IGKV0-YKPT*00": "GGCC"})
    version = {"version": release, "allele_counts": {"mouse": {"IGKV": {"api": api_count}}}}
    (tmp_path / "sources/ogrdb/VERSION.json").write_text(json.dumps(version))

    _, findings = run_check(tmp_path)

    assert [(f["kind"], f["names"]) for f in findings if f["stage"] == "provider->sources"] == expected_findings


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


def test_extract_insert_blocks_warns_on_unterminated_statement(caplog):
    dump = "INSERT INTO gene_description VALUES (1);\nINSERT INTO gene_description VALUES (2)"

    blocks = _extract_insert_blocks(dump, "gene_description")

    assert blocks == ["(1)"]
    assert "Unterminated INSERT INTO gene_description" in caplog.text


def gene_description_dump(
    name, locus, sequence, coding_seq_imgt, gene_start, gene_end, row_id=1, set_status="published"
):
    values = ["NULL"] * 46
    values[0], values[1], values[8], values[9] = str(row_id), f"'{name}'", f"'{locus}'", f"'{name[3]}'"
    values[16], values[17], values[41] = f"'{sequence}'", f"'{coding_seq_imgt}'", "'Homo sapiens'"
    values[44], values[45] = gene_start, gene_end
    dump = f"INSERT INTO `gene_description` VALUES ({','.join(values)});"
    if set_status:
        germline_set = [str(row_id), *["NULL"] * 6, f"'{set_status}'"]
        dump += f"\nINSERT INTO `germline_set` VALUES ({','.join(germline_set)});"
        dump += f"\nINSERT INTO `gene_descriptions_germline_sets` VALUES ({row_id},{row_id});"
    return dump


def parse_dump_to_fasta(tmp_path, dump):
    (tmp_path / "dump.sql").write_text(dump)
    downloader = OGRDBDownloader(output_dir=tmp_path / "out", cache_dir=tmp_path / "cache")
    downloader._process_sql_dump(tmp_path / "dump.sql", ["human"])
    return {path.name: path.read_text() for path in (tmp_path / "out").rglob("*.fasta")}


@pytest.mark.parametrize(
    "name, gene_start, gene_end",
    [("IGHV1-1*01", "5", "10"), ("IGHV1-1*01", "NULL", "NULL"), ("IGHD1-1*01", "5", "10"), ("IGHC*01", "1", "14")],
    ids=[
        "gene_start_and_gene_end",
        "degapped_coding_seq_imgt_when_coordinates_missing",
        "d_segment",
        "c_segment_spliced_coding_when_coordinates_span_introns",
    ],
)
def test_process_sql_dump_writes_coding_region_not_full_genomic_sequence(tmp_path, name, gene_start, gene_end):
    dump = gene_description_dump(name, "IGH", "TTTTCAGGTGAAAA", "CAG...GTG", gene_start, gene_end)

    fastas = parse_dump_to_fasta(tmp_path, dump)

    assert fastas[f"{name[:4]}.fasta"] == f">{name}\nCAGGTG\n"


def test_process_sql_dump_skips_t_cell_receptor_loci(tmp_path):
    dump = gene_description_dump("TRBV19*01", "TRB", "TTTTCAGGTGAAAA", "CAG...GTG", "5", "10")

    assert parse_dump_to_fasta(tmp_path, dump) == {}


@pytest.mark.parametrize(
    "older_set, current_set, expected",
    [
        ("superceded", "published", ">IGHV1-1*01\nCAGGTG\n"),
        ("superceded", "superceded", None),
        (None, None, None),
    ],
    ids=["superseded_release_then_published_set_member", "member_of_superseded_sets_only", "in_no_germline_set"],
)
def test_process_sql_dump_keeps_only_members_of_a_published_germline_set(tmp_path, older_set, current_set, expected):
    older = gene_description_dump("IGHV1-1*01", "IGH", "CAGGT", "CAG...GT", "1", "5", 1, older_set)
    current = gene_description_dump("IGHV1-1*01", "IGH", "TTTTCAGGTGAAAA", "CAG...GTG", "5", "10", 2, current_set)

    fastas = parse_dump_to_fasta(tmp_path, older + "\n" + current)

    assert fastas.get("IGHV.fasta") == expected


@pytest.mark.parametrize(
    "archive, api_sets, expected",
    [
        ({"IGKV-AAAA": "ACGT"}, [{"IGKV0-AAAA*00": "ACGT"}], [("IGKV0-AAAA*00", "ACGT", "ACGT")]),
        ({"IGKV1-1*01": "ACGT"}, [{"IGKV1-1*01": "ACGTA"}], [("IGKV1-1*01", "ACGTA", "ACGTA")]),
        (
            {"IGKV1-1*01": "ACGT"},
            [{"IGKV1-2*01": "GGGG"}],
            [("IGKV1-1*01", "ACGT", "ACGT."), ("IGKV1-2*01", "GGGG", "GGGG")],
        ),
        (
            {},
            [{"IGKV0-AAAA*00": "ACGT"}, {"IGKV0-BBBB*00": "ACGT", "IGKV0-AAAA*00": "TTTT"}],
            [("IGKV0-AAAA*00", "ACGT", "ACGT"), ("IGKV0-BBBB*00", "ACGT", "ACGT")],
        ),
    ],
    ids=[
        "archive_label_replaced_by_api_name_with_same_sequence",
        "archive_record_replaced_by_api_record_with_same_name",
        "archive_record_absent_from_api_kept",
        "earlier_api_set_record_kept",
    ],
)
def test_supplement_from_api_ships_each_allele_once_under_its_api_name(
    tmp_path, monkeypatch, archive, api_sets, expected
):
    downloader = OGRDBDownloader(output_dir=tmp_path / "out", cache_dir=tmp_path / "cache")
    write_fasta(tmp_path / "out" / "human" / "IGKV.fasta", archive)
    write_fasta(tmp_path / "out" / "human" / "IGKV_gapped.fasta", {n: s + "." for n, s in archive.items()})
    sets = [{"germline_set_id": str(i), "locus": "IGK"} for i in range(len(api_sets))]
    monkeypatch.setattr(downloader, "get_germline_sets", lambda _: sets)
    monkeypatch.setattr(
        downloader,
        "get_germline_set_fasta",
        lambda set_id, gapped=False: "".join(f">{n}\n{s}\n" for n, s in api_sets[int(set_id)].items()),
    )

    downloader.supplement_from_api(["human"])

    out = tmp_path / "out" / "human"
    gapped = dict(downloader.parse_fasta((out / "IGKV_gapped.fasta").read_text()))
    assert [(n, s, gapped[n]) for n, s in downloader.parse_fasta((out / "IGKV.fasta").read_text())] == expected


@pytest.mark.parametrize(
    "failing, message",
    [
        ("sets", "germline sets"),
        ("set_fasta", "set 7"),
        ("archive", "Failed to download OGRDB archive"),
        (None, None),
    ],
)
def test_download_replaces_fasta_only_when_archive_and_api_both_succeed(tmp_path, monkeypatch, failing, message):
    from urllib.error import URLError

    from sadie.germlines.scripts import download_ogrdb

    downloader = OGRDBDownloader(output_dir=tmp_path / "out", cache_dir=tmp_path / "cache")
    (tmp_path / "cache" / "ogrdb_archive.tgz").write_bytes(b"cached")
    on_disk = tmp_path / "out" / "human" / "IGHV.fasta"
    on_disk.parent.mkdir(parents=True)
    on_disk.write_text(">IGHV1-1*01\nAAAA\n>IGHV1-2*01\nCCCC\n")

    def unreachable(*args, **kwargs):
        raise URLError("offline")

    def archive_pass(sql_file, species):
        (downloader.output_dir / "human").mkdir(parents=True)
        (downloader.output_dir / "human" / "IGHV.fasta").write_text(">IGHV1-1*01\nAAAA\n")

    monkeypatch.setattr(downloader, "_get_latest_zenodo_record", lambda: ("1", "http://zenodo.invalid/a.tgz", "v1"))
    monkeypatch.setattr(download_ogrdb, "urlretrieve", unreachable if failing == "archive" else lambda *a, **k: None)
    monkeypatch.setattr(downloader, "_extract_archive", lambda archive, target: (target / "dump.sql").write_text(""))
    monkeypatch.setattr(downloader, "_process_sql_dump", archive_pass)
    sets = [{"germline_set_id": "7", "locus": "IGH"}]
    monkeypatch.setattr(downloader, "get_germline_sets", unreachable if failing == "sets" else lambda _: sets)
    api_fasta = ">IGHV1-1*01\nAAAA\n>IGHV1-3*01\nGGGG\n"
    monkeypatch.setattr(
        downloader, "get_germline_set_fasta", unreachable if failing == "set_fasta" else lambda *a, **k: api_fasta
    )

    if failing:
        with pytest.raises(RuntimeError, match=message):
            downloader.download(["human"])
        assert on_disk.read_text() == ">IGHV1-1*01\nAAAA\n>IGHV1-2*01\nCCCC\n"
    else:
        downloader.download(["human"])
        assert on_disk.read_text() == ">IGHV1-1*01\nAAAA\n>IGHV1-3*01\nGGGG\n"
    assert downloader.output_dir == tmp_path / "out"
