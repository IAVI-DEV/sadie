from __future__ import annotations

from contextlib import AbstractContextManager
from contextlib import nullcontext as does_not_raise

import pytest
from pydantic import BaseModel, ValidationError

from sadie.typing.chain import Chain
from sadie.typing.source import Source
from sadie.typing.species import SPECIES, Species


class TestModels(BaseModel):
    source: Source
    species: Species
    chain: Chain


class TestSpeciesValidation:
    def test_species_validation_success(self):
        model = TestModels(source="imgt", species="human", chain="H")
        assert model.species == "human"
        assert model.source == "imgt"
        assert model.chain == "H"

    def test_species_validation_transformation(self):
        model = TestModels(source="imgt", species="homo_sapiens", chain="H")
        assert model.species == "human"

    def test_species_validation_failure(self):
        with pytest.raises(ValidationError):
            TestModels(source="imgt", species="invalid_species", chain="H")


class TestChainValidation:
    def test_chain_validation_success(self):
        model = TestModels(source="imgt", species="human", chain="H")
        assert model.chain == "H"

    def test_chain_validation_lowercase(self):
        model = TestModels(source="imgt", species="human", chain="h")
        assert model.chain == "H"

    def test_chain_validation_failure(self):
        with pytest.raises(ValidationError):
            TestModels(source="imgt", species="human", chain="X")


class TestSpeciesDictConsistency:
    """Tests for species dict consistency fixes (VAL-BUG-002, VAL-BUG-003)."""

    def test_macaca_mulatta_resolves_to_macaque(self):
        """macaca_mulatta should map to 'macaque', not 'rhesus'."""
        assert Species.validate("macaca_mulatta") == "macaque"

    def test_cow_direct_key(self):
        """'cow' should be a direct key in SPECIES, not only reachable via 'bos_taurus'."""
        assert "cow" in SPECIES
        assert Species.validate("cow") == "cow"

    def test_bos_taurus_still_works(self):
        """bos_taurus should still resolve to cow."""
        assert Species.validate("bos_taurus") == "cow"

    def test_chicken_direct_key(self):
        """'chicken' should be a valid species."""
        assert "chicken" in SPECIES
        assert Species.validate("chicken") == "chicken"

    def test_gallus_gallus_resolves_to_chicken(self):
        """gallus_gallus should resolve to chicken."""
        assert Species.validate("gallus_gallus") == "chicken"

    def test_rhesus_still_resolves_to_macaque(self):
        """rhesus should still resolve to macaque (backward compat)."""
        assert Species.validate("rhesus") == "macaque"


class TestSourceValidation:
    def test_source_validation_success(self):
        model = TestModels(source="imgt", species="human", chain="H")
        assert model.source == "imgt"

    def test_source_validation_custom(self):
        model = TestModels(source="custom", species="human", chain="H")
        assert model.source == "custom"

    def test_source_validation_failure(self):
        with pytest.raises(ValidationError):
            TestModels(source="invalid_source", species="human", chain="H")
