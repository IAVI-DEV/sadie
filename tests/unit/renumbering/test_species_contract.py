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
    "mouse": ("EVQLQQSGPELVKPGASVKISCKASGYTFTDYNMDWVKQSHGKSLEWIGDINPNNGGT" "IYNQKFKGKATLTVDKSSSTAYMELRSLTSEDTAVYYCAR"),
    "macaque": (
        "EVQLVESGGGLVQPGGSLRLSCVISGFTFSSHGMYWVRQAPGKGLQWVAAISSGGSAWY"
        "TNSLKGRFTISRDNAKDTLYLQMDSLRTEDTAVYYCAKEVSSGYSYMDSWGQGVLVTVSS"
    ),
    "rhesus": (
        "EVQLVESGGGLVQPGGSLRLSCVISGFTFSSHGMYWVRQAPGKGLQWVAAISSGGSAWY"
        "TNSLKGRFTISRDNAKDTLYLQMDSLRTEDTAVYYCAKEVSSGYSYMDSWGQGVLVTVSS"
    ),
    "rabbit": (
        "QEQLVESGGGLVQPGESLRLSCAASGFTFDDYAMHWVRQAPGKGLEWVSGISWNSGSIG" "YADSVKGRFTISRDNAKNSLYLQMNSLRAEDTALYYCAKG"
    ),
    "rat": ("EVQLVESGGGLVQPKGSLKLSCAASGFTFSNYGMHWVRQAPGKGLEWVAYISSGSSTIY" "YPDTVKGRFTISRDNAKNTLYLQMSSLKSEDTAMYYCTR"),
    "cow": ("QVQLRESGPSLVKPSQTLSLTCTVSGFSLSSYGVGWVRQAPGKALECLGGISSGGSTGY" "NPALKYRLSITKDNSKSQVSLSLSSVTTEDTATYYCAK"),
    "chicken": (
        "AVTLDESGGGLQTPRGALSLVCKASGFTFSSYGMGWVRQAPGKGLEWVAGIGSS" "GSGTAYGSAVKGRATISRDNGQSTVRLQLNNLRAEDTGTYYCAKAAG"
    ),
}


class TestSpeciesContract:
    """Verify every allowed species can complete the full renumbering pipeline."""

    def test_all_allowed_species_have_hmms(self):
        """Every species in get_allowed_species() must load at least one HMM (H chain)."""
        for species in Renumbering.get_allowed_species():
            r = Renumbering(
                allowed_species=[species],
                allowed_chain=["H"],
                run_multiproc=False,
            )
            assert len(r.hmmer.hmms) > 0, f"Species '{species}' loaded 0 HMMs -- it will silently fail."

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
        assert not result.empty, f"Renumbering returned empty result for species '{species}'"

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
        hmm_names = [(h.name if isinstance(h.name, str) else h.name.decode()) for h in r.hmmer.hmms]
        assert any("macaque" in n for n in hmm_names), f"Expected macaque HMM but got: {hmm_names}"
        assert not any("human" in n for n in hmm_names), f"macaque should not load human HMMs: {hmm_names}"

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
        assert v_gene is not None, "macaque v_gene is None — _allowed scoping bug caused germline assignment to fail"
        identity_species = result["identity_species"].iloc[0]
        assert identity_species == "macaque", f"Expected identity_species='macaque' but got '{identity_species}'"

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
        assert genes["v_gene"][0] is not None, "v_gene is None with allowed_species=None — the else branch is broken"


class TestRhesusHMMRouting:
    """Tests for rhesus → macaque HMM routing (VAL-NAME-003, VAL-NAME-004, VAL-NAME-005).

    Verifies that 'rhesus' loads macaque HMMs through LocalHMMBuilder (not legacy
    ANARCI HMMs), produces no fallback warnings, and gives identical output to 'macaque'.
    """

    def test_rhesus_loads_macaque_hmms_not_legacy(self):
        """Renumbering(allowed_species=['rhesus']) must load macaque HMMs, not legacy ANARCI rhesus HMMs.

        The HMM name should contain 'macaque', proving it came from LocalHMMBuilder
        (not the legacy Numbering HMMs which use 'rhesus' naming).
        """
        r = Renumbering(
            scheme="kabat",
            allowed_species=["rhesus"],
            allowed_chain=["H"],
            run_multiproc=False,
        )
        hmm_names = [(h.name if isinstance(h.name, str) else h.name.decode()) for h in r.hmmer.hmms]
        assert any("macaque" in n for n in hmm_names), (
            f"Expected macaque HMM for rhesus but got: {hmm_names}. "
            f"'rhesus' should route to macaque HMMs via _HMM_SPECIES_ALIASES."
        )

    def test_rhesus_no_fallback_warning(self, caplog):
        """No 'Falling back to G3/Numbering' warning when using rhesus."""
        import logging

        with caplog.at_level(logging.WARNING):
            r = Renumbering(
                scheme="kabat",
                allowed_species=["rhesus"],
                allowed_chain=["H"],
                run_multiproc=False,
            )
        fallback_msgs = [rec for rec in caplog.records if "Falling back" in rec.message]
        assert len(fallback_msgs) == 0, (
            f"Got fallback warnings for rhesus: {[m.message for m in fallback_msgs]}. "
            f"rhesus should route to macaque HMMs without fallback."
        )

    def test_rhesus_and_macaque_produce_identical_output(self):
        """rhesus and macaque must produce identical renumbering output for the same VH sequence."""
        seq = SPECIES_TEST_SEQUENCES["macaque"]

        r_macaque = Renumbering(
            scheme="kabat",
            allowed_species=["macaque"],
            allowed_chain=["H"],
            run_multiproc=False,
        )
        r_rhesus = Renumbering(
            scheme="kabat",
            allowed_species=["rhesus"],
            allowed_chain=["H"],
            run_multiproc=False,
        )

        result_macaque = r_macaque.run_single("test_macaque", seq)
        result_rhesus = r_rhesus.run_single("test_rhesus", seq)

        assert not result_macaque.empty
        assert not result_rhesus.empty

        # Compare key columns (scheme, chain_type, v_gene, j_gene, numbered positions)
        for col in ["scheme", "chain_type", "v_gene", "j_gene"]:
            if col in result_macaque.columns and col in result_rhesus.columns:
                assert result_macaque[col].iloc[0] == result_rhesus[col].iloc[0], (
                    f"Column '{col}' differs: macaque={result_macaque[col].iloc[0]}, "
                    f"rhesus={result_rhesus[col].iloc[0]}"
                )

    def test_macaque_renumbering_unchanged_regression(self):
        """macaque renumbering must be stable — HMM position 30 is a match (not deletion)."""
        seq = SPECIES_TEST_SEQUENCES["macaque"]
        r = Renumbering(
            scheme="kabat",
            allowed_species=["macaque"],
            allowed_chain=["H"],
            run_multiproc=False,
        )
        result = r.run_single("test_macaque_regression", seq)
        assert not result.empty

        # Position 30 must have a residue (not be deleted)
        if "30" in result.columns:
            pos30 = result["30"].iloc[0]
            assert pos30 != "-" and pos30 is not None, (
                f"HMM position 30 is '{pos30}' — expected a match state, not a deletion. "
                f"This indicates wrong HMM was used."
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
            assert "macaque" in all_germlines["V"][chain], f"'macaque' missing from all_germlines['V']['{chain}']"
            assert len(all_germlines["V"][chain]["macaque"]) >= 1, f"all_germlines['V']['{chain}']['macaque'] is empty"
            assert (
                "rhesus" not in all_germlines["V"][chain]
            ), f"'rhesus' key still present in all_germlines['V']['{chain}'] — should be renamed to 'macaque'"

    def test_all_germlines_j_genes_use_macaque_key(self):
        """all_germlines J-gene entries must use 'macaque' key, not 'rhesus'."""
        from sadie.numbering.germlines import all_germlines

        for chain in ["H", "K", "L"]:
            assert "macaque" in all_germlines["J"][chain], f"'macaque' missing from all_germlines['J']['{chain}']"
            assert len(all_germlines["J"][chain]["macaque"]) >= 1, f"all_germlines['J']['{chain}']['macaque'] is empty"
            assert (
                "rhesus" not in all_germlines["J"][chain]
            ), f"'rhesus' key still present in all_germlines['J']['{chain}'] — should be renamed to 'macaque'"

    def test_no_rhesus_keys_anywhere_in_all_germlines(self):
        """No 'rhesus' keys should exist at any level in all_germlines."""
        from sadie.numbering.germlines import all_germlines

        for segment in all_germlines:
            for chain in all_germlines[segment]:
                assert (
                    "rhesus" not in all_germlines[segment][chain]
                ), f"'rhesus' key found in all_germlines['{segment}']['{chain}']"

    def test_species_aliases_maps_rhesus_to_macaque(self):
        """_SPECIES_ALIASES must map 'rhesus' → 'macaque' (not the reverse)."""
        from sadie.numbering.numbering import Numbering

        assert (
            "rhesus" in Numbering._SPECIES_ALIASES
        ), "'rhesus' not in _SPECIES_ALIASES — it should be an alias for 'macaque'"
        assert Numbering._SPECIES_ALIASES["rhesus"] == "macaque", (
            f"Expected _SPECIES_ALIASES['rhesus'] == 'macaque', " f"got '{Numbering._SPECIES_ALIASES['rhesus']}'"
        )
        assert (
            "macaque" not in Numbering._SPECIES_ALIASES
        ), "'macaque' should not be in _SPECIES_ALIASES — it is the canonical key, not an alias"

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
        assert (
            identity_species == "macaque"
        ), f"Expected identity_species='macaque' (resolved from rhesus alias) but got '{identity_species}'"


class TestCowSpeciesContract:
    """Tests for cow as a fully supported species (VAL-EXP-001, VAL-EXP-002, VAL-EXP-003)."""

    def test_cow_in_allowed_species(self):
        """'cow' must appear in Renumbering.get_allowed_species()."""
        allowed = Renumbering.get_allowed_species()
        assert "cow" in allowed, f"'cow' not in get_allowed_species(): {allowed}"

    def test_cow_hmms_load_successfully(self):
        """Renumbering(allowed_species=['cow']) must load cow HMMs without error."""
        r = Renumbering(
            allowed_species=["cow"],
            allowed_chain=["H", "K", "L"],
            run_multiproc=False,
        )
        assert len(r.hmmer.hmms) > 0, "No HMMs loaded for cow"
        hmm_names = [(h.name if isinstance(h.name, str) else h.name.decode()) for h in r.hmmer.hmms]
        assert any("cow" in n for n in hmm_names), f"Expected cow HMM but got: {hmm_names}"

    def test_cow_vh_produces_numbered_result(self):
        """Cow VH sequence must produce a non-empty numbered result with Kabat positions."""
        seq = SPECIES_TEST_SEQUENCES["cow"]
        r = Renumbering(
            scheme="kabat",
            allowed_species=["cow"],
            allowed_chain=["H"],
            run_multiproc=False,
        )
        result = r.run_single("test_cow_vh", seq)
        assert not result.empty, "Renumbering returned empty result for cow VH"
        # Verify at least some Kabat positions are assigned
        assert result.shape[1] > 5, f"Too few columns in cow result: {result.shape[1]}"

    def test_cow_germline_assignment_returns_cow_vgene(self):
        """Cow VH sequence must get a cow-species V-gene assignment (not human)."""
        seq = SPECIES_TEST_SEQUENCES["cow"]
        r = Renumbering(
            scheme="kabat",
            allowed_species=["cow"],
            allowed_chain=["H"],
            run_multiproc=False,
        )
        result = r.run_single("test_cow_germline", seq)
        assert not result.empty, "Renumbering returned empty result for cow"
        v_gene = result["v_gene"].iloc[0]
        assert v_gene is not None, "v_gene is None for cow — germline assignment failed"
        identity_species = result["identity_species"].iloc[0]
        assert identity_species == "cow", (
            f"Expected identity_species='cow' but got '{identity_species}'. "
            f"Cow germline assignment should return a cow V-gene, not {identity_species}."
        )

    def test_cow_germline_data_exists_in_all_germlines(self):
        """all_germlines must have cow entries for V and J segments."""
        from sadie.numbering.germlines import all_germlines

        for segment in ["V", "J"]:
            for chain in ["H", "K", "L"]:
                assert (
                    "cow" in all_germlines[segment][chain]
                ), f"'cow' missing from all_germlines['{segment}']['{chain}']"
                assert (
                    len(all_germlines[segment][chain]["cow"]) >= 1
                ), f"all_germlines['{segment}']['{chain}']['cow'] is empty"


class TestChickenSpeciesContract:
    """Tests for chicken as a supported species (VAL-EXP-004, VAL-EXP-005, VAL-EXP-006, VAL-EXP-008)."""

    def test_chicken_in_allowed_species(self):
        """'chicken' must appear in Renumbering.get_allowed_species()."""
        allowed = Renumbering.get_allowed_species()
        assert "chicken" in allowed, f"'chicken' not in get_allowed_species(): {allowed}"

    def test_chicken_hmms_load_successfully(self):
        """Renumbering(allowed_species=['chicken']) must load chicken HMMs without error."""
        r = Renumbering(
            allowed_species=["chicken"],
            allowed_chain=["H", "L"],
            run_multiproc=False,
        )
        assert len(r.hmmer.hmms) > 0, "No HMMs loaded for chicken"
        hmm_names = [(h.name if isinstance(h.name, str) else h.name.decode()) for h in r.hmmer.hmms]
        assert any("chicken" in n for n in hmm_names), f"Expected chicken HMM but got: {hmm_names}"

    def test_chicken_vh_produces_numbered_result(self):
        """Chicken VH sequence must produce a non-empty numbered result."""
        seq = SPECIES_TEST_SEQUENCES["chicken"]
        r = Renumbering(
            scheme="kabat",
            allowed_species=["chicken"],
            allowed_chain=["H"],
            run_multiproc=False,
        )
        result = r.run_single("test_chicken_vh", seq)
        assert not result.empty, "Renumbering returned empty result for chicken VH"
        assert result.shape[1] > 5, f"Too few columns in chicken result: {result.shape[1]}"

    def test_chicken_germline_assignment_returns_chicken_vgene(self):
        """Chicken VH must get a chicken-species V-gene assignment."""
        seq = SPECIES_TEST_SEQUENCES["chicken"]
        r = Renumbering(
            scheme="kabat",
            allowed_species=["chicken"],
            allowed_chain=["H"],
            run_multiproc=False,
        )
        result = r.run_single("test_chicken_germline", seq)
        assert not result.empty, "Renumbering returned empty result for chicken"
        v_gene = result["v_gene"].iloc[0]
        assert v_gene is not None, "v_gene is None for chicken — germline assignment failed"
        identity_species = result["identity_species"].iloc[0]
        assert identity_species == "chicken", (
            f"Expected identity_species='chicken' but got '{identity_species}'. "
            f"Chicken germline assignment should return a chicken V-gene."
        )

    def test_chicken_germline_data_exists_in_all_germlines(self):
        """all_germlines must have chicken entries for V/H, J/H, V/L, J/L."""
        from sadie.numbering.germlines import all_germlines

        for segment in ["V", "J"]:
            for chain in ["H", "L"]:
                assert (
                    "chicken" in all_germlines[segment][chain]
                ), f"'chicken' missing from all_germlines['{segment}']['{chain}']"
                assert (
                    len(all_germlines[segment][chain]["chicken"]) >= 1
                ), f"all_germlines['{segment}']['{chain}']['chicken'] is empty"

    def test_chicken_has_no_kappa(self):
        """Chicken biologically has no kappa chain — V/K and J/K should not have chicken entries."""
        from sadie.numbering.germlines import all_germlines

        for segment in ["V", "J"]:
            assert (
                "chicken" not in all_germlines[segment]["K"]
            ), f"Chicken should NOT have entries in all_germlines['{segment}']['K'] — chickens lack kappa"


class TestUnsupportedChainGuardRails:
    """Tests for unsupported species/chain combinations (VAL-EXP-007).

    When a user requests renumbering for a species/chain combo that has no HMM
    (e.g., alpaca kappa, alpaca lambda, chicken kappa), the system should raise
    a descriptive ValueError rather than silently failing.
    """

    @pytest.mark.parametrize(
        "species,chain,expected_supported",
        [
            ("alpaca", "K", ["H"]),
            ("alpaca", "L", ["H"]),
            ("chicken", "K", ["H", "L"]),
        ],
        ids=["alpaca-K", "alpaca-L", "chicken-K"],
    )
    def test_unsupported_chain_raises_descriptive_error(self, species, chain, expected_supported):
        """Requesting an unsupported species/chain combo must raise ValueError with descriptive message."""
        with pytest.raises(ValueError, match=species) as exc_info:
            Renumbering(
                allowed_species=[species],
                allowed_chain=[chain],
                run_multiproc=False,
            )
        error_msg = str(exc_info.value)
        # Error message must include the species name
        assert species in error_msg, f"Error message should include species '{species}': {error_msg}"
        # Error message must include the unsupported chain
        assert chain in error_msg, f"Error message should include chain '{chain}': {error_msg}"
        # Error message must mention supported chains for that species
        for supported_chain in expected_supported:
            assert (
                supported_chain in error_msg
            ), f"Error message should include supported chain '{supported_chain}' for {species}: {error_msg}"

    @pytest.mark.parametrize(
        "species,chain",
        [
            ("alpaca", "H"),
            ("chicken", "H"),
            ("chicken", "L"),
            ("human", "H"),
            ("human", "K"),
            ("human", "L"),
        ],
        ids=["alpaca-H", "chicken-H", "chicken-L", "human-H", "human-K", "human-L"],
    )
    def test_supported_chain_does_not_raise(self, species, chain):
        """Supported species/chain combos must work normally without raising errors."""
        r = Renumbering(
            allowed_species=[species],
            allowed_chain=[chain],
            run_multiproc=False,
        )
        assert len(r.hmmer.hmms) > 0, f"Expected HMMs loaded for {species} {chain}"


class TestMixedRequestGuardRails:
    """Tests for mixed request validation where some species/chain pairs are valid and others are not.

    The guard rail must validate EVERY explicitly requested species/chain pair individually,
    not just check whether zero HMMs were loaded total. This prevents silent dropping of
    unsupported pairs when at least one valid pair exists.
    """

    def test_alpaca_h_and_k_raises_for_missing_k(self):
        """allowed_species=['alpaca'], allowed_chain=['H','K'] must raise for alpaca K.

        alpaca has H but not K. The guard rail must catch the missing K even though
        alpaca H loads successfully (hmms is non-empty).
        """
        with pytest.raises(ValueError, match="alpaca") as exc_info:
            Renumbering(
                allowed_species=["alpaca"],
                allowed_chain=["H", "K"],
                run_multiproc=False,
            )
        error_msg = str(exc_info.value)
        assert "K" in error_msg, f"Error must mention unsupported chain 'K': {error_msg}"

    def test_human_and_alpaca_k_raises_for_alpaca_k(self):
        """allowed_species=['human','alpaca'], allowed_chain=['K'] must raise for alpaca K.

        human K is valid, alpaca K is not. The guard rail must catch alpaca K even
        though human K loads successfully.
        """
        with pytest.raises(ValueError, match="alpaca") as exc_info:
            Renumbering(
                allowed_species=["human", "alpaca"],
                allowed_chain=["K"],
                run_multiproc=False,
            )
        error_msg = str(exc_info.value)
        assert "alpaca" in error_msg, f"Error must mention species 'alpaca': {error_msg}"
        assert "K" in error_msg, f"Error must mention unsupported chain 'K': {error_msg}"

    def test_alpaca_h_only_does_not_raise(self):
        """allowed_species=['alpaca'], allowed_chain=['H'] must NOT raise.

        This is a fully supported combination — no error expected.
        """
        r = Renumbering(
            allowed_species=["alpaca"],
            allowed_chain=["H"],
            run_multiproc=False,
        )
        assert len(r.hmmer.hmms) > 0, "Expected at least one HMM for alpaca H"
