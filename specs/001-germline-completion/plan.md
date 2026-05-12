# Implementation Plan: MOTIF_LOOKUP Provenance & Coverage Testing

**Branch**: `001-motif-lookup-provenance` | **Date**: 2026-05-07 | **Spec**: [MOTIF-LOOKUP-PLAN.md](/Users/ckibet/project/sadie/MOTIF-LOOKUP-PLAN.md)
**Input**: MOTIF_LOOKUP provenance documentation and empirical coverage test implementation

**Note**: This focuses specifically on the MOTIF_LOOKUP implementation from the broader germlines module completion work.

## Summary

Document provenance and add empirical coverage testing for the J-gene FWR4 motif registry (`MOTIF_LOOKUP`). Move from inline Python dict to JSON with metadata, add `_provenance` fields for all 37 species, and implement regression tests to prevent motif accuracy degradation. This addresses user questions about motif reliability and origin while maintaining backward compatibility.

## Technical Context

**Language/Version**: Python 3.10 (required across all Sadie projects)
**Primary Dependencies**: json (stdlib), pathlib (stdlib), Biopython (sequence translation/parsing), pytest (≥8.0.0)
**Storage**: JSON files, FASTA sequence files (local filesystem)
**Testing**: pytest with existing SadieFixture framework, pytest-cov for coverage
**Target Platform**: Linux/macOS/Windows (cross-platform Python)
**Project Type**: single Python package (library component)
**Performance Goals**: JSON loading <50ms, coverage test execution <30 seconds for full test suite
**Constraints**: Backward compatibility required (public API unchanged), offline-first operation, <10MB additional storage
**Scale/Scope**: 37 species × 6 loci average = ~200 motif patterns, support for 10K+ J gene alleles per species in coverage testing

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Principle I (Provider-Based Architecture)**: ✅ **COMPLIANT** - MOTIF_LOOKUP is a data registry, not a provider. Does not violate provider architecture. Existing providers can reference motif data via the public API.

**Principle II (Priority-Based Merging)**: ✅ **COMPLIANT** - MOTIF_LOOKUP does not affect provider merging logic. It provides static reference data for FWR4 boundary detection used by existing germline processing.

**Principle III (Local-First Operation)**: ✅ **COMPLIANT** - Moving to JSON with local storage enhances local-first operation. No external API dependencies. All data stored locally with offline access.

**Principle IV (Staged Pipeline Architecture)**: ✅ **COMPLIANT** - MOTIF_LOOKUP sits in reference layer, consumed by germlines builders. Does not modify the sources → normalized → igblast pipeline stages.

**Principle V (Integration Compatibility)**: ✅ **COMPLIANT** - Explicitly maintains backward compatibility. Public API `MOTIF_LOOKUP` dict structure preserved. Existing consumer (`j_gene_data.py`) enhanced with provenance awareness but not breaking changes.

**Overall Assessment**: **PASS** - All constitutional principles satisfied. Implementation enhances existing functionality without architectural violations.

### Post-Design Re-evaluation (2026-05-07)

After completing Phase 1 design artifacts (data-model.md, contracts/, quickstart.md), constitutional compliance remains intact:

**Principle I (Provider-Based Architecture)**: ✅ **MAINTAINED** - Data model preserves provider independence. JSON schema validates motif registry without coupling to providers.

**Principle II (Priority-Based Merging)**: ✅ **MAINTAINED** - Provenance metadata does not affect germline merging priority. Motif patterns are reference data consumed by existing priority system.

**Principle III (Local-First Operation)**: ✅ **ENHANCED** - JSON file migration eliminates any remaining network dependencies. All provenance data stored locally with offline access guaranteed.

**Principle IV (Staged Pipeline Architecture)**: ✅ **MAINTAINED** - File migration from `germlines/builders/data/` to `reference/data/` clarifies boundaries. Reference layer clearly separated from pipeline stages.

**Principle V (Integration Compatibility)**: ✅ **VALIDATED** - Quickstart.md demonstrates backward compatibility preserved. Public API contract maintains exact `MOTIF_LOOKUP` structure while adding `MOTIF_PROVENANCE`.

**Design Risk Assessment**: **LOW** - JSON schema validation prevents data corruption. Coverage testing framework ensures empirical validation. No breaking changes to existing integrations.

## Project Structure

### Documentation (this feature)

```text
specs/001-germline-completion/
├── plan.md              # This file (implementation plan)
├── research.md          # Phase 0: JSON vs Python dict research, testing patterns
├── data-model.md        # Phase 1: MOTIF_LOOKUP data model with provenance
├── quickstart.md        # Phase 1: Usage guide for new MOTIF_PROVENANCE API
├── contracts/           # Phase 1: JSON schema for motif data validation
└── tasks.md             # Phase 2: Implementation task breakdown
```

### Source Code Changes

```text
src/sadie/reference/
├── settings.py          # MODIFIED: Replace MOTIF_LOOKUP dict with JSON loader
├── __init__.py          # MODIFIED: Export MOTIF_PROVENANCE in public API
└── data/               # NEW: Canonical location for motif JSON
    └── j_gene_motif.json # MOVED FROM: src/sadie/germlines/builders/data/

src/sadie/germlines/builders/
└── j_gene_data.py       # MODIFIED: Update path, add provenance awareness

tests/unit/reference/
└── test_motif_coverage.py  # NEW: Empirical coverage testing

src/sadie/germlines/sources/  # EXISTING: Used by coverage tests
├── imgt/{species}/          # FASTA files for validation
├── ogrdb/{species}/         # FASTA files for validation
└── vdjbase/{species}/       # FASTA files for validation
```

**Structure Decision**: Single Python package modification. Focus on reference data management within existing Sadie architecture. Leverages existing test framework and FASTA data sources for validation. JSON file centralized in reference module for clean API boundaries.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

**No constitutional violations identified.** All implementation approaches align with established principles. No complexity justification required.
