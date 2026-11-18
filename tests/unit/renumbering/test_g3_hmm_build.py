import filecmp

import pyhmmer

from sadie.renumbering.clients import G3

HEAVY_CHAIN_AA = (
    "EVQLVESGGGLEQPGGSLRLSCAGSGFTFRDYAMTWVRQAPGKGLEWVSSISGSGGNTYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYC"
    "AKDRLSITIRPRYYGLDVWGQGTTVTVSS"
)


def _offline_g3(data_folder):
    g3 = G3()
    g3.data_folder = data_folder
    return g3


def test_build_hmm_from_static_database_writes_128_state_model(tmp_path):
    hmm_path = _offline_g3(tmp_path).build_hmm(source="imgt", species="human", chain="H")

    with pyhmmer.plan7.HMMFile(hmm_path) as hmm_file:
        hmm = next(hmm_file)

    assert hmm_path == tmp_path / "hmms" / "human_H.hmm"
    assert hmm.M == 128
    assert hmm.nseq == 3679


def test_build_stockholm_from_static_database_matches_shipped_alignment(tmp_path, fixture_setup):
    built_stockholm = _offline_g3(tmp_path).build_stockholm(source="imgt", species="human", chain="H")
    shipped_stockholm = fixture_setup.hmm_data.parent / "stockholms" / "human_H.sto"

    assert filecmp.cmp(built_stockholm, shipped_stockholm, shallow=False)


def test_get_hmm_without_cached_file_builds_model_that_aligns_heavy_chain(tmp_path):
    g3 = _offline_g3(tmp_path)
    hmm = g3.get_hmm(source="imgt", species="human", chain="H")
    query = pyhmmer.easel.TextSequence(name=b"heavy", sequence=HEAVY_CHAIN_AA).digitize(g3.alphabet)

    top_hits = next(pyhmmer.hmmsearch([hmm], [query]))

    assert (tmp_path / "hmms" / "human_H.hmm").is_file()
    assert len(top_hits) == 1
    assert top_hits[0].best_domain.alignment.hmm_to == 128
