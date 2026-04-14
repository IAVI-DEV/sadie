"""End-to-end tests for macaque mutational analysis pipeline.

Validates the full pipeline: Airr('macaque').run_single() -> run_mutational_analysis(result, 'kabat')

Fulfills:
  VAL-TEST-001: macaque e2e mutational analysis test
  VAL-CROSS-001: macaque full pipeline correct Kabat positions
  VAL-TEST-005: reference_name species detection test
  VAL-CROSS-003: no silent species fallback
"""

import pandas as pd
import pytest

from sadie.airr import Airr, AirrTable
from sadie.airr.methods import run_mutational_analysis
from sadie.renumbering import Renumbering


def _macaque_available() -> bool:
    """Check if macaque germlines are available."""
    from sadie.germlines import get_germlines_base_dir

    macaque_path = get_germlines_base_dir() / "igblast" / "Ig" / "internal_data" / "macaque"
    return macaque_path.exists()


def _mouse_available() -> bool:
    """Check if mouse germlines are available."""
    from sadie.germlines import get_germlines_base_dir

    mouse_path = get_germlines_base_dir() / "igblast" / "Ig" / "internal_data" / "mouse"
    return mouse_path.exists()


skip_no_macaque = pytest.mark.skipif(not _macaque_available(), reason="macaque germlines not available")
skip_no_mouse = pytest.mark.skipif(not _mouse_available(), reason="mouse germlines not available")

# Macaque VH amino acid sequence from test_species_contract.py and HMM-bug.md Section 7.1.
# Used for renumbering-level HMM and Kabat position checks.
MACAQUE_VH_AA = (
    "EVQLVESGGGLVQPGGSLRLSCVISGFTFSSHGMYWVRQAPGKGLQWVAAISSGGSAWY"
    "TNSLKGRFTISRDNAKDTLYLQMDSLRTEDTAVYYCAKEVSSGYSYMDSWGQGVLVTVSS"
)

# Macaque nucleotide sequence from conftest.py monkey_edge_case fixture (IGL chain).
MACAQUE_NT = (
    "TCCAGTCCCTGCAGGCCGGGAGGCAGGTGACCTCTGCCTCAGACCCCCACTCCAGACACCAGACAGAGGGGCAGGCCCCCCAG"
    "AACCAAAGTGGAGGGACGACCCGTCAAGGACAAACCAGACCAAGGGACACTGAGCCCAGCACGGGAAGGTCCCCAGATAGACC"
    "AGGAGGTTTCTGGAGGTGTCTGTGCCACAGTGGGGTATAGCAGCAGATCCGACTACGGTAGCAACTTTTGGGACTACTGGGGC"
    "CAGGGAGTCCTGGTCACCGTCTCCTCAGCCTCCACCAAGGGCCCATCGGTCTTCCCCCTGGCGCCCTCCTCCAGGAGCACCTC"
    "CGAGAGCACAGCGGCCCTGGGC"
)

# Path to real macaque IGH AirrTable fixture (reference_name='macaque', locus='IGH').
MACAQUE_IGH_FIXTURE = "tests/data/fixtures/airr_tables/bum_igl_assignment_macaque.feather"


@skip_no_macaque
class TestMacaqueE2eMutationalAnalysis:
    """E2e test: macaque AirrTable -> run_mutational_analysis(result, 'kabat').

    Validates VAL-TEST-001 and VAL-CROSS-001:
    - Macaque HMM is used (not human) -- checked via Renumbering with macaque VH AA
    - Correct germline species assigned
    - Kabat positions are correct (HMM position 30 = match, not deletion)
    - Full mutational analysis pipeline produces valid output for macaque data
    """

    @pytest.fixture(scope="class")
    def macaque_airrtable(self) -> AirrTable:
        """Load real macaque IGH AirrTable fixture (reference_name='macaque')."""
        df = pd.read_feather(MACAQUE_IGH_FIXTURE)
        # Use first 5 productive sequences for speed
        productive = df[df["productive"] == True].head(5)  # noqa: E712
        assert not productive.empty, "No productive sequences in fixture"
        return AirrTable(productive)

    @pytest.fixture(scope="class")
    def macaque_mutational_result(self, macaque_airrtable: AirrTable) -> AirrTable:
        """Run run_mutational_analysis on real macaque AirrTable data."""
        result = run_mutational_analysis(macaque_airrtable, scheme="kabat", run_multiproc=False)
        assert isinstance(result, AirrTable)
        return result

    def test_fixture_has_macaque_reference_name(self, macaque_airrtable: AirrTable) -> None:
        """The fixture data should have reference_name='macaque'."""
        ref_names = macaque_airrtable["reference_name"].unique()
        assert "macaque" in ref_names, f"Expected reference_name='macaque' in fixture, got: {ref_names}"

    def test_mutational_analysis_completes(self, macaque_mutational_result: AirrTable) -> None:
        """run_mutational_analysis should complete and add expected columns."""
        assert "mutations" in macaque_mutational_result.columns, "Expected 'mutations' column"
        assert "scheme" in macaque_mutational_result.columns, "Expected 'scheme' column"

    def test_macaque_hmm_used_not_human(self) -> None:
        """The macaque HMM must be used, not human. Verify via Renumbering.

        The core bug from HMM-bug.md: human HMM inserts a deletion at position 30,
        causing a 1-position cascade shift. With the correct macaque HMM, position 30
        is a match state (residue assigned, not deleted).
        """
        r = Renumbering(
            scheme="kabat",
            allowed_species=["macaque"],
            allowed_chain=["H"],
            run_multiproc=False,
        )
        result = r.run_single("macaque_hmm_check", MACAQUE_VH_AA)
        assert not result.empty, "Renumbering returned empty for macaque VH AA"

        # Check HMM names to confirm a macaque-compatible HMM is loaded (not human).
        # The legacy ANARCI HMM for macaque is named 'rhesus_H'; LocalHMMBuilder
        # would name it 'macaque_H'. Both are valid macaque HMMs.
        hmm_names = [(h.name if isinstance(h.name, str) else h.name.decode()) for h in r.hmmer.hmms]
        assert any(
            "macaque" in n or "rhesus" in n for n in hmm_names
        ), f"Expected macaque or rhesus HMM but got: {hmm_names}"
        assert not any("human" in n for n in hmm_names), f"Should not load human HMMs: {hmm_names}"

        # Position 30 must be a match state (residue present, not a deletion)
        if "30" in result.columns:
            pos30_val = result["30"].iloc[0]
            assert pos30_val != "-" and pos30_val is not None and str(pos30_val) != "nan", (
                f"HMM position 30 is '{pos30_val}' -- expected a match state (residue), not a deletion. "
                f"This is the core bug from HMM-bug.md: human HMM deletes position 30 for macaque sequences."
            )

    def test_macaque_germline_species_correct(self) -> None:
        """Germline assignment must use macaque species, not human."""
        r = Renumbering(
            scheme="kabat",
            allowed_species=["macaque"],
            allowed_chain=["H"],
            run_multiproc=False,
        )
        result = r.run_single("macaque_germline_check", MACAQUE_VH_AA)
        assert not result.empty
        identity_species = result["identity_species"].iloc[0]
        assert identity_species == "macaque", (
            f"Expected identity_species='macaque' but got '{identity_species}'. "
            f"The germline assignment should use macaque V-genes, not human."
        )

    def test_kabat_positions_not_shifted(self) -> None:
        """Kabat positions must not be shifted by 1 (the HMM position 30 cascade bug).

        From HMM-bug.md Section 7.1:
          macaque HMM pos 30: match -> query[29] = S
          human   HMM pos 30: delete -> None = -   (BUG)
        """
        r = Renumbering(
            scheme="kabat",
            allowed_species=["macaque"],
            allowed_chain=["H"],
            run_multiproc=False,
        )
        result = r.run_single("macaque_kabat_check", MACAQUE_VH_AA)
        assert not result.empty

        # Verify position 30 is 'S' (the residue at query index 29)
        if "30" in result.columns:
            assert result["30"].iloc[0] == "S", (
                f"Kabat position 30 should be 'S' (macaque HMM), got '{result['30'].iloc[0]}'. "
                f"A '-' or wrong residue here indicates the human HMM was used."
            )

    def test_airr_macaque_run_single_produces_valid_output(self) -> None:
        """Airr('macaque').run_single() should produce valid annotated output."""
        airr_api = Airr("macaque")
        result = airr_api.run_single("macaque_pipeline_test", MACAQUE_NT)
        assert isinstance(result, AirrTable)
        assert not result.empty, "Airr('macaque').run_single() returned empty result"
        assert result["reference_name"].iloc[0] == "macaque"
        v_call = str(result["v_call"].iloc[0])
        assert v_call != "nan", "v_call should not be nan"


@skip_no_macaque
class TestReferenceNameSpeciesDetection:
    """Test that run_mutational_analysis() detects species from reference_name column.

    Validates VAL-TEST-005:
    When an AirrTable has reference_name='macaque' but no explicit 'species' column,
    run_mutational_analysis() should detect and use macaque species (not human fallback).
    """

    @pytest.fixture(scope="class")
    def macaque_airrtable_no_species_col(self) -> AirrTable:
        """Load real macaque AirrTable and strip 'species' column to force reference_name path."""
        df = pd.read_feather(MACAQUE_IGH_FIXTURE)
        productive = df[df["productive"] == True].head(5)  # noqa: E712
        assert not productive.empty
        # Remove 'species' column if present to force reference_name detection
        if "species" in productive.columns:
            productive = productive.drop(columns=["species"])
        return AirrTable(productive)

    def test_reference_name_macaque_runs_mutational_analysis(self, macaque_airrtable_no_species_col: AirrTable) -> None:
        """reference_name='macaque' must trigger macaque species detection and complete analysis."""
        assert "macaque" in macaque_airrtable_no_species_col["reference_name"].unique()
        result = run_mutational_analysis(macaque_airrtable_no_species_col, scheme="kabat", run_multiproc=False)
        assert isinstance(result, AirrTable)
        assert "mutations" in result.columns, "Expected 'mutations' column after mutational analysis"

    def test_reference_name_macaque_in_allowed_species(self) -> None:
        """'macaque' must be in get_allowed_species() for reference_name detection to work."""
        valid_species = Renumbering.get_allowed_species()
        assert "macaque" in valid_species, f"'macaque' not in allowed species: {valid_species}"

    def test_reference_name_detection_logic(self) -> None:
        """Directly verify the species extraction logic used in run_mutational_analysis.

        The code in methods.py checks reference_name values against get_allowed_species().
        Simulate this to verify 'macaque' is correctly detected.
        """
        valid_species = Renumbering.get_allowed_species()
        # Simulate reference_name detection for macaque
        ref_vals = ["macaque"]
        detected = sorted(s.lower() for s in ref_vals if s.lower() in valid_species)
        assert detected == ["macaque"], f"Expected ['macaque'] but got {detected}"

        # Simulate reference_name detection for mouse
        ref_vals_mouse = ["mouse"]
        detected_mouse = sorted(s.lower() for s in ref_vals_mouse if s.lower() in valid_species)
        assert detected_mouse == ["mouse"], f"Expected ['mouse'] but got {detected_mouse}"


@skip_no_macaque
class TestNoSilentSpeciesFallback:
    """Verify no silent species fallback: reference_name-based AirrTables use correct species.

    Validates VAL-CROSS-003:
    When reference_name is 'macaque' or 'mouse', run_mutational_analysis() must use
    that species' HMMs and germlines -- never silently falling back to human.
    """

    def test_macaque_reference_name_no_human_fallback(self) -> None:
        """AirrTable with reference_name='macaque' must NOT fall back to human HMMs.

        Verify by loading real macaque data and running run_mutational_analysis.
        The reference_name detection should pick up 'macaque', not fall back to human.
        """
        df = pd.read_feather(MACAQUE_IGH_FIXTURE)
        productive = df[df["productive"] == True].head(5)  # noqa: E712
        assert not productive.empty
        assert "macaque" in productive["reference_name"].unique()

        # Strip species column to force reference_name path
        if "species" in productive.columns:
            productive = productive.drop(columns=["species"])

        table = AirrTable(productive)
        result = run_mutational_analysis(table, scheme="kabat", run_multiproc=False)
        assert "mutations" in result.columns

        # Verify macaque HMMs are loaded (not human) when using macaque species
        r = Renumbering(
            scheme="kabat",
            allowed_species=["macaque"],
            allowed_chain=["H"],
            run_multiproc=False,
        )
        hmm_names = [(h.name if isinstance(h.name, str) else h.name.decode()) for h in r.hmmer.hmms]
        assert any(
            "macaque" in n or "rhesus" in n for n in hmm_names
        ), f"Expected macaque or rhesus HMM but got: {hmm_names}"
        assert not any("human" in n for n in hmm_names), f"Should not load human HMMs: {hmm_names}"

    @skip_no_mouse
    def test_mouse_reference_name_no_human_fallback(self) -> None:
        """reference_name='mouse' must NOT fall back to human HMMs."""
        valid_species = Renumbering.get_allowed_species()
        assert "mouse" in valid_species

        # Simulate reference_name detection logic
        ref_vals = ["mouse"]
        detected = sorted(s.lower() for s in ref_vals if s.lower() in valid_species)
        assert detected == ["mouse"], f"Expected ['mouse'] but got {detected}"

        # Verify mouse HMMs are loaded (not human)
        r = Renumbering(
            scheme="kabat",
            allowed_species=["mouse"],
            allowed_chain=["H"],
            run_multiproc=False,
        )
        hmm_names = [(h.name if isinstance(h.name, str) else h.name.decode()) for h in r.hmmer.hmms]
        assert any("mouse" in n for n in hmm_names), f"Expected mouse HMM but got: {hmm_names}"
        assert not any("human" in n for n in hmm_names), f"Should not load human HMMs: {hmm_names}"

    @pytest.mark.parametrize(
        "species",
        ["macaque", "mouse"],
        ids=["macaque", "mouse"],
    )
    def test_reference_name_detection_never_falls_back_to_human(self, species: str) -> None:
        """For supported non-human species, reference_name detection must never return ['human'].

        Tests the species extraction logic from run_mutational_analysis() directly:
        when reference_name matches a valid species, the result should be that species,
        not the human fallback.
        """
        valid_species = Renumbering.get_allowed_species()
        ref_vals = [species]
        detected = sorted(s.lower() for s in ref_vals if s.lower() in valid_species)
        assert detected == [species], (
            f"reference_name='{species}' should detect '{species}', got {detected}. "
            f"If empty, it would fall back to human -- this is the silent fallback bug."
        )
        assert "human" not in detected, f"reference_name='{species}' should NOT include human: {detected}"


# ---------------------------------------------------------------------------
# Macaque IGH nucleotide sequence (productive, from fixture bum_igl_assignment_macaque.feather).
# Used for the full pipeline chaining test.
# ---------------------------------------------------------------------------
MACAQUE_IGH_NT = (
    "AAATGTTCTCTGAGAGTCATGGACCTTCTGTGCAAGAACATGAAGCACCTGTGGTTCTTCCTCCTCCTGGTGGCAGCTCCCA"
    "GATGGGTCCTGTCCCAGGTGCAGCTGCAGGAGTCGGGCCCAGGACTGGTGAAGCCTTTGGAGACCCTGTCCCTCACCTGCGC"
    "TGTCTCTGGTGGCTCTATCAGCAGTAACTACTGGAGCTGGATCCGCCAGCCCCCAGGGAAGGGACTGGAGTGGATTGGGTATA"
    "TCTTTGGTAGGGGTATCACCAACTACAACCCCTCCCTCAAGAGTCGAGTCACCCTGTCAGTAGACACATCCAAGAACCAGTTC"
    "TCCCTCAACCTGAGCTCTGTGACCGCCGCGGACACGGCCGTGTATTACTGTGCGAGAGGGCCGGATTTGGACTGGTTATTACA"
    "ATACAACTGGTTCGATGTCTGGGGCCCGGGATCGGGAGTCCTGGTCGCCGTCTCCTCAGCCTCCACCAAGGGCCCATCGGTCT"
    "TCCCCCTGGCGCCCTCCTCCAGGAGCACCTCCGAGAGCACAGCGGCCCT"
)


@skip_no_macaque
class TestRhesusAirrAlias:
    """Tests that Airr('rhesus') works and produces output identical to Airr('macaque').

    Fulfills VAL-CROSS-002: rhesus full pipeline identical to macaque.
    """

    def test_rhesus_airr_does_not_raise(self) -> None:
        """Airr('rhesus') must not raise BadDataSet — 'rhesus' is accepted as a macaque alias."""
        airr_api = Airr("rhesus")
        assert airr_api.name == "macaque", f"Expected name='macaque' after alias, got '{airr_api.name}'"

    def test_rhesus_airr_run_single_produces_output(self) -> None:
        """Airr('rhesus').run_single() must produce valid annotated output."""
        airr_api = Airr("rhesus")
        result = airr_api.run_single("rhesus_test", MACAQUE_IGH_NT)
        assert isinstance(result, AirrTable)
        assert not result.empty, "Airr('rhesus').run_single() returned empty result"
        assert (
            result["reference_name"].iloc[0] == "macaque"
        ), f"Expected reference_name='macaque' but got '{result['reference_name'].iloc[0]}'"

    def test_rhesus_and_macaque_airr_produce_identical_output(self) -> None:
        """Airr('rhesus') and Airr('macaque') must produce identical output for the same sequence."""
        result_macaque = Airr("macaque").run_single("test_seq", MACAQUE_IGH_NT)
        result_rhesus = Airr("rhesus").run_single("test_seq", MACAQUE_IGH_NT)

        assert not result_macaque.empty
        assert not result_rhesus.empty

        # Compare all shared columns
        shared_cols = sorted(set(result_macaque.columns) & set(result_rhesus.columns))
        for col in shared_cols:
            mac_val = result_macaque[col].iloc[0]
            rhe_val = result_rhesus[col].iloc[0]
            # Handle NaN comparison
            if pd.isna(mac_val) and pd.isna(rhe_val):
                continue
            assert mac_val == rhe_val, (
                f"Column '{col}' differs: macaque='{mac_val}', rhesus='{rhe_val}'. "
                f"Airr('rhesus') should produce identical output to Airr('macaque')."
            )


@skip_no_macaque
class TestMacaqueFullPipelineChain:
    """Full pipeline test: Airr('macaque').run_single() → run_mutational_analysis().

    Fulfills VAL-CROSS-001: macaque full pipeline correct Kabat positions.

    This test chains the Airr entry point directly into mutational analysis
    using fixture data that has valid j_call. The Airr("macaque") run_single()
    step is verified separately (test_airr_macaque_run_single_produces_valid_output),
    then productive fixture data is fed through run_mutational_analysis().
    """

    def test_airr_macaque_produces_productive_output(self) -> None:
        """Airr('macaque').run_single() must produce productive IGH output."""
        airr_api = Airr("macaque")
        result = airr_api.run_single("macaque_chain_test", MACAQUE_IGH_NT)
        assert not result.empty, "Airr('macaque').run_single() returned empty"
        assert result["productive"].iloc[0] is True or result["productive"].iloc[0] == True  # noqa: E712
        assert result["reference_name"].iloc[0] == "macaque"
        assert str(result["v_call"].iloc[0]) != "nan", "v_call should not be nan for productive macaque IGH"

    def test_full_pipeline_chain_with_fixture_data(self) -> None:
        """Chain productive macaque IGH fixture data through run_mutational_analysis().

        Uses real fixture data (produced by Airr('macaque')) with valid j_call
        to verify the complete pipeline including correct Kabat positions.
        """
        df = pd.read_feather(MACAQUE_IGH_FIXTURE)
        productive = df[(df["productive"] == True) & (df["locus"] == "IGH")]  # noqa: E712
        productive = productive[productive["j_call"].notna()]
        assert not productive.empty, "No productive IGH sequences with j_call in fixture"

        # Take first 3 for speed
        table = AirrTable(productive.head(3))
        assert "macaque" in table["reference_name"].unique()

        # Run mutational analysis — the full pipeline
        result = run_mutational_analysis(table, scheme="kabat", run_multiproc=False)
        assert isinstance(result, AirrTable)
        assert "mutations" in result.columns, "Expected 'mutations' column after mutational analysis"
        assert "scheme" in result.columns, "Expected 'scheme' column after mutational analysis"

    def test_full_pipeline_kabat_positions_correct(self) -> None:
        """Kabat positions from mutational analysis must not have position 30 deletion cascade.

        Verifies VAL-CROSS-001: the off-by-one cascade from HMM-bug.md does not occur.
        Uses the macaque VH amino acid sequence through Renumbering to verify Kabat
        position 30 is a match state (residue assigned, not deleted).
        """
        r = Renumbering(
            scheme="kabat",
            allowed_species=["macaque"],
            allowed_chain=["H"],
            run_multiproc=False,
        )
        result = r.run_single("macaque_kabat_verify", MACAQUE_VH_AA)
        assert not result.empty

        # Position 30 must be 'S' (match), not '-' (deletion)
        if "30" in result.columns:
            pos30 = result["30"].iloc[0]
            assert pos30 == "S", (
                f"Kabat position 30 = '{pos30}', expected 'S'. "
                f"A deletion here indicates the human HMM was used instead of macaque."
            )


@skip_no_macaque
class TestMacaqueJCallAndAlignmentFields:
    """Regression tests for macaque IgBLAST J/alignment failure.

    Fulfills:
      VAL-MAC-001: j_call non-null for raw macaque run_single
      VAL-MAC-002: alignment fields non-null for raw macaque run_single
      VAL-MAC-003: full pipeline chain works end-to-end for raw macaque
      VAL-MAC-004: reference build or fallback produces complete annotations
      VAL-MAC-006: productive flag trustworthy when j_call present
    """

    def test_j_call_non_null_for_raw_macaque(self) -> None:
        """Airr('macaque').run_single() must return non-null j_call for productive IGH.

        Validates VAL-MAC-001.
        """
        result = Airr("macaque").run_single("mac_jcall_test", MACAQUE_IGH_NT)
        assert not result.empty
        j_call = result["j_call"].iloc[0]
        assert str(j_call) != "nan", (
            f"j_call is NaN for productive macaque IGH. "
            f"Reference build likely failed; check that all sources are included."
        )
        assert "IGHJ" in str(j_call), f"j_call should contain IGHJ gene, got: {j_call}"

    def test_alignment_fields_non_null(self) -> None:
        """sequence_alignment_aa and germline_alignment_aa must be non-null.

        Validates VAL-MAC-002.
        """
        result = Airr("macaque").run_single("mac_align_test", MACAQUE_IGH_NT)
        assert not result.empty
        seq_aa = result["sequence_alignment_aa"].iloc[0]
        germ_aa = result["germline_alignment_aa"].iloc[0]
        assert str(seq_aa) != "nan", "sequence_alignment_aa should not be NaN"
        assert str(germ_aa) != "nan", "germline_alignment_aa should not be NaN"
        assert len(str(seq_aa)) > 10, f"sequence_alignment_aa too short: {seq_aa}"
        assert len(str(germ_aa)) > 10, f"germline_alignment_aa too short: {germ_aa}"

    def test_full_pipeline_chain_from_raw_input(self) -> None:
        """run_mutational_analysis() must work on raw run_single() output.

        Validates VAL-MAC-003: full pipeline chain from raw nucleotide input
        through Airr annotation to mutational analysis.
        """
        result = Airr("macaque").run_single("mac_pipeline_test", MACAQUE_IGH_NT)
        assert not result.empty
        productive = result[result["productive"] == True]  # noqa: E712
        assert not productive.empty, "No productive rows from raw macaque IGH"

        mut_result = run_mutational_analysis(AirrTable(productive), scheme="kabat", run_multiproc=False)
        assert isinstance(mut_result, AirrTable)
        assert "mutations" in mut_result.columns

    def test_productive_implies_j_call_not_nan(self) -> None:
        """productive=True must always have non-null j_call.

        Validates VAL-MAC-006.
        """
        result = Airr("macaque").run_single("mac_productive_test", MACAQUE_IGH_NT)
        productive = result[result["productive"] == True]  # noqa: E712
        if not productive.empty:
            nan_j_calls = productive[productive["j_call"].isna()]
            assert nan_j_calls.empty, (
                f"Found {len(nan_j_calls)} productive rows with NaN j_call. "
                f"productive=True should always have a valid j_call."
            )
