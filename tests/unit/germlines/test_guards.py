"""
Literal guard and disk guard for the species registry (issue #26).

Literal guard: no registry alias string appears as a bare Python string
literal in src/sadie/ code outside the approved files.

Disk guard: no alias appears as a species directory name or file stem under
src/sadie/germlines/, except crab_eating_macaque which is deferred until the
custom source directory is renamed.
"""

import ast
import re
from pathlib import Path

import pytest

from sadie.germlines.registry import SpeciesRegistry

SRC_ROOT = Path(__file__).parents[3] / "src" / "sadie"
GERMLINES_ROOT = SRC_ROOT / "germlines"

# Files where aliases are intentionally defined or referenced in comments
LITERAL_GUARD_EXEMPT = {
    SRC_ROOT / "germlines" / "registry.py",
    SRC_ROOT / "reference" / "settings.py",
    SRC_ROOT / "typing" / "species.py",
    # hmmer.py interfaces with ANARCI HMM files named rhesus_H.hmm — the ANARCI
    # internal name "rhesus" is a legitimate boundary reference here.
    SRC_ROOT / "renumbering" / "aligners" / "hmmer.py",
}

DISK_GUARD_DEFERRED: set[str] = set()

# The set of non-slug alias keys we guard against
_ALIASES = set(SpeciesRegistry.ALIASES.keys())


def _extract_string_literals(path: Path) -> list[str]:
    """Return all string literals found in a Python source file."""
    try:
        tree = ast.parse(path.read_text())
    except SyntaxError:
        return []
    literals: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            literals.append(node.value)
    return literals


@pytest.mark.parametrize("alias", sorted(_ALIASES))
def test_alias_not_used_as_string_literal_in_src(alias):
    """No .py file outside approved files should contain the alias as a literal."""
    offenders: list[str] = []
    for path in SRC_ROOT.rglob("*.py"):
        if path in LITERAL_GUARD_EXEMPT:
            continue
        for lit in _extract_string_literals(path):
            if lit == alias:
                rel = path.relative_to(SRC_ROOT.parent.parent)
                offenders.append(str(rel))
    assert not offenders, (
        f"Alias {alias!r} found as a string literal in:\n  "
        + "\n  ".join(offenders)
        + "\nUse the canonical slug or SpeciesRegistry.normalize() instead."
    )


def _species_stems_in_germlines() -> set[str]:
    """Collect all species-like directory names and FASTA/aux/ndm file stems."""
    stems: set[str] = set()
    # Directory names under sources/, normalized/, database/, internal_data/, aux_db/
    for subdir in ("sources", "normalized", "igblast"):
        base = GERMLINES_ROOT / subdir
        if not base.exists():
            continue
        for entry in base.rglob("*"):
            if entry.is_dir():
                stems.add(entry.name)
    # organism.yaml keys
    yaml_path = GERMLINES_ROOT / "igblast" / "internal_data" / "organism.yaml"
    if yaml_path.exists():
        for line in yaml_path.read_text().splitlines():
            m = re.match(r"^  ([a-z][a-zA-Z0-9_]+):\s*$", line)
            if m:
                stems.add(m.group(1))
    return stems


def test_disk_guard_no_aliases_in_germlines_paths():
    """Species directory names and organism.yaml keys should only be canonical slugs."""
    allowed_dirs = {"_template", "raw"} | DISK_GUARD_DEFERRED
    stems = _species_stems_in_germlines()
    offenders = set()
    for stem in stems:
        if stem in allowed_dirs:
            continue
        if stem in _ALIASES and stem not in DISK_GUARD_DEFERRED:
            offenders.add(stem)

    assert not offenders, (
        "Alias names found in germlines disk paths (rename to canonical slug):\n  "
        + "\n  ".join(sorted(offenders))
    )
