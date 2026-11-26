"""
Allele Aliases
==============

Old OGRDB labels and the current name of each, written per species by the OGRDB
downloader to ``sources/ogrdb/<species>/aliases.tsv``.

Reasons, checked against the FASTA files written with the alias file:
- renamed: the current name ships the sequence the label had
- revised: the current name ships another sequence
- retired: no current name ships

The label had the sequence parsed last for it. A label on two published
descriptions (mouse IGKV-KA5D, IGKV-YKPT) keeps one of the two.
"""

import csv
import functools
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


@functools.lru_cache(maxsize=None)
def read_aliases(path: Path) -> Dict[str, Tuple[str, str]]:
    """Return alias -> (current, reason); a missing or unreadable file has no aliases."""
    try:
        with open(path, newline="", encoding="utf-8") as f:
            return {row["alias"]: (row["current"], row["reason"]) for row in csv.DictReader(f, delimiter="\t")}
    except FileNotFoundError:
        logger.debug(f"No OGRDB alias file {path}; no aliases used")
        return {}
    except (OSError, UnicodeDecodeError, KeyError, csv.Error) as e:
        logger.warning(f"OGRDB alias file {path} not read ({type(e).__name__}); no aliases used")
        return {}
