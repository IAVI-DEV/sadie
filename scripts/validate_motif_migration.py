#!/usr/bin/env python3
"""
MOTIF_LOOKUP Migration Validation Script

This script validates the migration from Python dict-based MOTIF_LOOKUP
to the new JSON-based system with provenance metadata.

User Story 4: JSON Migration & Data Quality
- Validate complete migration to JSON-based system
- Ensure data integrity across all components
- Verify backward compatibility preservation
- Test production readiness

Usage:
    python scripts/validate_motif_migration.py [--verify-all] [--performance] [--verbose]

Examples:
    python scripts/validate_motif_migration.py                    # Basic validation
    python scripts/validate_motif_migration.py --verify-all       # Comprehensive validation
    python scripts/validate_motif_migration.py --performance      # Performance benchmarks
    python scripts/validate_motif_migration.py --verbose          # Detailed output
"""

import sys
import time
import argparse
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from sadie.reference.settings import (
    get_motif_lookup,
    get_motif_provenance,
    _load_motif_registry,
    _get_motif_json_path
)
from sadie.reference import MOTIF_LOOKUP, MOTIF_PROVENANCE
from sadie.reference.validation import (
    comprehensive_motif_validation,
    quick_validation_summary,
    validate_against_schema,
    load_json_schema
)


class MigrationValidator:
    """Validates MOTIF_LOOKUP migration to JSON-based system."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.results: Dict[str, Any] = {}

    def log(self, message: str, level: str = "INFO"):
        """Log a message with timestamp."""
        if self.verbose or level in ["ERROR", "WARNING"]:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] {level}: {message}")

    def add_error(self, message: str):
        """Add an error to the validation results."""
        self.errors.append(message)
        self.log(message, "ERROR")

    def add_warning(self, message: str):
        """Add a warning to the validation results."""
        self.warnings.append(message)
        self.log(message, "WARNING")

    def validate_file_structure(self) -> bool:
        """Validate that required files exist and are accessible."""
        self.log("Validating file structure...")

        # Check JSON file exists
        json_path = _get_motif_json_path()
        if not json_path.exists():
            self.add_error(f"JSON file not found: {json_path}")
            return False

        # Check JSON file is valid
        try:
            with open(json_path) as f:
                data = json.load(f)
            if not isinstance(data, dict) or len(data) == 0:
                self.add_error(f"JSON file invalid or empty: {json_path}")
                return False
        except json.JSONDecodeError as e:
            self.add_error(f"JSON file malformed: {json_path} - {e}")
            return False

        # Check schema files exist
        specs_dir = project_root / "specs" / "001-germline-completion" / "contracts"
        schema_files = [
            "motif-registry.schema.json",
            "coverage-test-result.schema.json",
            "motif-api-response.schema.json"
        ]

        for schema_file in schema_files:
            schema_path = specs_dir / schema_file
            if not schema_path.exists():
                self.add_warning(f"Schema file missing: {schema_path}")

        self.log("✓ File structure validation complete")
        return True

    def validate_data_loading(self) -> bool:
        """Validate that data loads correctly."""
        self.log("Validating data loading...")

        try:
            # Test loading functions
            motif_lookup = get_motif_lookup()
            motif_provenance = get_motif_provenance()
            raw_registry = _load_motif_registry()

            # Check data is loaded
            if not motif_lookup or len(motif_lookup) == 0:
                self.add_error("MOTIF_LOOKUP failed to load or is empty")
                return False

            if not motif_provenance or len(motif_provenance) == 0:
                self.add_error("MOTIF_PROVENANCE failed to load or is empty")
                return False

            if not raw_registry or len(raw_registry) == 0:
                self.add_error("Raw registry failed to load or is empty")
                return False

            # Check species count
            expected_species_count = 37
            if len(motif_lookup) != expected_species_count:
                self.add_warning(f"Expected {expected_species_count} species, got {len(motif_lookup)}")

            self.results['species_count'] = len(motif_lookup)
            self.log(f"✓ Loaded {len(motif_lookup)} species")

        except Exception as e:
            self.add_error(f"Data loading failed: {e}")
            return False

        return True

    def validate_backward_compatibility(self) -> bool:
        """Validate backward compatibility with existing API."""
        self.log("Validating backward compatibility...")

        try:
            # Test proxy object behaves like dict
            assert hasattr(MOTIF_LOOKUP, '__getitem__')
            assert hasattr(MOTIF_LOOKUP, '__iter__')
            assert hasattr(MOTIF_LOOKUP, '__len__')
            assert hasattr(MOTIF_LOOKUP, 'keys')
            assert hasattr(MOTIF_LOOKUP, 'values')
            assert hasattr(MOTIF_LOOKUP, 'items')
            assert hasattr(MOTIF_LOOKUP, 'get')

            # Test typical access patterns
            human_data = MOTIF_LOOKUP['human']
            assert isinstance(human_data, dict)

            ighj_pattern = MOTIF_LOOKUP['human']['IGHJ']
            assert isinstance(ighj_pattern, str)

            # Test get() method
            nonexistent = MOTIF_LOOKUP.get('nonexistent_species', {})
            assert nonexistent == {}

            # Test 'in' operator
            assert 'human' in MOTIF_LOOKUP

            # Test iteration
            species_list = list(MOTIF_LOOKUP.keys())
            assert 'human' in species_list

            # Test len()
            assert len(MOTIF_LOOKUP) > 0

            self.log("✓ Backward compatibility validation complete")

        except Exception as e:
            self.add_error(f"Backward compatibility validation failed: {e}")
            return False

        return True

    def validate_data_integrity(self) -> bool:
        """Validate data integrity and structure."""
        self.log("Validating data integrity...")

        try:
            # Get validation summary
            raw_registry = _load_motif_registry()
            summary = quick_validation_summary(raw_registry)

            # Check for validation errors
            if not summary['validation_passed']:
                for error in summary['validation_errors']:
                    self.add_error(f"Data integrity error: {error}")
                return False

            # Check provenance coverage
            if summary['species_with_provenance'] != summary['total_species']:
                self.add_error(f"Provenance missing: {summary['total_species'] - summary['species_with_provenance']} species")

            # Check pattern coverage
            if summary['total_patterns'] < 100:
                self.add_warning(f"Low pattern coverage: {summary['total_patterns']} patterns")

            # Store results
            self.results['data_summary'] = summary

            self.log(f"✓ Data integrity validated: {summary['total_species']} species, {summary['total_patterns']} patterns")

        except Exception as e:
            self.add_error(f"Data integrity validation failed: {e}")
            return False

        return True

    def validate_schema_compliance(self) -> bool:
        """Validate schema compliance."""
        self.log("Validating schema compliance...")

        try:
            # Load data and schema
            raw_registry = _load_motif_registry()
            schema_path = project_root / "specs" / "001-germline-completion" / "contracts" / "motif-registry.schema.json"

            if not schema_path.exists():
                self.add_warning("Schema file not found - skipping schema validation")
                return True

            schema = load_json_schema(schema_path)

            # Validate against schema
            is_valid = validate_against_schema(raw_registry, schema)

            if not is_valid:
                self.add_error("Schema validation failed")
                return False

            self.log("✓ Schema validation complete")

        except Exception as e:
            self.add_error(f"Schema validation failed: {e}")
            return False

        return True

    def validate_performance(self) -> bool:
        """Validate performance requirements."""
        self.log("Validating performance...")

        try:
            # Test loading performance
            start_time = time.time()
            motif_lookup = get_motif_lookup()
            load_time = time.time() - start_time

            if load_time > 0.050:  # 50ms requirement
                self.add_warning(f"Loading slow: {load_time:.3f}s (requirement: <50ms)")
            else:
                self.log(f"✓ Loading time: {load_time:.3f}s")

            # Test lookup performance
            start_time = time.time()
            for _ in range(1000):
                pattern = motif_lookup['human']['IGHJ']
            lookup_time = time.time() - start_time

            if lookup_time > 0.010:  # Should be very fast
                self.add_warning(f"Lookups slow: {lookup_time:.3f}s for 1000 lookups")
            else:
                self.log(f"✓ Lookup time: {lookup_time:.3f}s for 1000 lookups")

            self.results['performance'] = {
                'load_time': load_time,
                'lookup_time': lookup_time
            }

        except Exception as e:
            self.add_error(f"Performance validation failed: {e}")
            return False

        return True

    def validate_j_gene_integration(self) -> bool:
        """Validate integration with j_gene_data.py."""
        self.log("Validating j_gene_data integration...")

        try:
            from sadie.germlines.builders.j_gene_data import parse_j_gene, get_j_gene_data

            # Test parsing with new system
            sequence = 'TTTGGGACAAGGTGACCGTGATCCTCTGGACAGGCTACGGC'
            result = parse_j_gene('human', 'IGHJ1*01', sequence)

            if not isinstance(result, dict):
                self.add_error("J gene parsing failed - invalid return type")
                return False

            if result.get('not_implemented', True):
                self.add_error("J gene parsing failed - marked as not implemented for human")
                return False

            # Test j gene data retrieval
            rf, chain_type, cdr3_end, extra_bps = get_j_gene_data('IGHJ1*01', 'H')

            if not all(isinstance(x, int) for x in [rf, cdr3_end, extra_bps]):
                self.add_error("J gene data retrieval failed - invalid return types")
                return False

            if chain_type != 'JH':
                self.add_error(f"J gene data retrieval failed - expected 'JH', got '{chain_type}'")
                return False

            self.log("✓ j_gene_data integration validation complete")

        except Exception as e:
            self.add_error(f"j_gene_data integration validation failed: {e}")
            return False

        return True

    def run_comprehensive_validation(self) -> bool:
        """Run comprehensive validation using built-in utilities."""
        self.log("Running comprehensive validation...")

        try:
            raw_registry = _load_motif_registry()
            schema_path = project_root / "specs" / "001-germline-completion" / "contracts" / "motif-registry.schema.json"

            is_valid = comprehensive_motif_validation(raw_registry, schema_path)

            if not is_valid:
                self.add_error("Comprehensive validation failed")
                return False

            self.log("✓ Comprehensive validation complete")

        except Exception as e:
            self.add_error(f"Comprehensive validation failed: {e}")
            return False

        return True

    def generate_report(self) -> Dict[str, Any]:
        """Generate validation report."""
        return {
            'timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
            'validation_passed': len(self.errors) == 0,
            'error_count': len(self.errors),
            'warning_count': len(self.warnings),
            'errors': self.errors,
            'warnings': self.warnings,
            'results': self.results
        }

    def run_validation(self, verify_all: bool = False, performance: bool = False) -> bool:
        """Run migration validation."""
        self.log("Starting MOTIF_LOOKUP migration validation...")

        # Core validations (always run)
        validations = [
            ("File Structure", self.validate_file_structure),
            ("Data Loading", self.validate_data_loading),
            ("Backward Compatibility", self.validate_backward_compatibility),
            ("Data Integrity", self.validate_data_integrity),
        ]

        # Extended validations (optional)
        if verify_all:
            validations.extend([
                ("Schema Compliance", self.validate_schema_compliance),
                ("j_gene Integration", self.validate_j_gene_integration),
                ("Comprehensive Validation", self.run_comprehensive_validation),
            ])

        if performance:
            validations.append(("Performance", self.validate_performance))

        # Run validations
        all_passed = True
        for name, validation_func in validations:
            self.log(f"Running {name} validation...")
            try:
                passed = validation_func()
                if not passed:
                    all_passed = False
                    self.log(f"✗ {name} validation failed", "ERROR")
                else:
                    self.log(f"✓ {name} validation passed")
            except Exception as e:
                self.add_error(f"{name} validation crashed: {e}")
                all_passed = False

        # Generate summary
        if all_passed:
            self.log("✓ All validations passed - migration successful!", "INFO")
        else:
            self.log(f"✗ Migration validation failed with {len(self.errors)} errors", "ERROR")

        return all_passed


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate MOTIF_LOOKUP migration to JSON-based system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("Usage:")[1] if "Usage:" in __doc__ else ""
    )

    parser.add_argument(
        "--verify-all",
        action="store_true",
        help="Run comprehensive validation including schema compliance and integration tests"
    )

    parser.add_argument(
        "--performance",
        action="store_true",
        help="Run performance benchmarks"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )

    parser.add_argument(
        "--report-file",
        type=Path,
        help="Save validation report to JSON file"
    )

    args = parser.parse_args()

    # Run validation
    validator = MigrationValidator(verbose=args.verbose)
    success = validator.run_validation(
        verify_all=args.verify_all,
        performance=args.performance
    )

    # Generate report
    report = validator.generate_report()

    # Save report if requested
    if args.report_file:
        with open(args.report_file, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"Report saved to: {args.report_file}")

    # Print summary
    print("\n" + "="*60)
    print("MIGRATION VALIDATION SUMMARY")
    print("="*60)
    print(f"Status: {'PASSED' if success else 'FAILED'}")
    print(f"Errors: {len(validator.errors)}")
    print(f"Warnings: {len(validator.warnings)}")

    if validator.errors:
        print("\nErrors:")
        for i, error in enumerate(validator.errors, 1):
            print(f"  {i}. {error}")

    if validator.warnings:
        print("\nWarnings:")
        for i, warning in enumerate(validator.warnings, 1):
            print(f"  {i}. {warning}")

    if 'species_count' in validator.results:
        print(f"\nSpecies validated: {validator.results['species_count']}")

    if 'performance' in validator.results:
        perf = validator.results['performance']
        print(f"Load time: {perf['load_time']:.3f}s")
        print(f"Lookup time: {perf['lookup_time']:.3f}s")

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()