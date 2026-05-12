"""
Test backward compatibility of MOTIF_LOOKUP after JSON migration.

This module ensures that the MOTIF_LOOKUP dict interface remains unchanged
after migration from Python dict to JSON-based loading system.

User Story 3: Maintain Backward Compatibility
- Test MOTIF_LOOKUP dict structure preservation
- Verify existing API works without modification
- Test integration with existing consumers
"""

import pytest
from collections.abc import Mapping

from sadie.reference.settings import get_motif_lookup, get_motif_provenance
from sadie.reference import MOTIF_LOOKUP, MOTIF_PROVENANCE


class TestMotifLookupBackwardCompatibility:
    """Test backward compatibility of MOTIF_LOOKUP interface."""

    def test_motif_lookup_is_dict_like(self):
        """Test that MOTIF_LOOKUP behaves like a dictionary."""
        # Should behave like a dict
        assert hasattr(MOTIF_LOOKUP, '__getitem__')
        assert hasattr(MOTIF_LOOKUP, '__iter__')
        assert hasattr(MOTIF_LOOKUP, '__len__')
        assert hasattr(MOTIF_LOOKUP, 'keys')
        assert hasattr(MOTIF_LOOKUP, 'values')
        assert hasattr(MOTIF_LOOKUP, 'items')
        assert hasattr(MOTIF_LOOKUP, 'get')

    def test_motif_lookup_implements_mapping(self):
        """Test that MOTIF_LOOKUP implements Mapping interface."""
        assert isinstance(MOTIF_LOOKUP, Mapping)

    def test_motif_lookup_contains_expected_species(self):
        """Test that MOTIF_LOOKUP contains expected species."""
        # Should have all 37 species
        assert len(MOTIF_LOOKUP) == 37

        # Test key access patterns that existing code uses
        assert 'human' in MOTIF_LOOKUP
        assert 'mouse' in MOTIF_LOOKUP
        assert 'rat' in MOTIF_LOOKUP

    def test_motif_lookup_species_structure(self):
        """Test that species data maintains expected structure."""
        human_data = MOTIF_LOOKUP['human']

        # Should be dict-like
        assert isinstance(human_data, dict)

        # Should contain expected loci (J segments)
        expected_loci = ['IGHJ', 'IGKJ', 'IGLJ']
        for locus in expected_loci:
            assert locus in human_data

        # Patterns should be strings
        assert isinstance(human_data['IGHJ'], str)
        assert isinstance(human_data['IGKJ'], str)
        assert isinstance(human_data['IGLJ'], str)

    def test_motif_lookup_pattern_access(self):
        """Test that motif patterns are accessible as before."""
        # Typical usage patterns from existing code
        human_ighj = MOTIF_LOOKUP['human']['IGHJ']
        mouse_ighj = MOTIF_LOOKUP['mouse']['IGHJ']

        assert isinstance(human_ighj, str)
        assert isinstance(mouse_ighj, str)
        assert len(human_ighj) > 0
        assert len(mouse_ighj) > 0

    def test_motif_lookup_get_method(self):
        """Test that get() method works for default values."""
        # Should return default for missing keys
        result = MOTIF_LOOKUP.get('nonexistent_species', {})
        assert result == {}

        # Should return species data for existing keys
        human_data = MOTIF_LOOKUP.get('human')
        assert human_data is not None
        assert 'IGHJ' in human_data

    def test_motif_lookup_iteration(self):
        """Test that iteration over MOTIF_LOOKUP works."""
        # Should be able to iterate over keys
        species_names = list(MOTIF_LOOKUP.keys())
        assert len(species_names) == 37
        assert 'human' in species_names

        # Should be able to iterate over items
        items = list(MOTIF_LOOKUP.items())
        assert len(items) == 37

        # Each item should be (species, patterns_dict)
        species, patterns = items[0]
        assert isinstance(species, str)
        assert isinstance(patterns, dict)

    def test_motif_lookup_values(self):
        """Test that values() method returns pattern dictionaries."""
        values = list(MOTIF_LOOKUP.values())
        assert len(values) == 37

        # Each value should be a dict containing patterns
        for patterns_dict in values:
            assert isinstance(patterns_dict, dict)
            # Should have at least one J segment pattern
            j_segments = ['IGHJ', 'IGKJ', 'IGLJ', 'TRAJ', 'TRBJ', 'TRDJ', 'TRGJ']
            has_j_segment = any(seg in patterns_dict for seg in j_segments)
            assert has_j_segment

    def test_motif_provenance_available(self):
        """Test that MOTIF_PROVENANCE is available in public API."""
        assert MOTIF_PROVENANCE is not None
        assert len(MOTIF_PROVENANCE) == 37

        # Should have provenance for all species
        assert 'human' in MOTIF_PROVENANCE

        # Human should be IMGT-validated
        human_prov = MOTIF_PROVENANCE['human']
        assert human_prov['imgt_validated'] is True
        assert 'source' in human_prov
        assert 'last_reviewed' in human_prov

    def test_no_provenance_in_motif_lookup(self):
        """Test that _provenance fields are filtered out of MOTIF_LOOKUP."""
        # MOTIF_LOOKUP should not contain _provenance fields for backward compatibility
        for species, patterns in MOTIF_LOOKUP.items():
            assert '_provenance' not in patterns

        # But MOTIF_PROVENANCE should contain provenance data
        assert len(MOTIF_PROVENANCE) > 0


class TestMotifLookupConsumerPatterns:
    """Test common usage patterns from existing consumers."""

    def test_species_pattern_lookup(self):
        """Test typical pattern lookup usage."""
        # Simulate common usage patterns
        species = 'human'
        locus = 'IGHJ'

        if species in MOTIF_LOOKUP:
            species_data = MOTIF_LOOKUP[species]
            if locus in species_data:
                pattern = species_data[locus]
                assert isinstance(pattern, str)
                assert len(pattern) > 0

    def test_ignore_list_handling(self):
        """Test that ignore lists are preserved."""
        # Some species have ignore lists
        for species, patterns in MOTIF_LOOKUP.items():
            if 'ignore' in patterns:
                ignore_list = patterns['ignore']
                assert isinstance(ignore_list, list)
                # Should be list of gene names to ignore
                for gene in ignore_list:
                    assert isinstance(gene, str)

    def test_missing_species_handling(self):
        """Test handling of missing species gracefully."""
        # Should not raise KeyError for missing species
        nonexistent = MOTIF_LOOKUP.get('nonexistent_species')
        assert nonexistent is None

        # Should be able to check existence
        assert 'nonexistent_species' not in MOTIF_LOOKUP
        assert 'human' in MOTIF_LOOKUP

    def test_missing_locus_handling(self):
        """Test handling of missing loci within species."""
        human_patterns = MOTIF_LOOKUP['human']

        # Should not raise KeyError for missing locus
        nonexistent = human_patterns.get('NONEXISTENT')
        assert nonexistent is None

        # Should be able to check existence
        assert 'NONEXISTENT' not in human_patterns
        assert 'IGHJ' in human_patterns


class TestMotifLookupPerformance:
    """Test performance characteristics of MOTIF_LOOKUP."""

    def test_lookup_performance(self):
        """Test that lookups are fast enough for production use."""
        import time

        # Test repeated access performance
        start_time = time.time()

        # Simulate 1000 lookups
        for _ in range(1000):
            pattern = MOTIF_LOOKUP['human']['IGHJ']
            assert pattern is not None

        elapsed = time.time() - start_time

        # Should be much faster than 50ms for 1000 lookups
        assert elapsed < 0.050, f"1000 lookups took {elapsed:.3f}s, too slow"

    def test_initial_loading_performance(self):
        """Test that initial loading is within performance requirements."""
        import time

        # Test fresh loading
        start_time = time.time()
        fresh_lookup = get_motif_lookup()
        elapsed = time.time() - start_time

        # Should load within 50ms requirement
        assert elapsed < 0.050, f"Initial loading took {elapsed:.3f}s, exceeds 50ms requirement"
        assert len(fresh_lookup) == 37


class TestMotifLookupDataIntegrity:
    """Test data integrity after migration."""

    def test_all_species_have_patterns(self):
        """Test that all species have at least one pattern."""
        for species, patterns in MOTIF_LOOKUP.items():
            # Should have at least one pattern (excluding ignore list)
            pattern_count = sum(1 for k, v in patterns.items()
                              if k != 'ignore' and isinstance(v, str))
            assert pattern_count > 0, f"Species {species} has no patterns"

    def test_patterns_are_valid_regex(self):
        """Test that all patterns are valid regular expressions."""
        import re

        for species, patterns in MOTIF_LOOKUP.items():
            for locus, pattern in patterns.items():
                if locus != 'ignore' and isinstance(pattern, str):
                    try:
                        re.compile(pattern)
                    except re.error as e:
                        pytest.fail(f"Invalid regex for {species}.{locus}: {pattern} - {e}")

    def test_expected_loci_present(self):
        """Test that expected loci are present for major species."""
        major_species = ['human', 'mouse', 'rat']
        expected_loci = ['IGHJ', 'IGKJ', 'IGLJ']

        for species in major_species:
            if species in MOTIF_LOOKUP:
                patterns = MOTIF_LOOKUP[species]
                for locus in expected_loci:
                    assert locus in patterns, f"Missing {locus} for {species}"


class TestMotifLookupVersusProvenance:
    """Test consistency between MOTIF_LOOKUP and MOTIF_PROVENANCE."""

    def test_same_species_in_both(self):
        """Test that MOTIF_LOOKUP and MOTIF_PROVENANCE have same species."""
        lookup_species = set(MOTIF_LOOKUP.keys())
        provenance_species = set(MOTIF_PROVENANCE.keys())

        assert lookup_species == provenance_species, \
            f"Species mismatch: MOTIF_LOOKUP has {lookup_species - provenance_species}, " \
            f"MOTIF_PROVENANCE has {provenance_species - lookup_species}"

    def test_provenance_metadata_structure(self):
        """Test that provenance metadata has expected structure."""
        for species, provenance in MOTIF_PROVENANCE.items():
            assert isinstance(provenance, dict)
            assert 'source' in provenance
            assert 'imgt_validated' in provenance
            assert 'last_reviewed' in provenance

            assert isinstance(provenance['source'], str)
            assert isinstance(provenance['imgt_validated'], bool)
            assert isinstance(provenance['last_reviewed'], str)

            # Date should be in YYYY-MM-DD format
            import re
            date_pattern = r'^\d{4}-\d{2}-\d{2}$'
            assert re.match(date_pattern, provenance['last_reviewed']), \
                f"Invalid date format for {species}: {provenance['last_reviewed']}"