#!/usr/bin/env python3
import argparse
import collections
import json
import logging
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

import yaml

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

SOURCES_DIR = Path(__file__).parent.parent / "sources"

VALID_NUCLEOTIDES = set("ACGTNacgtn.")
IUPAC_AMBIGUOUS = set("RYSWKMBDHVryswkmbdhv")


def validate_fasta_header(header: str) -> tuple[bool, str]:
    if not header.startswith(">"):
        return False, "Header must start with '>'"
    if len(header) < 2:
        return False, "Header too short"
    return True, ""


def validate_sequence(seq: str) -> tuple[bool, str]:
    if not seq:
        return False, "Empty sequence"
    valid_chars = VALID_NUCLEOTIDES | IUPAC_AMBIGUOUS
    invalid = set(seq) - valid_chars
    if invalid:
        return False, f"Invalid characters: {invalid}"
    return True, ""


def validate_fasta_file(path: Path) -> tuple[bool, list[str]]:
    errors = []
    if not path.exists():
        return False, [f"File not found: {path}"]
    if path.stat().st_size == 0:
        return False, [f"Empty file: {path}"]

    try:
        content = path.read_text()
    except Exception as e:
        return False, [f"Read error: {e}"]

    lines = content.strip().split("\n")
    if not lines:
        return False, ["No content"]

    i = 0
    seq_count = 0
    while i < len(lines):
        if not lines[i].strip():
            i += 1
            continue
        header = lines[i].strip()
        valid, msg = validate_fasta_header(header)
        if not valid:
            errors.append(f"Line {i+1}: {msg}")
            i += 1
            continue

        seq_lines = []
        i += 1
        while i < len(lines) and not lines[i].startswith(">"):
            seq_lines.append(lines[i].strip())
            i += 1

        seq = "".join(seq_lines)
        valid, msg = validate_sequence(seq)
        if not valid:
            errors.append(f"Sequence for {header[:50]}: {msg}")
        seq_count += 1

    if seq_count == 0:
        errors.append("No sequences found")

    return len(errors) == 0, errors


def validate_structure(species_dir: Path) -> tuple[bool, list[str]]:
    errors = []
    if not species_dir.exists():
        return False, [f"Species directory not found: {species_dir}"]
    if not species_dir.is_dir():
        return False, [f"Not a directory: {species_dir}"]

    required_heavy = ["IGHV.fasta", "IGHD.fasta", "IGHJ.fasta"]
    for req in required_heavy:
        fpath = species_dir / req
        gapped = species_dir / req.replace(".fasta", "_gapped.fasta")
        if not fpath.exists() and not gapped.exists():
            errors.append(f"Missing required file: {req}")

    for fasta in species_dir.glob("*.fasta"):
        if not fasta.stat().st_mode & 0o444:
            errors.append(f"File not readable: {fasta.name}")

    return len(errors) == 0, errors


def validate_provider(provider: str, species: Optional[str] = None) -> tuple[bool, dict]:
    provider_dir = SOURCES_DIR / provider
    if not provider_dir.exists():
        return False, {"error": f"Provider directory not found: {provider_dir}"}

    results = {"provider": provider, "species": {}, "total_files": 0, "valid_files": 0}
    species_dirs = [provider_dir / species] if species else list(provider_dir.iterdir())

    for sp_dir in species_dirs:
        if not sp_dir.is_dir() or sp_dir.name.startswith("."):
            continue
        sp_name = sp_dir.name
        results["species"][sp_name] = {"files": {}, "valid": True}

        for fasta in sp_dir.glob("*.fasta"):
            results["total_files"] += 1
            valid, errors = validate_fasta_file(fasta)
            results["species"][sp_name]["files"][fasta.name] = {"valid": valid, "errors": errors}
            if valid:
                results["valid_files"] += 1
            else:
                results["species"][sp_name]["valid"] = False

    all_valid = results["valid_files"] == results["total_files"]
    return all_valid, results


def validate_all() -> tuple[bool, dict]:
    all_results = {"providers": {}, "summary": {"total": 0, "valid": 0}}
    all_valid = True

    for provider_dir in SOURCES_DIR.iterdir():
        if not provider_dir.is_dir() or provider_dir.name.startswith("."):
            continue
        provider = provider_dir.name
        valid, results = validate_provider(provider)
        all_results["providers"][provider] = results
        all_results["summary"]["total"] += results.get("total_files", 0)
        all_results["summary"]["valid"] += results.get("valid_files", 0)
        if not valid:
            all_valid = False

    return all_valid, all_results


def print_results(results: dict, verbose: bool = False):
    for provider, data in results.get("providers", {}).items():
        for sp_name, sp_data in data.get("species", {}).items():
            status = "✓" if sp_data["valid"] else "✗"
            print(f"{status} {provider}/{sp_name}")
            if verbose or not sp_data["valid"]:
                for fname, fdata in sp_data.get("files", {}).items():
                    fstatus = "✓" if fdata["valid"] else "✗"
                    print(f"    {fstatus} {fname}")
                    for err in fdata.get("errors", []):
                        print(f"        - {err}")

    summary = results.get("summary", {})
    print(f"\nSummary: {summary.get('valid', 0)}/{summary.get('total', 0)} files valid")


# ---------------------------------------------------------------------------
# Allele counts across pipeline stages:
# provider -> sources -> normalized -> database fasta -> BLAST db -> internal_data / aux, and reference.yml.
# Every delta is classified EXPECTED (a known rule), UNEXPLAINED (a loss or misroute) or INFO.

CHAINS, SEGMENTS = "HKL", "VDJC"
PRIORITY = ["vdjbase", "ogrdb", "imgt", "custom"]  # GermlineManager.DEFAULT_PROVIDERS order
D_REGION = re.compile(r"IGHD\d")  # providers/imgt.py D filter; IgD constants are IGHD*0x


def _fasta(path: Path) -> list[dict]:
    from Bio import SeqIO

    records = []
    if path.exists():
        for rec in SeqIO.parse(path, "fasta"):
            source = re.search(r"source=(\w+)", rec.description)
            seq = str(rec.seq).upper().replace(".", "").replace("-", "")
            records.append({"name": rec.id, "source": source.group(1) if source else None, "seq": seq})
    return records


def _segment(name: str) -> str:
    """Segment the downloader routes a name to (download_ogrdb.supplement_from_api)."""
    if re.match(r"IG[HKL]V", name):
        return "V"
    if re.match(r"IG[HKL]J", name):
        return "J"
    return "D" if re.match(r"IGHD(?!\*)", name) else "C"


def _rank(provider: Optional[str]) -> int:
    return PRIORITY.index(provider) if provider in PRIORITY else len(PRIORITY)


def _blast_ids(prefix: Path) -> Optional[list[str]]:
    # None  = blastdbcmd not on PATH (column shown as '-', not a failure)
    # []    = executable available but DB files absent or unreadable (flags all DB alleles as lost)
    if not shutil.which("blastdbcmd"):
        return None
    if not any(prefix.parent.glob(prefix.name + "*.nsq")):
        return []
    cmd = ["blastdbcmd", "-db", str(prefix), "-entry", "all", "-outfmt", "%a"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode:
        logger.warning("blastdbcmd %s returned %d: %s", prefix, result.returncode, result.stderr.strip())
        return []
    return [i.replace("lcl|", "") for i in result.stdout.split()]


def _check_species(
    base: Path, species: str, ogrdb_dir: Path, counts: dict, listed: list, rows: list, findings: list
) -> None:
    from sadie.germlines.builders.blast import BlastDBBuilder

    sanitize = BlastDBBuilder()._sanitize_seq_id
    unexplained_stages: dict[str, set] = collections.defaultdict(set)
    first_row = len(rows)

    def flag(stage: str, where: str, kind: str, names, what: str, segment: Optional[str] = None) -> None:
        names = list(names)
        if not names:
            return
        findings.append({"species": species, "stage": stage, "file": where, "kind": kind, "what": what, "names": names})
        if kind == "UNEXPLAINED":
            for name in names:
                unexplained_stages[f"IG{name[2]}{segment}" if segment else where].add(stage)

    def per_file(directory: Path) -> dict:
        return {(c, s): _fasta(directory / f"IG{c}{s}.fasta") for c in CHAINS for s in SEGMENTS}

    norm = per_file(base / "normalized" / species / "ungapped")
    normg = per_file(base / "normalized" / species / "gapped")
    src = per_file(ogrdb_dir)
    db_dir = base / "igblast" / "database" / species
    db = {s: _fasta(db_dir / f"{species}_{s}.fasta") for s in SEGMENTS}
    blast = {s: _blast_ids(db_dir / f"{species}_{s}") for s in SEGMENTS}
    internal_dir = base / "igblast" / "Ig" / "internal_data" / species
    internal = {r["name"] for r in _fasta(internal_dir / f"{species}_V.fasta")}
    ndm_path, aux_path = internal_dir / f"{species}.ndm.imgt", base / "igblast" / "aux_db" / f"{species}_gl.aux"
    ndm, aux = set(), set()
    if ndm_path.exists():
        ndm = {line.split("\t")[0] for line in ndm_path.read_text().splitlines() if line.strip()}
    if aux_path.exists():
        aux = {line.split()[0] for line in aux_path.read_text().splitlines() if line.strip() and line[0] != "#"}

    # normalized -> database fasta: chains combined, ids sanitized, duplicate ids suffixed (builders/blast.py)
    expected_ids: dict[str, list] = {}
    for s in SEGMENTS:
        seen: dict[str, int] = {}
        expected_ids[s] = []
        for c in CHAINS:
            for r in norm[(c, s)]:
                i = sanitize(r["name"])
                seen[i] = seen.get(i, -1) + 1
                expected_ids[s].append((c, r["name"], f"{i}_{seen[i]}" if seen[i] else i))
        have, want = {r["name"] for r in db[s]}, {i for _, _, i in expected_ids[s]}
        where, stage = f"{species}_{s}", "normalized->database"
        db_fasta = db_dir / f"{species}_{s}.fasta"
        # Check existence of the DB FASTA, not whether it has records: a zero-record file is a build
        # failure (should flag missing alleles), while a missing file means the DB hasn't been built yet.
        if db_fasta.exists():
            flag(stage, where, "UNEXPLAINED", sorted(want - have), "normalized alleles missing from database", s)
            flag(stage, where, "UNEXPLAINED", sorted(have - want), "database ids with no normalized allele", s)
            truncated = [f"{n} -> {i}" for _, n, i in expected_ids[s] if n != i]
            flag(stage, where, "EXPECTED", truncated, "ids over 50 chars truncated (builders/blast.py)")
        if blast[s] is not None:
            flag("database->blast", where, "UNEXPLAINED", sorted(have ^ set(blast[s])), "ids differ from BLAST db", s)
    misrouted_c = [r["name"] for r in db["C"] if _segment(r["name"]) == "D" and len(r["seq"]) < 200]
    misrouted_d = [r["name"] for r in db["D"] if _segment(r["name"]) != "D"]
    flag("database routing", f"{species}_C", "UNEXPLAINED", misrouted_c, "D-segment records inside the C database", "C")
    flag("database routing", f"{species}_D", "UNEXPLAINED", misrouted_d, "non-D records inside the D database", "D")

    # database V+D+J+C -> internal_data combined fasta; database V -> ndm.imgt; database J -> aux
    union: set = set()
    repeated = []
    for s in SEGMENTS:
        for name in (r["name"] for r in db[s]):
            if name in union:
                repeated.append(name)
            union.add(name)
    # Compare against internal_data whenever the directory exists (even if the combined fasta is empty).
    if internal_dir.exists():
        stage, where = "database->internal_data", f"{species}_V"
        for s in SEGMENTS:
            diff = sorted(i for i in union ^ internal if _segment(i) == s)
            flag(stage, where, "UNEXPLAINED", diff, "ids differ from union of V, D, J, C", s)
        flag(stage, where, "EXPECTED", repeated, "ids repeated across segment files, kept once")
    db_v, db_j = {r["name"] for r in db["V"]}, {r["name"] for r in db["J"]}
    gapped_v = {r["name"] for c in CHAINS for r in normg[(c, "V")]}
    no_gap = {i for _, n, i in expected_ids["V"] if n not in gapped_v}
    truncated_v = {i for _, n, i in expected_ids["V"] if n != i}
    # Check ndm.imgt whenever the ndm file exists (even if it's empty).
    if ndm_path.exists():
        stage, where, missing = "database V->ndm.imgt", ndm_path.name, db_v - ndm
        unannotated = missing - no_gap
        gapless, truncated = sorted(missing & no_gap), sorted(unannotated & truncated_v)
        flag(stage, where, "EXPECTED", gapless, "V alleles with no gapped sequence, so no annotation row")
        flag(stage, where, "UNEXPLAINED", truncated, "database id truncated, ndm keeps the full name", "V")
        flag(stage, where, "UNEXPLAINED", sorted(unannotated - truncated_v), "V alleles with no annotation row", "V")
        flag(stage, where, "UNEXPLAINED", sorted(ndm - db_v), "annotation rows naming no database V allele", "V")
    # Check aux whenever the aux file exists (even if it's empty).
    if aux_path.exists():
        stage, where = "database J->aux", aux_path.name
        flag(stage, where, "UNEXPLAINED", sorted(db_j - aux), "J alleles with no aux row", "J")
        flag(stage, where, "UNEXPLAINED", sorted(aux - db_j), "aux rows naming no database J allele", "J")

    for c in CHAINS:
        for s in SEGMENTS:
            fname = f"IG{c}{s}"
            src_recs, norm_recs, gapped_recs = src[(c, s)], norm[(c, s)], normg[(c, s)]
            if not (src_recs or norm_recs):
                continue
            src_names, norm_by_name = {r["name"] for r in src_recs}, {r["name"]: r for r in norm_recs}
            # provider -> sources, from the counts recorded in VERSION.json at download time
            api, written = counts.get(fname, {}).get("api"), counts.get(fname, {}).get("written")
            n_src, stage = len(src_recs), "provider->sources"
            if api is not None and n_src > api:
                flag(stage, fname, "UNEXPLAINED", [f"{n_src - api} records"], "not in the published API set")
            if api is not None and n_src < api:
                flag(stage, fname, "UNEXPLAINED", [f"{api - n_src} records"], "published API records missing")
            if written is not None and written != n_src:
                flag(
                    stage, fname, "UNEXPLAINED", [f"{n_src} now, {written} at download"], "file changed since download"
                )
            duplicates = [n for n, k in collections.Counter(r["name"] for r in src_recs).items() if k > 1]
            flag("sources", fname, "UNEXPLAINED", duplicates, "duplicate names in one file")
            misrouted = sorted(n for n in src_names if _segment(n) != s)
            flag("sources routing", fname, "UNEXPLAINED", misrouted, "name pattern says another segment")
            # sources -> normalized: GermlineManager keeps the first provider per name, then per identical
            # sequence — but deduplication is per file, not across chains/segments.
            by_seq: dict[str, dict] = {}
            for r in norm_recs:
                by_seq.setdefault(r["seq"], r)
            kept, by_higher, collapsed, rejected, lost, differ = 0, [], [], [], [], []
            for r in src_recs:
                n, winner = r["name"], norm_by_name.get(r["name"])
                if winner and winner["source"] == "ogrdb":
                    kept += 1
                elif winner:
                    (by_higher if _rank(winner["source"]) < _rank("ogrdb") else lost).append(
                        f"{n} (name held by {winner['source']})"
                    )
                    if winner["seq"] != r["seq"]:
                        differ.append(f"{n} (ogrdb {len(r['seq'])} nt, {winner['source']} {len(winner['seq'])} nt)")
                elif n in {r2["name"] for recs in norm.values() for r2 in recs}:
                    lost.append(f"{n} (filed under another segment)")
                elif r["seq"] in by_seq and _rank(by_seq[r["seq"]]["source"]) <= _rank("ogrdb"):
                    collapsed.append(f"{n} = {by_seq[r['seq']]['name']} ({by_seq[r['seq']]['source']})")
                elif s == "D" and not D_REGION.match(n):
                    rejected.append(n)
                else:
                    lost.append(n)
            stage = "sources->normalized"
            flag(stage, fname, "EXPECTED", by_higher, "name already supplied by a higher-priority provider")
            flag(stage, fname, "EXPECTED", collapsed, "identical sequence kept under an earlier name")
            flag(stage, fname, "EXPECTED", rejected, "rejected: not a D-REGION name")
            flag(stage, fname, "UNEXPLAINED", lost, "source alleles absent from normalized")
            flag(stage, fname, "INFO", differ, "same name, different sequence than the provider that won")
            phantom = [r["name"] for r in norm_recs if r["source"] == "ogrdb" and r["name"] not in src_names]
            flag(stage, fname, "UNEXPLAINED", phantom, "tagged ogrdb with no source record")
            gapped_names, stage = {r["name"] for r in gapped_recs}, "normalized ungapped<->gapped"
            ungapped_only_kind = "EXPECTED" if s == "V" else "UNEXPLAINED"
            flag(stage, fname, ungapped_only_kind, sorted(set(norm_by_name) - gapped_names), "alleles in ungapped only")
            flag(stage, fname, "UNEXPLAINED", sorted(gapped_names - set(norm_by_name)), "alleles in gapped only")
            unsourced = [g for g in listed if g[2] == c and _segment(g) == s and g not in src_names]
            flag("reference.yml->sources", fname, "UNEXPLAINED", unsourced, "listed under ogrdb with no source record")
            in_db = [i for cc, _, i in expected_ids[s] if cc == c]
            db_names, blast_names = {r["name"] for r in db[s]}, set(blast[s] or [])
            rows.append(
                {
                    "species": species,
                    "file": fname,
                    "api": api,
                    "src": n_src,
                    "kept": kept,
                    "by_higher": len(by_higher),
                    "collapsed": len(collapsed) + len(rejected),
                    "norm": len(norm_recs),
                    "db": sum(i in db_names for i in in_db) if db[s] else None,
                    "blast": sum(i in blast_names for i in in_db) if blast[s] is not None else None,
                    "ndm": sum(i in ndm for i in in_db) if s == "V" and ndm_path.exists() else None,
                    "aux": sum(i in aux for i in in_db) if s == "J" and aux_path.exists() else None,
                }
            )
    for row in rows[first_row:]:
        row["flags"] = sorted(unexplained_stages[row["file"]])
        row["ok"] = (
            not row["flags"]
            and row["src"] == row["kept"] + row["by_higher"] + row["collapsed"]
            and row["db"] in (None, row["norm"])
            and row["blast"] in (None, row["db"])
            and row["aux"] in (None, row["db"])
        )


def check_allele_counts(
    germlines_dir: Optional[Path] = None, reference_yml: Optional[Path] = None
) -> tuple[list[dict], list[dict]]:
    """Count alleles per OGRDB species and file at every pipeline stage. Returns (rows, findings)."""
    base = Path(germlines_dir) if germlines_dir else SOURCES_DIR.parent
    ref = Path(reference_yml) if reference_yml else Path(__file__).parents[2] / "reference" / "data" / "reference.yml"
    yml = yaml.safe_load(ref.read_text()) if ref.exists() else {}
    version_path = base / "sources" / "ogrdb" / "VERSION.json"
    counts = (json.loads(version_path.read_text()) if version_path.exists() else {}).get("allele_counts", {})
    rows: list[dict] = []
    findings: list[dict] = []

    # Enumerate species from the union of normalized dirs and ogrdb source dirs so that a deleted
    # normalized dir doesn't silently drop its source alleles from the report.
    ogrdb_sources = base / "sources" / "ogrdb"
    all_species: set[str] = set()
    normalized = base / "normalized"
    if normalized.exists():
        all_species.update(d.name for d in normalized.iterdir() if d.is_dir() and not d.name.startswith("."))
    if ogrdb_sources.exists():
        all_species.update(
            d.name for d in ogrdb_sources.iterdir() if d.is_dir() and not d.name.startswith(".") and d.name != "VERSION.json"
        )

    for sp_name in sorted(all_species):
        ogrdb_dir = ogrdb_sources / sp_name
        if ogrdb_dir.is_dir():
            listed = [g for names in ((yml.get(sp_name) or {}).get("ogrdb") or {}).values() for g in names or []]
            _check_species(base, sp_name, ogrdb_dir, counts.get(sp_name, {}), listed, rows, findings)
    return rows, findings


def format_count_report(rows: list[dict], findings: list[dict], max_names: int = 8) -> str:
    columns = ["file", "api", "src", "kept", "by_higher", "collapsed", "norm", "db", "blast", "ndm", "aux"]
    lines = []
    for species in dict.fromkeys(r["species"] for r in rows):
        lines += [species, "  " + "".join(f"{c:>10}" for c in columns) + "  verdict"]
        for r in (r for r in rows if r["species"] == species):
            cells = "".join(f"{'-' if r[c] is None else r[c]:>10}" for c in columns)
            lines.append(f"  {cells}  " + ("ok" if r["ok"] else " ".join(["MISMATCH", *r["flags"]])))
        for kind in ("UNEXPLAINED", "EXPECTED", "INFO"):
            for f in (f for f in findings if f["species"] == species and f["kind"] == kind):
                more = f" ... +{len(f['names']) - max_names}" if len(f["names"]) > max_names else ""
                lines.append(f"  {kind} [{f['stage']}] {f['file']}: {len(f['names'])} {f['what']}")
                lines.append("      " + ", ".join(f["names"][:max_names]) + more)
    unexplained = sum(f["kind"] == "UNEXPLAINED" for f in findings)
    lines.append(
        f"rows matching end to end: {sum(r['ok'] for r in rows)}/{len(rows)}; unexplained findings: {unexplained}"
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Validate germline FASTA files")
    parser.add_argument("--provider", help="Validate specific provider")
    parser.add_argument("--species", help="Validate specific species")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--file", help="Validate specific file")
    args = parser.parse_args()

    if args.file:
        path = Path(args.file)
        valid, errors = validate_fasta_file(path)
        if valid:
            print(f"✓ {path.name} is valid")
            sys.exit(0)
        else:
            print(f"✗ {path.name} has errors:")
            for err in errors:
                print(f"  - {err}")
            sys.exit(1)

    if args.provider:
        valid, results = validate_provider(args.provider, args.species)
        print_results({"providers": {args.provider: results}}, args.verbose)
    else:
        valid, results = validate_all()
        print_results(results, args.verbose)

    sys.exit(0 if valid else 1)


if __name__ == "__main__":
    main()
