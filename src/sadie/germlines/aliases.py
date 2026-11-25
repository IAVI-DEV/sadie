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
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

ALIAS_FILE = "aliases.tsv"
COLUMNS = ("alias", "current", "reason")


def write_aliases(path: Path, aliases: Dict[str, Tuple[str, str]]) -> None:
    """Write alias -> (current, reason) rows, sorted by alias."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        writer.writerow(COLUMNS)
        writer.writerows((alias, *aliases[alias]) for alias in sorted(aliases))


def read_aliases(path: Path) -> Dict[str, Tuple[str, str]]:
    """Return alias -> (current, reason); a missing or unreadable file has no aliases."""
    try:
        with open(path, newline="", encoding="utf-8") as f:
            return {row["alias"]: (row["current"], row["reason"]) for row in csv.DictReader(f, delimiter="\t")}
    except FileNotFoundError:
        return {}
    except (OSError, UnicodeDecodeError, KeyError, csv.Error) as e:
        logger.warning(f"OGRDB alias file {path} not read ({type(e).__name__}); no aliases used")
        return {}
