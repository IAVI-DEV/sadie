"""
Test validation of all 37 species against JSON schema.

This module validates that all species in the MOTIF_LOOKUP registry
conform to the JSON schema specification.

User Story 4: JSON Migration & Data Quality
- Validate all 37 species against contracts/motif-registry.schema.json
- Ensure data integrity across the complete dataset
- Test schema compliance for production readiness
"""

import json
import pytest
from pathlib import Path

from sadie.reference.settings import _load_motif_registry, _get_motif_json_path
from sadie.reference.validation import (
    comprehensive_motif_validation,
    validate_against_schema,
    load_json_schema,
    quick_validation_summary
)


class TestMotifSchemaValidation:
    """Test validation of all species against JSON schema."""

    def test_all_species_against_schema(self):
        """Test that all 37 species validate against JSON schema."""
        # Load raw motif registry (with provenance)
        raw_registry = _load_motif_registry()

        # Load schema
        schema_path = Path(__file__).parents[3] / "specs" / "001-germline-completion" / "contracts" / "motif-registry.schema.json"

        assert schema_path.exists(), f"Schema file not found: {schema_path}"

        schema = load_json_schema(schema_path)

        # Validate against schema
        is_valid = validate_against_schema(raw_registry, schema)
        assert is_valid is True

    def test_comprehensive_validation_all_species(self):
        """Test comprehensive validation of all species."""
        # Load raw motif registry
        raw_registry = _load_motif_registry()

        # Schema path
        schema_path = Path(__file__).parents[3] / "specs" / "001-germline-completion" / "contracts" / "motif-registry.schema.json"

        # Run comprehensive validation
        is_valid = comprehensive_motif_validation(raw_registry, schema_path)
        assert is_valid is True

    def test_validation_summary(self):
        """Test validation summary for all species."""
        # Load raw motif registry
        raw_registry = _load_motif_registry()

        # Generate validation summary
        summary = quick_validation_summary(raw_registry)

        # Should have all expected species
        assert summary['total_species'] == 37

        # Should have provenance for all species
        assert summary['species_with_provenance'] == 37

        # Should have IMGT validated + legacy = total
        assert summary['imgt_validated_species'] + summary['legacy_species'] == 37

        # Should have patterns
        assert summary['total_patterns'] > 0

        # Should have no validation errors
        if summary['validation_errors']:
            pytest.fail(f"Validation errors found: {summary['validation_errors']}")

        assert summary['validation_passed'] is True

    def test_individual_species_validation(self):
        """Test validation of each species individually."""
        raw_registry = _load_motif_registry()

        for species, species_data in raw_registry.items():
            # Each species should have _provenance
            assert '_provenance' in species_data, f"Missing provenance for {species}"

            # Validate provenance structure
            provenance = species_data['_provenance']
            required_fields = {'source', 'imgt_validated', 'last_reviewed'}
            assert required_fields.issubset(provenance.keys()), \
                f"Missing provenance fields for {species}: {required_fields - provenance.keys()}"

            # Should have at least one pattern
            pattern_count = sum(1 for k, v in species_data.items()
                              if k not in ('_provenance', 'ignore') and isinstance(v, str))
            assert pattern_count > 0, f"No patterns found for {species}"

    def test_expected_species_present(self):
        """Test that all expected species are present."""
        raw_registry = _load_motif_registry()

        # Key species that should be present
        expected_species = [
            'human', 'mouse', 'rat', 'dog', 'cat', 'rabbit', 'cow',
            'horse', 'sheep', 'goat', 'pig', 'alpaca', 'macaque'
        ]

        for species in expected_species:
            assert species in raw_registry, f"Expected species missing: {species}"

        # Should have 37 total species
        assert len(raw_registry) == 37

    def test_imgt_validated_species(self):
        """Test IMGT-validated species have correct metadata."""
        raw_registry = _load_motif_registry()

        imgt_validated_count = 0
        for species, species_data in raw_registry.items():
            provenance = species_data['_provenance']
            if provenance['imgt_validated']:
                imgt_validated_count += 1

                # IMGT-validated should have high-quality source
                assert 'IMGT' in provenance['source'] or 'validated' in provenance['source'].lower(), \
                    f"IMGT-validated species {species} should reference IMGT in source"

        # Should have expected number of IMGT-validated species
        assert imgt_validated_count > 0, "No IMGT-validated species found"

    def test_legacy_species(self):
        """Test legacy species have appropriate metadata."""
        raw_registry = _load_motif_registry()

        legacy_count = 0
        for species, species_data in raw_registry.items():
            provenance = species_data['_provenance']
            if not provenance['imgt_validated']:
                legacy_count += 1

                # Legacy should indicate need for validation
                assert ('legacy' in provenance['source'].lower() or
                        'requires' in provenance.get('notes', '').lower() or
                        'validation' in provenance.get('notes', '').lower()), \
                    f"Legacy species {species} should indicate validation status"

        # Should have legacy species
        assert legacy_count > 0, "No legacy species found"

    def test_pattern_regex_validity(self):
        """Test that all patterns are valid regex expressions."""
        import re
        raw_registry = _load_motif_registry()

        invalid_patterns = []

        for species, species_data in raw_registry.items():
            for key, value in species_data.items():
                if key not in ('_provenance', 'ignore') and isinstance(value, str):
                    try:
                        re.compile(value)
                    except re.error as e:
                        invalid_patterns.append(f"{species}.{key}: {value} - {e}")

        if invalid_patterns:
            pytest.fail(f"Invalid regex patterns found:\n" + "\n".join(invalid_patterns))

    def test_ignore_lists_structure(self):
        """Test that ignore lists have correct structure."""
        raw_registry = _load_motif_registry()

        for species, species_data in raw_registry.items():
            if 'ignore' in species_data:
                ignore_list = species_data['ignore']
                assert isinstance(ignore_list, list), \
                    f"Ignore list for {species} should be a list, got {type(ignore_list)}"

                # All items should be strings
                for item in ignore_list:
                    assert isinstance(item, str), \
                        f"Ignore list item for {species} should be string, got {type(item)}"

    def test_locus_naming_convention(self):
        """Test that locus names follow expected conventions."""
        raw_registry = _load_motif_registry()

        expected_loci = ['IGHJ', 'IGKJ', 'IGLJ', 'TRAJ', 'TRBJ', 'TRDJ', 'TRGJ']

        for species, species_data in raw_registry.items():
            for key in species_data.keys():
                if key not in ('_provenance', 'ignore'):
                    assert key in expected_loci, \
                        f"Unexpected locus name {key} for species {species}"

    def test_date_format_validation(self):
        """Test that all dates are in correct format."""
        import re
        raw_registry = _load_motif_registry()

        date_pattern = r'^\d{4}-\d{2}-\d{2}$'

        for species, species_data in raw_registry.items():
            provenance = species_data['_provenance']
            last_reviewed = provenance['last_reviewed']

            assert re.match(date_pattern, last_reviewed), \
                f"Invalid date format for {species}: {last_reviewed} (should be YYYY-MM-DD)"


class TestMotifDataCompleteness:
    """Test completeness of motif data."""

    def test_species_coverage(self):
        """Test that we have good species coverage."""
        raw_registry = _load_motif_registry()

        # Should have major model organisms
        model_organisms = ['human', 'mouse', 'rat']
        for organism in model_organisms:
            assert organism in raw_registry, f"Missing model organism: {organism}"

        # Should have clinical/veterinary species
        clinical_species = ['dog', 'cat', 'rabbit', 'cow', 'horse', 'sheep', 'goat', 'pig']
        clinical_present = sum(1 for species in clinical_species if species in raw_registry)
        assert clinical_present > 0, "No clinical/veterinary species found"

        # Should have primates
        primates = ['macaque', 'human']  # Add others if present
        primate_present = sum(1 for species in primates if species in raw_registry)
        assert primate_present > 0, "No primate species found"

    def test_locus_coverage(self):
        """Test that major loci are covered."""
        raw_registry = _load_motif_registry()

        # Track locus coverage across all species
        locus_coverage = {}

        for species, species_data in raw_registry.items():
            for locus in species_data.keys():
                if locus not in ('_provenance', 'ignore'):
                    if locus not in locus_coverage:
                        locus_coverage[locus] = 0
                    locus_coverage[locus] += 1

        # Should have good coverage of major loci
        major_loci = ['IGHJ', 'IGKJ', 'IGLJ']
        for locus in major_loci:
            assert locus in locus_coverage, f"No coverage for major locus: {locus}"
            assert locus_coverage[locus] > 10, \
                f"Insufficient coverage for {locus}: {locus_coverage[locus]} species"

    def test_data_quality_metrics(self):
        """Test overall data quality metrics."""
        raw_registry = _load_motif_registry()
        summary = quick_validation_summary(raw_registry)

        # Quality thresholds
        assert summary['total_species'] >= 37, "Insufficient species coverage"
        assert summary['total_patterns'] >= 100, "Insufficient pattern coverage"
        assert summary['species_with_provenance'] == summary['total_species'], \
            "Not all species have provenance"

        # Balance of IMGT vs legacy
        imgt_ratio = summary['imgt_validated_species'] / summary['total_species']
        # Most species are legacy - IMGT validation is limited to major model organisms
        assert 0.02 <= imgt_ratio <= 0.5, \
            f"IMGT validation ratio {imgt_ratio:.2f} outside expected range"


class TestMotifSchemaCompliance:
    """Test compliance with schema requirements."""

    def test_schema_file_exists(self):
        """Test that schema file exists and is valid."""
        schema_path = Path(__file__).parents[3] / "specs" / "001-germline-completion" / "contracts" / "motif-registry.schema.json"

        assert schema_path.exists(), f"Schema file missing: {schema_path}"

        # Should be valid JSON
        with open(schema_path) as f:
            schema = json.load(f)

        # Should have expected structure
        assert '$schema' in schema
        assert 'type' in schema
        assert schema['type'] == 'object'

    def test_json_file_exists_and_valid(self):
        """Test that JSON file exists and is valid."""
        json_path = _get_motif_json_path()

        assert json_path.exists(), f"JSON file missing: {json_path}"

        # Should be valid JSON
        with open(json_path) as f:
            data = json.load(f)

        assert isinstance(data, dict), "JSON should contain a dictionary"
        assert len(data) > 0, "JSON should not be empty"

    def test_end_to_end_validation(self):
        """Test complete end-to-end validation pipeline."""
        # Load data
        raw_registry = _load_motif_registry()

        # Load schema
        schema_path = Path(__file__).parents[3] / "specs" / "001-germline-completion" / "contracts" / "motif-registry.schema.json"
        schema = load_json_schema(schema_path)

        # Run all validations
        # 1. Schema validation
        schema_valid = validate_against_schema(raw_registry, schema)
        assert schema_valid, "Schema validation failed"

        # 2. Comprehensive validation
        comprehensive_valid = comprehensive_motif_validation(raw_registry, schema_path)
        assert comprehensive_valid, "Comprehensive validation failed"

        # 3. Summary validation
        summary = quick_validation_summary(raw_registry)
        assert summary['validation_passed'], f"Validation errors: {summary['validation_errors']}"

        # Success - all validations passed
        assert True