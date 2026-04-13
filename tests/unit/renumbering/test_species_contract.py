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

    def test_macaque_germline_resolves_to_rhesus(self):
        """Regression: macaque sequences must resolve germline against rhesus entries."""
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
        assert identity_species == "rhesus", (
            f"Expected identity_species='rhesus' but got '{identity_species}'."
            f" The macaque->rhesus alias in Numbering._SPECIES_ALIASES may be broken."
        )
