"""
Integration tests for MOTIF_LOOKUP with full pipeline.

This module tests the complete integration of the new MOTIF_LOOKUP system
with the full Sadie pipeline to ensure no breaking changes.

User Story 3: Maintain Backward Compatibility
- Test full pipeline integration with new MOTIF_LOOKUP
- Verify existing workflows continue to work
- Test integration points across modules
"""

import pytest
import time

from sadie.reference import MOTIF_LOOKUP, MOTIF_PROVENANCE
from sadie.reference.settings import get_motif_lookup, get_motif_provenance
from sadie.germlines.builders.j_gene_data import parse_j_gene, get_j_gene_data


class TestMotifLookupIntegrationBasics:
    """Test basic integration of MOTIF_LOOKUP system."""

    def test_motif_lookup_available(self):
        """Test that MOTIF_LOOKUP is available and populated."""
        assert MOTIF_LOOKUP is not None
        assert len(MOTIF_LOOKUP) > 0

        # Should have expected major species
        assert 'human' in MOTIF_LOOKUP
        assert 'mouse' in MOTIF_LOOKUP
        assert 'rat' in MOTIF_LOOKUP

    def test_motif_provenance_available(self):
        """Test that MOTIF_PROVENANCE is available and populated."""
        assert MOTIF_PROVENANCE is not None
        assert len(MOTIF_PROVENANCE) > 0

        # Should have provenance for all species in MOTIF_LOOKUP
        assert set(MOTIF_LOOKUP.keys()) == set(MOTIF_PROVENANCE.keys())

    def test_api_consistency(self):
        """Test that different access methods are consistent."""
        # Direct function calls vs imported objects
        direct_lookup = get_motif_lookup()
        direct_provenance = get_motif_provenance()

        # Should return the same data
        assert len(MOTIF_LOOKUP) == len(direct_lookup)
        assert len(MOTIF_PROVENANCE) == len(direct_provenance)

        # Test specific species
        assert MOTIF_LOOKUP['human'] == direct_lookup['human']
        assert MOTIF_PROVENANCE['human'] == direct_provenance['human']


class TestJGeneDataIntegration:
    """Test integration with j_gene_data module."""

    def test_j_gene_data_uses_new_system(self):
        """Test that j_gene_data.py uses the new MOTIF_LOOKUP system."""
        from sadie.germlines.builders.j_gene_data import MOTIF_LOOKUP as jgene_lookup

        # Should be the same object/data
        assert len(jgene_lookup) == len(MOTIF_LOOKUP)
        assert jgene_lookup['human'] == MOTIF_LOOKUP['human']

    def test_parse_j_gene_integration(self):
        """Test J gene parsing with new system."""
        # Test human IGHJ parsing
        human_sequence = 'TTTGGGACAAGGTGACCGTGATCCTCTGGACAGGCTACGGC'

        result = parse_j_gene('human', 'IGHJ1*01', human_sequence)

        # Should return expected structure
        assert isinstance(result, dict)
        assert 'sequence_gapped_aa' in result
        assert 'cdr3' in result
        assert 'fwr4' in result
        assert 'reading_frame' in result

        # Should not be marked as not implemented for human
        assert result['not_implemented'] is False

    def test_get_j_gene_data_integration(self):
        """Test J gene data retrieval with new system."""
        # Test known human gene
        rf, chain_type, cdr3_end, extra_bps = get_j_gene_data('IGHJ1*01', 'H')

        assert isinstance(rf, int)
        assert chain_type == 'JH'
        assert isinstance(cdr3_end, int)
        assert isinstance(extra_bps, int)

    def test_species_coverage_integration(self):
        """Test that species coverage is maintained."""
        # Test multiple species
        test_species = ['human', 'mouse', 'rat']

        for species in test_species:
            if species in MOTIF_LOOKUP:
                patterns = MOTIF_LOOKUP[species]

                # Should have at least IGHJ pattern
                assert 'IGHJ' in patterns
                assert isinstance(patterns['IGHJ'], str)

                # Test parsing works
                test_seq = 'TTTGGGACAAGGTGACCGTGATCCTCTGGACAGG'
                result = parse_j_gene(species, 'IGHJ1*01', test_seq)
                assert isinstance(result, dict)


class TestPerformanceIntegration:
    """Test performance of integrated system."""

    def test_initial_loading_performance(self):
        """Test that initial loading is fast enough."""
        start_time = time.time()

        # Fresh loads
        lookup = get_motif_lookup()
        provenance = get_motif_provenance()

        elapsed = time.time() - start_time

        # Should load within 50ms requirement
        assert elapsed < 0.050, f"Initial loading took {elapsed:.3f}s, exceeds requirement"
        assert len(lookup) > 0
        assert len(provenance) > 0

    def test_lookup_performance(self):
        """Test that lookups are performant."""
        start_time = time.time()

        # Simulate typical usage patterns
        for _ in range(100):
            pattern = MOTIF_LOOKUP['human']['IGHJ']
            assert pattern is not None

            provenance = MOTIF_PROVENANCE['human']
            assert provenance is not None

        elapsed = time.time() - start_time

        # Should be very fast
        assert elapsed < 0.010, f"100 lookups took {elapsed:.3f}s, too slow"

    def test_j_gene_parsing_performance(self):
        """Test that J gene parsing is performant with new system."""
        sequence = 'TTTGGGACAAGGTGACCGTGATCCTCTGGACAGGCTACGGC'

        start_time = time.time()

        for _ in range(50):
            result = parse_j_gene('human', 'IGHJ1*01', sequence)
            assert result is not None

        elapsed = time.time() - start_time

        # Should be reasonable for production use
        assert elapsed < 0.100, f"50 parses took {elapsed:.3f}s, too slow"


class TestDataIntegrityIntegration:
    """Test data integrity across the integrated system."""

    def test_pattern_accessibility(self):
        """Test that all patterns are accessible via different methods."""
        # Get all species and patterns
        for species, patterns in MOTIF_LOOKUP.items():
            for locus, pattern in patterns.items():
                if locus != 'ignore' and isinstance(pattern, str):
                    # Should be accessible via the proxy
                    proxy_pattern = MOTIF_LOOKUP[species][locus]
                    assert proxy_pattern == pattern

                    # Should be accessible via direct function
                    direct_lookup = get_motif_lookup()
                    direct_pattern = direct_lookup[species][locus]
                    assert direct_pattern == pattern

    def test_provenance_consistency(self):
        """Test that provenance data is consistent."""
        for species in MOTIF_LOOKUP.keys():
            # Should have corresponding provenance
            assert species in MOTIF_PROVENANCE

            # Provenance should have required fields
            prov = MOTIF_PROVENANCE[species]
            assert 'source' in prov
            assert 'imgt_validated' in prov
            assert 'last_reviewed' in prov

    def test_no_provenance_leakage(self):
        """Test that provenance doesn't leak into MOTIF_LOOKUP."""
        for species, patterns in MOTIF_LOOKUP.items():
            # Should not contain provenance metadata
            assert '_provenance' not in patterns

            # All non-ignore keys should be locus patterns
            for key, value in patterns.items():
                if key != 'ignore':
                    assert isinstance(value, str) or isinstance(value, list)

    def test_regex_pattern_validity(self):
        """Test that all patterns are valid regex expressions."""
        import re

        for species, patterns in MOTIF_LOOKUP.items():
            for locus, pattern in patterns.items():
                if locus != 'ignore' and isinstance(pattern, str):
                    try:
                        re.compile(pattern)
                    except re.error as e:
                        pytest.fail(f"Invalid regex for {species}.{locus}: {pattern} - {e}")


class TestBackwardCompatibilityIntegration:
    """Test backward compatibility with existing code patterns."""

    def test_dict_interface_compatibility(self):
        """Test that MOTIF_LOOKUP maintains dict interface."""
        # Common access patterns that existing code uses

        # Key access
        human_data = MOTIF_LOOKUP['human']
        assert isinstance(human_data, dict)

        # Nested key access
        ighj_pattern = MOTIF_LOOKUP['human']['IGHJ']
        assert isinstance(ighj_pattern, str)

        # get() method
        nonexistent = MOTIF_LOOKUP.get('nonexistent_species', {})
        assert nonexistent == {}

        # 'in' operator
        assert 'human' in MOTIF_LOOKUP
        assert 'nonexistent_species' not in MOTIF_LOOKUP

        # Iteration
        species_list = list(MOTIF_LOOKUP.keys())
        assert 'human' in species_list

        # len() function
        assert len(MOTIF_LOOKUP) > 0

    def test_typical_consumer_patterns(self):
        """Test typical patterns that consumers use."""
        # Pattern 1: Check if species exists, then get pattern
        species = 'human'
        if species in MOTIF_LOOKUP:
            species_data = MOTIF_LOOKUP[species]
            if 'IGHJ' in species_data:
                pattern = species_data['IGHJ']
                assert isinstance(pattern, str)

        # Pattern 2: Use get() with defaults
        pattern = MOTIF_LOOKUP.get('human', {}).get('IGHJ', 'default_pattern')
        assert pattern != 'default_pattern'

        # Pattern 3: Iterate over all species
        pattern_count = 0
        for species, patterns in MOTIF_LOOKUP.items():
            for locus, pattern in patterns.items():
                if locus != 'ignore' and isinstance(pattern, str):
                    pattern_count += 1

        assert pattern_count > 0

    def test_j_gene_data_consumer_patterns(self):
        """Test patterns used by j_gene_data consumers."""
        # Pattern used in parse_j_gene function
        species = 'human'
        if species in MOTIF_LOOKUP:
            species_data = MOTIF_LOOKUP[species]
            if 'IGHJ' in species_data:
                pattern = species_data['IGHJ']
                ignore_list = species_data.get('ignore', [])

                assert isinstance(pattern, str)
                assert isinstance(ignore_list, list) or ignore_list == []


class TestErrorHandlingIntegration:
    """Test error handling in integrated system."""

    def test_missing_species_handling(self):
        """Test handling of missing species gracefully."""
        # Should not raise exceptions
        nonexistent_lookup = MOTIF_LOOKUP.get('nonexistent_species')
        assert nonexistent_lookup is None

        # Should handle in parse_j_gene
        sequence = 'TTTGGGACAAGGTGACCGTGATCCTCTGGACAGG'
        result = parse_j_gene('nonexistent_species', 'IGHJ1*01', sequence)

        assert result['not_implemented'] is True
        assert result['expression_match'] is False

    def test_missing_locus_handling(self):
        """Test handling of missing loci gracefully."""
        # Should not raise exceptions for valid species, invalid locus
        human_patterns = MOTIF_LOOKUP['human']
        nonexistent_pattern = human_patterns.get('NONEXISTENT_LOCUS')
        assert nonexistent_pattern is None

        # Should handle in parse_j_gene
        sequence = 'TTTGGGACAAGGTGACCGTGATCCTCTGGACAGG'
        result = parse_j_gene('human', 'NONEXISTENT*01', sequence)

        assert result['not_implemented'] is True
        assert result['expression_match'] is False

    def test_malformed_data_resilience(self):
        """Test resilience to data issues."""
        # Test with empty sequence
        result = parse_j_gene('human', 'IGHJ1*01', '')
        assert isinstance(result, dict)

        # Test with invalid characters in sequence
        result = parse_j_gene('human', 'IGHJ1*01', 'XXXYYY')
        assert isinstance(result, dict)


class TestFeatureFlagCompatibility:
    """Test compatibility when feature flags or modes change."""

    def test_consistent_results_across_access_methods(self):
        """Test that different access methods give consistent results."""
        # Import-time vs runtime access should be consistent
        from sadie.reference import MOTIF_LOOKUP as imported_lookup

        runtime_lookup = get_motif_lookup()

        # Should have same keys
        assert set(imported_lookup.keys()) == set(runtime_lookup.keys())

        # Should have same values for sample species
        assert imported_lookup['human'] == runtime_lookup['human']
        assert imported_lookup['mouse'] == runtime_lookup['mouse']

    def test_caching_consistency(self):
        """Test that caching doesn't break consistency."""
        # Multiple calls should return consistent data
        lookup1 = get_motif_lookup()
        lookup2 = get_motif_lookup()

        # Should be consistent
        assert lookup1['human'] == lookup2['human']
        assert len(lookup1) == len(lookup2)

        provenance1 = get_motif_provenance()
        provenance2 = get_motif_provenance()

        # Should be consistent
        assert provenance1['human'] == provenance2['human']
        assert len(provenance1) == len(provenance2)