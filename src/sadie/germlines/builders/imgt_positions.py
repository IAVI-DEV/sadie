"""
IMGT Region Position Utilities
==============================

Helpers for deriving ungapped IMGT region positions from gapped V-gene sequences.
Positions are 0-based (inclusive) by default to match G3 API output.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from itertools import product
from typing import Dict, Iterable, Optional, Tuple

from sadie.germlines.builders.gapper import CODON_TABLE

# IMGT V gene regions in standard gapped coordinates (1-based, inclusive)
IMGT_V_REGIONS = {
    "FWR1": (1, 78),
    "CDR1": (79, 114),
    "FWR2": (115, 165),
    "CDR2": (166, 195),
    "FWR3": (196, 312),
}

GAP_CHARACTERS = {".", "-"}

# Conserved landmark codons: first gapped column in the standard layout.
# Some alignments (rat, dog, macaque, ...) carry extra gap columns, so their
# landmarks sit a few codons to the right of the standard columns.
CYS23_COLUMN, TRP41_COLUMN, CYS104_COLUMN = 67, 121, 310
CYS_CODONS, TRP_CODONS, TYR_CODONS = ("TGT", "TGC"), ("TGG",), ("TAT", "TAC")
AROMATIC_103_CODONS = (*TYR_CODONS, "TTT", "TTC", "CAT", "CAC")  # Tyr, Phe, His
# Residues 42-44 that make a Trp the CONSERVED-TRP 41 (W-[IV]-R-Q heavy, W-[YFL]-Q-Q light) and not
# Trp 39 of W-x-W-I-R-Q or a Trp at 42: hydrophobic 42 with the usual 43 and 44, or Gln 44
TRP41_CONTEXT = re.compile(r"[IVLFYM][RQLHP][QHK]|..Q")
TRP41_AFTER_TRP39_CONTEXT = re.compile(r"[IVLFYM][^P].")  # of W-x-W the second is Trp41 only as W-[IV]-R-Q
EXTRA_COLUMNS = range(0, 13, 3)  # the most any shipped alignment has is 12
FWR2_LENGTH = 51  # codons 39-55
MIN_EVIDENCE = 1.5  # landmarks, for a layout none of whose alleles has all three

Shifts = Tuple[int, int, int]  # extra columns in front of Cys23, Trp41, Cys104
RegionColumns = Dict[str, Tuple[int, int]]


def gap_layout(gapped_sequence: str) -> str:
    """Gap mask of a gapped sequence. Region bounds are a property of this layout, not of the bases."""
    return "".join("." if char in GAP_CHARACTERS else "N" for char in gapped_sequence)


def _ungapped(gapped: str) -> str:
    return "".join(char for char in gapped if char not in GAP_CHARACTERS)


def _landmark_evidence(sequence: str, shifts: Shifts) -> Tuple[float, float, float]:
    """Evidence for Cys23, Trp41 and Cys104 at these shifts: 1.0 each when the landmark is there."""

    def codon(column: int) -> str:
        return sequence[column - 1 : column + 2]

    cys23, trp41, cys104 = shifts
    after_trp = _ungapped(sequence[TRP41_COLUMN + trp41 + 2 :])[:9]
    context = "".join(CODON_TABLE.get(after_trp[i : i + 3], "X") for i in range(0, 9, 3))
    after_trp39 = _ungapped(sequence[: TRP41_COLUMN + trp41 - 1])[-6:-3] in TRP_CODONS
    pattern = TRP41_AFTER_TRP39_CONTEXT if after_trp39 else TRP41_CONTEXT
    trp41_evidence = codon(TRP41_COLUMN + trp41) in TRP_CODONS and bool(pattern.fullmatch(context))
    # a Cys in CDR3 or in a pseudogene is not 2nd-CYS, so it needs the Tyr two codons before (Y-x-C);
    # with 2nd-CYS mutated, the Y-Y/F/H in front of it is half a landmark
    cys104_column = CYS104_COLUMN + cys104
    before = _ungapped(sequence[: cys104_column - 1])
    if before[-6:-3] not in TYR_CODONS:
        cys104_evidence = 0.0
    elif codon(cys104_column) in CYS_CODONS:
        cys104_evidence = 1.0
    else:
        cys104_evidence = 0.5 * (before[-3:] in AROMATIC_103_CODONS)
    return float(codon(CYS23_COLUMN + cys23) in CYS_CODONS), float(trp41_evidence), cys104_evidence


def _fwr2_extra_columns(layout: str, shifts: Shifts) -> int:
    """Gap columns inside FWR2, limited to the extra columns the layout has after Trp41."""
    fwr2_start = IMGT_V_REGIONS["FWR2"][0] + shifts[1]
    occupied = [column for column, char in enumerate(layout[fwr2_start - 1 :], start=fwr2_start) if char != "."]
    if len(occupied) < FWR2_LENGTH:
        return 0
    gap_columns = occupied[FWR2_LENGTH - 1] - (IMGT_V_REGIONS["FWR2"][1] + shifts[1])
    return min(max(gap_columns, 0), max(shifts[2] - shifts[1], 0))


def alignment_region_columns(gapped_sequences: Iterable[str]) -> Dict[str, RegionColumns]:
    """
    IMGT V region bounds, as gapped columns (1-based, inclusive), for every gap layout of one alignment file.

    Alleles with the same gap layout get the same bounds. A layout takes the shifts on which most of its
    alleles show all three landmarks; ties (Trp39/Trp41, Y-C-C) go to the shifts most alleles of the whole
    file agree on. A layout whose alleles lack a landmark takes its best supported shifts, the file's most
    common ones among equals, and a layout with under 1.5 landmarks keeps the standard columns.
    A Trp counts as Trp41 only with its usual residues 42-44 or Gln 44 after it. A landmark the
    layout shows no trace of follows the layout's own evidenced landmarks, not the file.
    """
    by_layout: Dict[str, list] = defaultdict(list)
    for sequence in gapped_sequences:
        by_layout[gap_layout(sequence)].append(sequence.upper())
    candidates = list(product(EXTRA_COLUMNS, repeat=3))
    file_votes: Counter = Counter()
    layout_votes: Dict[str, Counter] = {}
    evidence: Dict[str, Dict[Shifts, Tuple[float, float, float]]] = {}
    for layout, sequences in by_layout.items():
        found = [(shifts, _landmark_evidence(sequence, shifts)) for sequence in sequences for shifts in candidates]
        layout_votes[layout] = Counter(shifts for shifts, scores in found if sum(scores) == 3)
        evidence[layout] = {
            shifts: max((scores for found_at, scores in found if found_at == shifts), key=sum) for shifts in candidates
        }
        file_votes.update(layout_votes[layout])

    def preference(shifts: Shifts) -> tuple:
        return file_votes[shifts], shifts[0] <= shifts[1] <= shifts[2], -sum(shifts)

    layout_shifts: Dict[str, Shifts] = {}
    fwr2_basis: Dict[str, Shifts] = {}  # the shifts a layout's FWR2 gap columns are read with
    for layout in by_layout:
        votes = layout_votes[layout]
        if votes:
            layout_shifts[layout] = max(votes, key=lambda shifts: (votes[shifts], *preference(shifts)))
            fwr2_basis[layout] = layout_shifts[layout]
            continue
        support = {shifts: sum(scores) for shifts, scores in evidence[layout].items()}
        # among equally supported shifts follow the file; a mutated 2nd-CYS takes the first Y-Y it can
        best = max(
            candidates,
            key=lambda shifts: (
                support[shifts],
                0 if support[shifts].is_integer() else -shifts[2],
                file_votes[shifts],
                -sum(shifts),
            ),
        )
        if support[best] < MIN_EVIDENCE:
            layout_shifts[layout] = fwr2_basis[layout] = (0, 0, 0)
            continue
        fwr2_basis[layout] = best

        def ends_on_cys(cys104: int, sequences: list = by_layout[layout]) -> bool:
            column = CYS104_COLUMN + cys104
            return 2 * sum(sequence[column - 1 : column + 2] in CYS_CODONS for sequence in sequences) > len(sequences)

        # a landmark this layout shows no trace of must not take a file shift beyond the layout's own
        # evidenced ones: it follows its nearest evidenced landmark, and a traceless 2nd-CYS keeps its column
        scores = (*evidence[layout][best][:2], evidence[layout][best][2] or ends_on_cys(best[2]))
        evidenced = [index for index, score in enumerate(scores) if score]
        shifts = list(best)
        for index in set(range(3)) - set(evidenced):
            if shifts[index] > max(best[i] for i in evidenced):
                shifts[index] = 0 if index == 2 else best[min(evidenced, key=lambda i: abs(i - index))]
        # without Y-x-C evidence the FWR3 end stays on a Cys codon that a smaller shift sits on
        smaller = [cys104 for cys104 in EXTRA_COLUMNS if cys104 < shifts[2] and ends_on_cys(cys104)]
        if evidence[layout][best][2] < 1 and smaller and not ends_on_cys(shifts[2]):
            shifts[2] = max(smaller)
        layout_shifts[layout] = (shifts[0], shifts[1], shifts[2])

    # where the extra columns after Trp41 sit is a property of the alignment: majority over its layouts
    fwr2_extra: Dict[Shifts, Counter] = defaultdict(Counter)
    for layout, shifts in fwr2_basis.items():
        fwr2_extra[shifts][_fwr2_extra_columns(layout, shifts)] += len(by_layout[layout])

    region_columns = {}
    for layout, (cys23, trp41, cys104) in layout_shifts.items():
        basis = fwr2_basis[layout]
        extra = max(fwr2_extra[basis].items(), key=lambda item: (item[1], -item[0]))[0]
        if not layout_votes[layout]:  # never widen FWR2 without evidence from the layout itself
            extra = min(extra, _fwr2_extra_columns(layout, basis))
        fwr2_end = IMGT_V_REGIONS["FWR2"][1] + trp41 + extra
        cdr2_end = fwr2_end + IMGT_V_REGIONS["CDR2"][1] - IMGT_V_REGIONS["FWR2"][1]
        region_columns[layout] = {
            "FWR1": (1, IMGT_V_REGIONS["FWR1"][1] + cys23),
            "CDR1": (IMGT_V_REGIONS["CDR1"][0] + cys23, IMGT_V_REGIONS["CDR1"][1] + trp41),
            "FWR2": (IMGT_V_REGIONS["FWR2"][0] + trp41, fwr2_end),
            "CDR2": (fwr2_end + 1, cdr2_end),
            "FWR3": (cdr2_end + 1, IMGT_V_REGIONS["FWR3"][1] + cys104),
        }
    return region_columns


def calculate_imgt_v_positions(
    gapped_sequence: str, *, zero_based: bool = True, region_columns: Optional[RegionColumns] = None
) -> Dict[str, Tuple[int, int]]:
    """
    Calculate ungapped IMGT region positions for V genes.

    Region bounds are anchored on the conserved Cys23, Trp41 and Cys104 codons,
    falling back to the standard IMGT columns when a landmark is absent.

    Parameters
    ----------
    gapped_sequence : str
        IMGT-gapped nucleotide sequence.
    zero_based : bool, optional
        If True, return 0-based positions (default). If False, return 1-based positions.
    region_columns : Dict[str, Tuple[int, int]], optional
        Bounds of this sequence's gap layout from alignment_region_columns() over its whole
        alignment file. Derived from this sequence alone if not provided.

    Returns
    -------
    Dict[str, Tuple[int, int]]
        Mapping of region name to (start, end) positions in ungapped sequence.
    """
    if not gapped_sequence:
        return {}

    pos_map: Dict[int, int] = {}
    ungapped_pos = 0

    for gapped_pos, char in enumerate(gapped_sequence, start=1):
        if char not in GAP_CHARACTERS:
            pos_map[gapped_pos] = ungapped_pos
            ungapped_pos += 1

    regions: Dict[str, Tuple[int, int]] = {}
    if region_columns is None:
        region_columns = alignment_region_columns([gapped_sequence])[gap_layout(gapped_sequence)]
    if any(not any(column in pos_map for column in range(start, end + 1)) for start, end in region_columns.values()):
        region_columns = IMGT_V_REGIONS  # a shifted region came out empty: keep the standard columns
    for region_name, (gapped_start, gapped_end) in region_columns.items():
        start_pos = None
        end_pos = None

        for gapped_pos in range(gapped_start, min(gapped_end, len(gapped_sequence)) + 1):
            if gapped_pos in pos_map:
                if start_pos is None:
                    start_pos = pos_map[gapped_pos]
                end_pos = pos_map[gapped_pos]

        if start_pos is not None and end_pos is not None:
            if zero_based:
                regions[region_name.lower()] = (start_pos, end_pos)
            else:
                regions[region_name.lower()] = (start_pos + 1, end_pos + 1)

    return regions


def derive_imgt_v_regions(
    gapped_sequence: str,
    ungapped_sequence: Optional[str] = None,
    *,
    zero_based: bool = True,
) -> Tuple[Dict[str, Tuple[int, int]], Dict[str, str]]:
    """
    Derive IMGT V-region positions and sequences from a gapped sequence.

    Parameters
    ----------
    gapped_sequence : str
        IMGT-gapped nucleotide sequence.
    ungapped_sequence : str, optional
        Ungapped nucleotide sequence. Derived from gapped_sequence if not provided.
    zero_based : bool, optional
        If True, return 0-based positions (default). If False, return 1-based positions.

    Returns
    -------
    Tuple[Dict[str, Tuple[int, int]], Dict[str, str]]
        Region positions and region nucleotide sequences.
    """
    positions = calculate_imgt_v_positions(gapped_sequence, zero_based=zero_based)
    if not positions:
        return {}, {}

    if ungapped_sequence is None:
        ungapped_sequence = gapped_sequence.replace(".", "").replace("-", "")
    ungapped_sequence = ungapped_sequence.upper()

    regions: Dict[str, str] = {}
    for region_name, (start, end) in positions.items():
        if zero_based:
            start_index = start
            end_index = end + 1
        else:
            start_index = max(start - 1, 0)
            end_index = end

        if start_index < len(ungapped_sequence):
            regions[region_name] = ungapped_sequence[start_index:end_index]

    return positions, regions
