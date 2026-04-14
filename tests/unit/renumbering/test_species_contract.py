"""Species contract tests for the Renumbering pipeline.

Verifies that every species accepted by Renumbering can flow through
the full pipeline: HMM loading -> hmmsearch -> numbering -> germline
assignment -- without silent fallback or empty results.

This catches naming mismatches like macaque/rhesus where one layer
uses a different species key than another.
"""
import pytest

from sadie.renumbering import Renumbering

# Representative VH sequences per species for testing.
# These are real germline-derived sequences that should number correctly.
SPECIES_TEST_SEQUENCES = {
    "human": (
        "EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTY"
        "YADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAKDQGAMGYWGQGTLVTVSS"
    ),
    "mouse": (
        "EVQLQQSGPELVKPGASVKISCKASGYTFTDYNMDWVKQSHGKSLEWIGDINPNNGGT"
        "IYNQKFKGKATLTVDKSSSTAYMELRSLTSEDTAVYYCAR"
    ),
    "macaque": (
        "EVQLVESGGGLVQPGGSLRLSCVISGFTFSSHGMYWVRQAPGKGLQWVAAISSGGSAWY"
        "TNSLKGRFTISRDNAKDTLYLQMDSLRTEDTAVYYCAKEVSSGYSYMDSWGQGVLVTVSS"
    ),
    "rhesus": (
        "EVQLVESGGGLVQPGGSLRLSCVISGFTFSSHGMYWVRQAPGKGLQWVAAISSGGSAWY"
        "TNSLKGRFTISRDNAKDTLYLQMDSLRTEDTAVYYCAKEVSSGYSYMDSWGQGVLVTVSS"
    ),
    "rabbit": (
        "QEQLVESGGGLVQPGESLRLSCAASGFTFDDYAMHWVRQAPGKGLEWVSGISWNSGSIG"
        "YADSVKGRFTISRDNAKNSLYLQMNSLRAEDTALYYCAKG"
    ),
    "rat": (
        "EVQLVESGGGLVQPKGSLKLSCAASGFTFSNYGMHWVRQAPGKGLEWVAYISSGSSTIY"
        "YPDTVKGRFTISRDNAKNTLYLQMSSLKSEDTAMYYCTR"
    ),
}


class TestSpeciesContract:
    """Verify every allowed species can complete the full renumbering pipeline."""

    def test_all_allowed_species_have_hmms(self):
        """Every species in get_allowed_species() must load at least one HMM."""
        for species in Renumbering.get_allowed_species():
            r = Renumbering(
                allowed_species=[species],
                allowed_chain=["H", "K", "L"],
                run_multiproc=False,
            )
            assert len(r.hmmer.hmms) > 0, (
                f"Species '{species}' loaded 0 HMMs -- it will silently fail."
            )

    @pytest.mark.parametrize(
        "species,seq",
        [(sp, seq) for sp, seq in SPECIES_TEST_SEQUENCES.items()],
        ids=list(SPECIES_TEST_SEQUENCES.keys()),
    )
    def test_species_produces_numbered_result(self, species, seq):
        """A representative VH sequence for each species must produce a non-empty result."""
        r = Renumbering(
            scheme="kabat",
            allowed_species=[species],
            allowed_chain=["H"],
            run_multiproc=False,
        )
        result = r.run_single(f"test_{species}", seq)
        assert not result.empty, (
            f"Renumbering returned empty result for species '{species}'"
        )

    @pytest.mark.parametrize(
        "species,seq",
        [(sp, seq) for sp, seq in SPECIES_TEST_SEQUENCES.items()],
        ids=list(SPECIES_TEST_SEQUENCES.keys()),
    )
    def test_species_gets_germline_assignment(self, species, seq):
        """Germline assignment must succeed (not None) for species with test sequences."""
        r = Renumbering(
            scheme="kabat",
            allowed_species=[species],
            allowed_chain=["H"],
            run_multiproc=False,
        )
        result = r.run_single(f"test_{species}", seq)
        assert not result.empty
        v_gene = result["v_gene"].iloc[0]
        assert v_gene is not None, (
            f"Species '{species}' got None v_gene -- germline assignment failed silently."
            f" Check that _SPECIES_ALIASES or all_germlines covers this species."
        )

    def test_macaque_uses_macaque_hmm_not_human(self):
        """Regression: macaque must use macaque HMMs, not silently fall back to human."""
        r = Renumbering(
            scheme="kabat",
            allowed_species=["macaque"],
            allowed_chain=["H"],
            run_multiproc=False,
        )
        hmm_names = [
            (h.name if isinstance(h.name, str) else h.name.decode())
            for h in r.hmmer.hmms
        ]
        assert any("macaque" in n for n in hmm_names), (
            f"Expected macaque HMM but got: {hmm_names}"
        )
        assert not any("human" in n for n in hmm_names), (
            f"macaque should not load human HMMs: {hmm_names}"
        )

    def test_macaque_germline_resolves_to_macaque(self):
        """Regression: macaque sequences must resolve germline against macaque entries in all_germlines."""
        seq = SPECIES_TEST_SEQUENCES["macaque"]
        r = Renumbering(
            scheme="kabat",
            allowed_species=["macaque"],
            allowed_chain=["H"],
            run_multiproc=False,
        )
        result = r.run_single("test_macaque_germline", seq)
        assert not result.empty
        identity_species = result["identity_species"].iloc[0]
        assert identity_species == "macaque", (
            f"Expected identity_species='macaque' but got '{identity_species}'."
            f" The all_germlines keys should use 'macaque' as the canonical name."
        )


class TestRatIGHJData:
    """Tests for rat IGHJ data gap in all_germlines (VAL-BUG-005)."""

    def test_rat_ighj_exists_in_all_germlines(self):
        """all_germlines['J']['H'] must contain 'rat' with at least 1 IGHJ gene."""
        from sadie.numbering.germlines import all_germlines

        assert "rat" in all_germlines["J"]["H"], "rat missing from all_germlines['J']['H']"
        rat_j = all_germlines["J"]["H"]["rat"]
        assert len(rat_j) >= 1, f"Expected at least 1 rat IGHJ entry, got {len(rat_j)}"

    def test_rat_ighj_entries_have_correct_format(self):
        """Rat IGHJ entries must be 128 chars with dash padding and WGxG motif."""
        from sadie.numbering.germlines import all_germlines

        rat_j = all_germlines["J"]["H"]["rat"]
        for gene, seq in rat_j.items():
            assert len(seq) == 128, f"{gene}: expected 128 chars, got {len(seq)}"
            aa_part = seq.lstrip("-")
            assert len(aa_part) == 14, f"{gene}: expected 14 aa, got {len(aa_part)}"
            assert "W" in aa_part, f"{gene}: missing conserved W in WGxG motif"

    def test_rat_ighj_gene_names_start_with_ighj(self):
        """Rat IGHJ gene names must follow IGHJ naming convention."""
        from sadie.numbering.germlines import all_germlines

        rat_j = all_germlines["J"]["H"]["rat"]
        for gene in rat_j:
            assert gene.startswith("IGHJ"), f"Unexpected gene name: {gene}"


class TestAllowedScopingBug:
    """Tests for the _allowed variable scoping bug in run_germline_assignment().

    Bug 1: The resolved species list _allowed is built but the iteration loop
    uses the original allowed_species instead of _allowed.

    Bug 2: The else branch (allowed_species=None) references _allowed before
    it's defined, causing NameError.
    """

    def test_macaque_in_allowed_species_resolves_and_iterates(self):
        """allowed_species=['macaque'] must resolve to the 'macaque' key in all_germlines,
        producing a valid v_gene."""
        from sadie.numbering.numbering import Numbering

        seq = SPECIES_TEST_SEQUENCES["macaque"]
        r = Renumbering(
            scheme="kabat",
            allowed_species=["macaque"],
            allowed_chain=["H"],
            run_multiproc=False,
        )
        result = r.run_single("test_macaque_scoping", seq)
        assert not result.empty, "Renumbering returned empty result for macaque"

        v_gene = result["v_gene"].iloc[0]
        assert v_gene is not None, (
            "macaque v_gene is None — _allowed scoping bug caused germline assignment to fail"
        )
        identity_species = result["identity_species"].iloc[0]
        assert identity_species == "macaque", (
            f"Expected identity_species='macaque' but got '{identity_species}'"
        )

    def test_allowed_species_none_does_not_raise_nameerror(self):
        """allowed_species=None in run_germline_assignment() must not raise NameError.

        Bug: The else branch (when allowed_species is None) references _allowed
        before it's defined. This tests the Numbering method directly since
        Renumbering.__init__ defaults allowed_species to ["human"].
        """
        from sadie.numbering.numbering import Numbering

        n = Numbering(scheme="kabat")
        seq = SPECIES_TEST_SEQUENCES["human"]

        # Build a simple state_vector with match states for positions 1-128
        padded = seq + "-" * (128 - len(seq)) if len(seq) < 128 else seq[:128]
        state_vector = [((i + 1, "m"), i) for i in range(min(len(seq), 128))]

        # This must not raise NameError for undefined _allowed
        genes = n.run_germline_assignment(state_vector, padded, "H", allowed_species=None)
        assert genes["v_gene"][0] is not None, (
            "v_gene is None with allowed_species=None — the else branch is broken"
        )


class TestMacaqueGermlineKeyRename:
    """Tests for the rhesus→macaque key rename in all_germlines (VAL-NAME-001, VAL-NAME-002).

    Verifies that all_germlines uses 'macaque' as the canonical species key
    and that no 'rhesus' keys remain. Also verifies the inverted _SPECIES_ALIASES.
    """

    def test_all_germlines_v_genes_use_macaque_key(self):
        """all_germlines V-gene entries must use 'macaque' key, not 'rhesus'."""
        from sadie.numbering.germlines import all_germlines

        for chain in ["H", "K", "L"]:
            assert "macaque" in all_germlines["V"][chain], (
                f"'macaque' missing from all_germlines['V']['{chain}']"
            )
            assert len(all_germlines["V"][chain]["macaque"]) >= 1, (
                f"all_germlines['V']['{chain}']['macaque'] is empty"
            )
            assert "rhesus" not in all_germlines["V"][chain], (
                f"'rhesus' key still present in all_germlines['V']['{chain}'] — should be renamed to 'macaque'"
            )

    def test_all_germlines_j_genes_use_macaque_key(self):
        """all_germlines J-gene entries must use 'macaque' key, not 'rhesus'."""
        from sadie.numbering.germlines import all_germlines

        for chain in ["H", "K", "L"]:
            assert "macaque" in all_germlines["J"][chain], (
                f"'macaque' missing from all_germlines['J']['{chain}']"
            )
            assert len(all_germlines["J"][chain]["macaque"]) >= 1, (
                f"all_germlines['J']['{chain}']['macaque'] is empty"
            )
            assert "rhesus" not in all_germlines["J"][chain], (
                f"'rhesus' key still present in all_germlines['J']['{chain}'] — should be renamed to 'macaque'"
            )

    def test_no_rhesus_keys_anywhere_in_all_germlines(self):
        """No 'rhesus' keys should exist at any level in all_germlines."""
        from sadie.numbering.germlines import all_germlines

        for segment in all_germlines:
            for chain in all_germlines[segment]:
                assert "rhesus" not in all_germlines[segment][chain], (
                    f"'rhesus' key found in all_germlines['{segment}']['{chain}']"
                )

    def test_species_aliases_maps_rhesus_to_macaque(self):
        """_SPECIES_ALIASES must map 'rhesus' → 'macaque' (not the reverse)."""
        from sadie.numbering.numbering import Numbering

        assert "rhesus" in Numbering._SPECIES_ALIASES, (
            "'rhesus' not in _SPECIES_ALIASES — it should be an alias for 'macaque'"
        )
        assert Numbering._SPECIES_ALIASES["rhesus"] == "macaque", (
            f"Expected _SPECIES_ALIASES['rhesus'] == 'macaque', "
            f"got '{Numbering._SPECIES_ALIASES['rhesus']}'"
        )
        assert "macaque" not in Numbering._SPECIES_ALIASES, (
            "'macaque' should not be in _SPECIES_ALIASES — it is the canonical key, not an alias"
        )

    def test_rhesus_backward_compat_resolves_to_macaque_germlines(self):
        """Using allowed_species=['rhesus'] must still produce valid results via macaque germlines."""
        seq = SPECIES_TEST_SEQUENCES["rhesus"]
        r = Renumbering(
            scheme="kabat",
            allowed_species=["rhesus"],
            allowed_chain=["H"],
            run_multiproc=False,
        )
        result = r.run_single("test_rhesus_compat", seq)
        assert not result.empty, "Renumbering returned empty for 'rhesus' — backward compat broken"
        v_gene = result["v_gene"].iloc[0]
        assert v_gene is not None, "v_gene is None for 'rhesus' — germline assignment failed"
        identity_species = result["identity_species"].iloc[0]
        assert identity_species == "macaque", (
            f"Expected identity_species='macaque' (resolved from rhesus alias) but got '{identity_species}'"
        )
