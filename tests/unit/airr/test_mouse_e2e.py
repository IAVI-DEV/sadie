"""End-to-end tests for mouse mutational analysis pipeline.

Validates the full pipeline: Airr('mouse').run_fasta() -> run_mutational_analysis(result, 'kabat')

Fulfills:
  VAL-TEST-002: mouse e2e mutational analysis test
"""

from pathlib import Path

import pytest

from sadie.airr import Airr, AirrTable
from sadie.airr.methods import run_mutational_analysis
from sadie.renumbering import Renumbering


def _mouse_available() -> bool:
    """Check if mouse germlines are available."""
    from sadie.germlines import get_germlines_base_dir

    mouse_path = get_germlines_base_dir() / "igblast" / "Ig" / "internal_data" / "mouse"
    return mouse_path.exists()


skip_no_mouse = pytest.mark.skipif(not _mouse_available(), reason="mouse germlines not available")

# Mouse VH amino acid sequence from HMM-bug.md Section 7 and test_species_contract.py.
# Used for renumbering-level HMM and Kabat position checks.
MOUSE_VH_AA = "EVQLQQSGPELVKPGASVKISCKASGYTFTDYNMDWVKQSHGKSLEWIGDINPNNGGT" "IYNQKFKGKATLTVDKSSSTAYMELRSLTSEDTAVYYCAR"

# Path to real mouse VDJ FASTA fixture for full pipeline tests.
MOUSE_VDJ_FASTA = (
    Path(__file__).parent.parent.parent / "data" / "fixtures" / "fasta_inputs" / "mouse_vdj_validation.fasta"
)


@skip_no_mouse
class TestMouseE2eMutationalAnalysis:
    """E2e test: mouse AirrTable -> run_mutational_analysis(result, 'kabat').

    Validates VAL-TEST-002:
    - Mouse HMM is used (not human) -- checked via Renumbering with mouse VH AA
    - Correct germline species assigned
    - Kabat positions are correct (HMM position 30 = match, not deletion)
    - Full mutational analysis pipeline produces valid output for mouse data
    """

    @pytest.fixture(scope="class")
    def mouse_airrtable(self) -> AirrTable:
        """Run SADIE mouse annotation on real FASTA fixture to get AirrTable."""
        assert MOUSE_VDJ_FASTA.exists(), f"Fixture not found: {MOUSE_VDJ_FASTA}"
        airr_api = Airr("mouse")
        result = airr_api.run_fasta(str(MOUSE_VDJ_FASTA))
        assert isinstance(result, AirrTable)
        # Filter to productive IGH sequences for mutational analysis
        productive_igh = result[(result["productive"] == True) & (result["locus"] == "IGH")]  # noqa: E712
        assert not productive_igh.empty, "No productive IGH sequences in mouse fixture"
        return AirrTable(productive_igh)

    @pytest.fixture(scope="class")
    def mouse_mutational_result(self, mouse_airrtable: AirrTable) -> AirrTable:
        """Run run_mutational_analysis on mouse AirrTable data."""
        result = run_mutational_analysis(mouse_airrtable, scheme="kabat", run_multiproc=False)
        assert isinstance(result, AirrTable)
        return result

    def test_fixture_has_mouse_reference_name(self, mouse_airrtable: AirrTable) -> None:
        """The fixture data should have reference_name='mouse'."""
        ref_names = mouse_airrtable["reference_name"].unique()
        assert "mouse" in ref_names, f"Expected reference_name='mouse' in fixture, got: {ref_names}"

    def test_mutational_analysis_completes(self, mouse_mutational_result: AirrTable) -> None:
        """run_mutational_analysis should complete and add expected columns."""
        assert "mutations" in mouse_mutational_result.columns, "Expected 'mutations' column"
        assert "scheme" in mouse_mutational_result.columns, "Expected 'scheme' column"

    def test_mouse_hmm_used_not_human(self) -> None:
        """The mouse HMM must be used, not human. Verify via Renumbering.

        The core bug from HMM-bug.md: human HMM inserts a deletion at position 30,
        causing a 1-position cascade shift. With the correct mouse HMM, position 30
        is a match state (residue assigned, not deleted).
        """
        r = Renumbering(
            scheme="kabat",
            allowed_species=["mouse"],
            allowed_chain=["H"],
            run_multiproc=False,
        )
        result = r.run_single("mouse_hmm_check", MOUSE_VH_AA)
        assert not result.empty, "Renumbering returned empty for mouse VH AA"

        # Check HMM names to confirm mouse HMM is loaded
        hmm_names = [(h.name if isinstance(h.name, str) else h.name.decode()) for h in r.hmmer.hmms]
        assert any("mouse" in n for n in hmm_names), f"Expected mouse HMM but got: {hmm_names}"
        assert not any("human" in n for n in hmm_names), f"Should not load human HMMs: {hmm_names}"

        # Position 30 must be a match state (residue present, not a deletion)
        if "30" in result.columns:
            pos30_val = result["30"].iloc[0]
            assert pos30_val != "-" and pos30_val is not None and str(pos30_val) != "nan", (
                f"HMM position 30 is '{pos30_val}' -- expected a match state (residue), not a deletion. "
                f"This is the core bug from HMM-bug.md: human HMM deletes position 30 for mouse sequences."
            )

    def test_mouse_germline_species_correct(self) -> None:
        """Germline assignment must use mouse species, not human."""
        r = Renumbering(
            scheme="kabat",
            allowed_species=["mouse"],
            allowed_chain=["H"],
            run_multiproc=False,
        )
        result = r.run_single("mouse_germline_check", MOUSE_VH_AA)
        assert not result.empty
        identity_species = result["identity_species"].iloc[0]
        assert identity_species == "mouse", (
            f"Expected identity_species='mouse' but got '{identity_species}'. "
            f"The germline assignment should use mouse V-genes, not human."
        )

    def test_kabat_positions_not_shifted(self) -> None:
        """Kabat positions must not be shifted by 1 (the HMM position 30 cascade bug).

        From HMM-bug.md Section 7:
          mouse HMM pos 30: match -> query[29] = T
          human HMM pos 30: delete -> None = -   (BUG)

        With the correct mouse HMM, position 30 should be 'T' (the residue at query index 29).
        """
        r = Renumbering(
            scheme="kabat",
            allowed_species=["mouse"],
            allowed_chain=["H"],
            run_multiproc=False,
        )
        result = r.run_single("mouse_kabat_check", MOUSE_VH_AA)
        assert not result.empty

        # Verify position 30 is 'T' (the residue at query index 29 for this mouse sequence)
        if "30" in result.columns:
            assert result["30"].iloc[0] == "T", (
                f"Kabat position 30 should be 'T' (mouse HMM), got '{result['30'].iloc[0]}'. "
                f"A '-' or wrong residue here indicates the human HMM was used."
            )

    def test_full_pipeline_mutational_analysis_produces_valid_output(self, mouse_mutational_result: AirrTable) -> None:
        """Full pipeline from FASTA -> Airr annotation -> mutational analysis should succeed.

        Verifies the pipeline completes end-to-end with real mouse sequences and produces
        valid mutational analysis output with correct scheme annotation.
        """
        # Verify non-empty results
        assert not mouse_mutational_result.empty, "Mutational analysis result is empty"

        # All rows should have kabat scheme
        scheme_vals = mouse_mutational_result["scheme"].dropna().unique()
        assert len(scheme_vals) > 0, "No scheme values found — mutational analysis may have failed"
        assert "kabat" in scheme_vals, f"Expected 'kabat' scheme but got: {scheme_vals}"

    def test_mutations_count_matches_aa_alignment_diffs(self, mouse_mutational_result: AirrTable) -> None:
        """`mutations` count must match actual AA diffs between sequence_alignment_aa and germline_alignment_aa.

        Regression guard for the bug where mutations was inflated relative to visible AA differences
        (e.g., gap positions from outer-joined renumbering tables counted as mutations). Counts
        strict substitutions: positions where both sides are residues (not '-' or 'X') and differ.
        """
        for _, row in mouse_mutational_result.iterrows():
            mat = row.get("sequence_alignment_aa")
            germ = row.get("germline_alignment_aa")
            muts = row.get("mutations")
            assert isinstance(mat, str) and isinstance(germ, str), f"Non-string alignment for {row['sequence_id']}"
            assert len(mat) == len(germ), (
                f"{row['sequence_id']}: sequence_alignment_aa (len={len(mat)}) and "
                f"germline_alignment_aa (len={len(germ)}) must be the same length"
            )
            manual = sum(
                1 for a, b in zip(mat, germ) if a != b and a not in ("-", "X") and b not in ("-", "X")
            )
            muts_len = len(muts) if isinstance(muts, list) else 0
            assert muts_len == manual, (
                f"{row['sequence_id']}: mutations count ({muts_len}) != manual AA diff count ({manual}). "
                f"mutations={muts}"
            )

    def test_mouse_v_gene_assigned(self, mouse_airrtable: AirrTable) -> None:
        """Airr('mouse') should assign mouse V-genes (IGHV*), not human ones."""
        for _, row in mouse_airrtable.iterrows():
            v_call = str(row["v_call"])
            assert v_call != "nan", f"v_call should not be nan for sequence {row['sequence_id']}"
            assert (
                "IGHV" in v_call
            ), f"Expected mouse IGHV gene in v_call but got '{v_call}' for sequence {row['sequence_id']}"

    def test_mouse_reference_name_detection(self, mouse_airrtable: AirrTable) -> None:
        """reference_name='mouse' must trigger mouse species detection in run_mutational_analysis.

        Simulate the species detection logic from methods.py: when reference_name='mouse',
        the analysis should use mouse HMMs and not fall back to human.
        """
        valid_species = Renumbering.get_allowed_species()
        assert "mouse" in valid_species, f"'mouse' not in allowed species: {valid_species}"

        ref_vals = mouse_airrtable["reference_name"].dropna().unique()
        detected = sorted(s.lower() for s in ref_vals if s.lower() in valid_species)
        assert "mouse" in detected, (
            f"reference_name detection should find 'mouse' but got {detected}. "
            f"Available reference_names: {ref_vals.tolist()}"
        )
        assert "human" not in detected, f"reference_name detection should NOT include 'human': {detected}"
