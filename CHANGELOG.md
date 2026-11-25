# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **OGRDB germline database updated** to Zenodo record `23947887` (published 2026-11-04).
  Version is now tracked by Zenodo record ID (`release-23947887`) and auto-checked on each
  `sadie germlines populate` run.

  **Human** — constant-region isotype genes added for the first time:

  | Locus | Sequences |
  |-------|-----------|
  | IGHV  | 209       |
  | IGKV  | 82        |
  | IGLV  | 88        |
  | IGHD  | 33        |
  | IGHJ  | 7         |
  | IGKJ  | 7         |
  | IGLJ  | 10        |
  | IGHC  | 338 *(IGHA×102, IGHE×36, IGHG×152, IGHM×28, IGHD-delta×20)* |

  **Mouse** — strain-specific alleles now fully populated across 45 germline sets covering
  18 inbred strains (AKR/J, A/J, 129S1/SvImJ, BALB/c/ByJ, C3H/HeJ, C57BL/6J, CAST/EiJ,
  CBA/J, DBA/1J, DBA/2J, LEWES/EiJ, MRL/MpJ, MSM/MsJ, NOD/ShiLtJ, NOR/LtJ, NZB/BlNJ,
  PWD/PhJ, SJL/J):

  | Locus | Sequences |
  |-------|-----------|
  | IGHV  | 691       |
  | IGKV  | 1,580     |
  | IGLV  | 63        |
  | IGHD  | 66        |
  | IGHJ  | 28        |
  | IGKJ  | 11        |
  | IGLJ  | 7         |

- **Custom mouse provider** — 29 strain-specific S-alleles (`IGHV1S*`, `IGKV6-B/C/D*01`,
  etc.) extracted from bundled G3 reference data and registered under
  `sources/custom/mouse/`; `reference.yml` mouse section restored to 635 genes.

### Changed

- **OGRDB human and mouse data re-parsed, not re-versioned** (2026-11-24). Same Zenodo record
  `23947887` and the same API sets: human IGH_VDJ v10, IGKappa_VJ v5, IGLambda_VJ v4 and IGHC v1.
  Made with `sadie germlines populate -p ogrdb --force` and `sadie germlines rebuild -s human -s mouse`.
  The downloader now keeps only archive rows that a published germline set lists, and an API record
  replaces an archive record with the same name or sequence. The sources now equal the published
  API sets, one record per API name.

  | Species | File | Before | After | Added | Removed | Sequence changed |
  |---------|------|--------|-------|-------|---------|------------------|
  | human   | IGHV | 229    | 209   | 0     | 20      | 0                |
  | human   | IGKV | 83     | 82    | 0     | 1       | 0                |
  | human   | IGHC | 328    | 338   | 10    | 0       | 0                |
  | mouse   | IGHV | 1,117  | 691   | 0     | 426     | 0                |
  | mouse   | IGKV | 2,810  | 1,580 | 0     | 1,230   | 0                |
  | mouse   | IGLV | 66     | 63    | 0     | 3       | 0                |
  | mouse   | IGHD | 132    | 66    | 0     | 66      | 0                |
  | mouse   | IGHJ | 56     | 28    | 0     | 28      | 0                |
  | mouse   | IGKJ | 22     | 11    | 0     | 11      | 0                |
  | mouse   | IGLJ | 14     | 7     | 0     | 7       | 0                |

  Human IGHD, IGHJ, IGKJ, IGLV and IGLJ are unchanged. Macaque was not re-downloaded.

  - Human: the 21 removed records are inferred `*i` alleles that no published germline set lists.
    16 are superseded and 1 is withdrawn. 4 are published but in no set (`IGHV1-69*i01`,
    `IGHV4-61*i01`, `IGHV2-70*i02`, `IGKV3-15*i01`).
  - Human: in `human_V`, 11 of them carried the sequence of a current allele that VDJbase supplies
    1-2 nt longer under its current name (for example `IGHV3-7*i01` = `IGHV3-7*04`).
    `human_V` goes from 1,539 to 1,518 records.
  - Human: the 10 IgD `_SC` constant records are added. `human_C` goes from 400 to 409 records.
    `IGHD*04_c620t_SC` has the sequence of `IGHD*02_a987g_SC`, so 9 add a new sequence.
  - Human: `IGHG4D*01_d171` and `IGHG4*01_c20g_c56t_c188t_a314g_g338a` have the same sequence.
    The records now follow the API order, so `human_C` keeps the second name.
  - Mouse: every removed record was an archive label (`IGKV-XXXX`) for a sequence that the API
    names `IGKV0-XXXX*00`. `mouse_V` keeps 1,652 records and the same sequences. 797 V, 19 D and
    24 J names change to API names.
  - Mouse: two API names stand for two sequences each (`IGKV0-YKPT*00`, `IGKV0-KA5D*00`). One
    record ships per name. The PWD/PhJ `IGKV0-KA5D*00` sequence (287 nt) ships under no name, as
    before.
  - `reference.yml` OGRDB lists: human 732 to 728 names. Mouse keeps 1,176 names, and 840 change.
  - The Added tables above now give the re-parsed counts. They said human IGHD 53. The shipped
    file had 33, and the API set has 33.

- **`sadie germlines populate`** — OGRDB now auto-detects new Zenodo releases at run time;
  `is_up_to_date()` compares Zenodo record IDs rather than calendar month.

### Added
- **MOTIF_PROVENANCE API**: New provenance metadata system for J-gene FWR4 motif patterns
  - Access pattern origins and validation status via `sadie.reference.MOTIF_PROVENANCE`
  - Distinguish between IMGT-validated (2 species) and legacy patterns (35 species)
  - Comprehensive metadata including source, last_reviewed date, and validation status

- **JSON-based MOTIF_LOOKUP**: Migrated from Python dict to JSON with enhanced capabilities
  - Centralized motif registry in `src/sadie/reference/data/j_gene_motif.json`
  - Schema validation with `specs/001-germline-completion/contracts/motif-registry.schema.json`
  - Backward compatibility maintained - existing code continues to work unchanged

- **Empirical Coverage Testing**: Framework for validating motif patterns against real sequences
  - Test suite in `tests/unit/reference/test_motif_coverage.py`
  - Species-specific thresholds: 95% for IMGT-validated, 80% for legacy patterns
  - Biopython integration for sequence validation
  - JSON schema-compliant coverage reports

- **Migration Validation Tools**: Comprehensive validation and migration tools
  - Migration validation script: `scripts/validate_motif_migration.py`
  - Schema validation for all 37 species
  - Performance benchmarking and regression testing
  - Integration testing with existing j_gene_data module

- **Enhanced Error Handling**: Improved error messages and data integrity validation
  - Helpful error messages for missing species with suggestions
  - Comprehensive JSON validation and structure checks
  - Graceful handling of malformed data
  - Performance-optimized loading with caching

### Changed
- **j_gene_data.py**: Updated to use centralized motif lookup from `sadie.reference`
  - Removed local JSON loading code
  - Improved integration with new provenance system
  - Maintained all existing functionality

### Technical Details
- **Species Coverage**: Support for 37 species with comprehensive motif patterns
- **Performance**: <50ms loading time, cached for subsequent access
- **Compatibility**: Full backward compatibility via `_MotifLookupProxy` class
- **Validation**: 17 test classes with comprehensive coverage validation
- **Documentation**: Updated quickstart guide with migration examples

### Migration Guide

#### For Existing Users (No Changes Required)
```python
# This code continues to work unchanged
from sadie.reference import MOTIF_LOOKUP

pattern = MOTIF_LOOKUP['human']['IGHJ']  # Still works exactly the same
```

#### For New Features
```python
# New provenance API
from sadie.reference import MOTIF_LOOKUP, MOTIF_PROVENANCE

# Check if patterns are validated
human_prov = MOTIF_PROVENANCE['human']
if human_prov['imgt_validated']:
    pattern = MOTIF_LOOKUP['human']['IGHJ']  # High confidence
    print(f"IMGT-validated pattern from: {human_prov['source']}")
```

#### Validation Tools
```bash
# Validate complete migration
python scripts/validate_motif_migration.py --verify-all

# Run empirical coverage tests
pytest tests/unit/reference/test_motif_coverage.py -v
```

### Compatibility
- ✅ **Python 3.10+**: Full compatibility maintained
- ✅ **Existing API**: No breaking changes to `MOTIF_LOOKUP` usage
- ✅ **j_gene_data.py**: Seamless integration with updated module
- ✅ **Performance**: <50ms loading requirement met
- ✅ **Testing**: All existing tests continue to pass

### Dependencies
- **BioPython**: Required for empirical coverage testing (optional feature)
- **jsonschema**: Required for schema validation (development/testing)
- **pytest**: Required for running test suite

---

## Development Notes

This release implements the complete MOTIF_LOOKUP provenance and coverage testing system as specified in the project requirements. The implementation maintains full backward compatibility while adding comprehensive metadata tracking and empirical validation capabilities.

Key architectural decisions:
1. **JSON-first approach**: Central registry with schema validation
2. **Backward compatibility**: Proxy pattern preserves existing API
3. **Performance optimization**: Lazy loading with caching
4. **Comprehensive testing**: 60+ test cases covering all aspects
5. **Production readiness**: Full error handling and validation

The system supports 37 species with over 130 motif patterns, providing a solid foundation for J-gene FWR4 boundary detection across diverse biological systems.
