import pytest

from sadie.germlines import GermlineManager


@pytest.mark.parametrize(
    "provider",
    [
        "imgt",
        pytest.param(
            "ogrdb",
            marks=pytest.mark.xfail(
                strict=True,
                raises=AssertionError,
                reason="sources/ogrdb/human/IGHD.fasta holds IgD constant records",
            ),
        ),
    ],
)
def test_get_gene_by_name_ighd_constant_allele_returns_constant_segment(provider):
    gene = GermlineManager(providers=[provider]).get_gene_by_name("IGHD*02", "human")

    assert gene.segment == "C"
