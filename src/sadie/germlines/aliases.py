"""
Allele Aliases
==============

Old OGRDB labels and the current name of each, written per species by the OGRDB
downloader to ``sources/ogrdb/<species>/aliases.tsv``.

Reasons:
- renamed: the current name holds the identical sequence
- revised: a later release of the same OGRDB description is current; its sequence changed
- retired: no published germline set lists the description; no current name
"""

import csv
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

ALIAS_FILE = "aliases.tsv"
COLUMNS = ("alias", "current", "reason")


def write_aliases(path: Path, aliases: Dict[str, Tuple[str, str]]) -> None:
    """Write alias -> (current, reason) rows, sorted by alias."""
    with open(path, "w", newline="") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        writer.writerow(COLUMNS)
        writer.writerows((alias, *aliases[alias]) for alias in sorted(aliases))


def read_aliases(path: Path) -> Dict[str, Tuple[str, str]]:
    """Return alias -> (current, reason); an absent file has no aliases."""
    if not path.exists():
        return {}
    with open(path, newline="") as f:
        return {row["alias"]: (row["current"], row["reason"]) for row in csv.DictReader(f, delimiter="\t")}


def resolve_alias(name: str, species: str, sources_dir: Path) -> Optional[str]:
    """Return the current OGRDB name for an old label when the sequence is unchanged, else None."""
    current, reason = read_aliases(Path(sources_dir) / "ogrdb" / species / ALIAS_FILE).get(name, ("", ""))
    if reason == "renamed":
        logger.warning(f"OGRDB {species} label {name} is now {current} (same sequence); using {current}")
        return current
    if reason:
        logger.warning(f"OGRDB {species} label {name} not resolved: {reason}, current release {current or 'none'}")
    return None
