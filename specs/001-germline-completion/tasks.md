# Tasks: MOTIF_LOOKUP Provenance & Coverage Testing

**Feature Branch**: `001-motif-lookup-provenance`
**Generated**: 2026-05-07
**Input**: Design documents from `/specs/001-germline-completion/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

## Overview

This document breaks down the MOTIF_LOOKUP implementation into actionable tasks organized by user story. Each user story phase is independently testable and delivers incremental value.

**Total Tasks**: 41
**Parallelizable Tasks**: 24
**User Stories**: 4 (3 × P1, 1 × P2)
**Estimated Duration**: 12-16 hours

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single Python package**: `src/sadie/`, `tests/` at repository root
- Paths shown below follow existing Sadie project structure

## Implementation Strategy

**MVP Scope**: User Story 1 (Document Motif Provenance)
- Delivers core value: answers user questions about motif origins
- Establishes provenance metadata framework
- Estimated: 3-4 hours

**Incremental Delivery**:
1. MVP (US1): Provenance documentation
2. Phase 2 (US2): Empirical coverage testing
3. Phase 3 (US3): Backward compatibility validation
4. Phase 4 (US4): Complete JSON migration

## Dependencies Graph

```
Phase 1 (Setup)
    ↓
Phase 2 (Foundational)
    ↓
├── US1 (P1) ← Independent (MVP)
├── US2 (P1) ← Uses US1 provenance data for thresholds
├── US3 (P1) ← Tests US1 changes for compatibility
└── US4 (P2) ← Validates all previous work
    ↓
Phase 7 (Polish)
```

**Parallel Execution Opportunities**:
- All user stories can start in parallel after foundational phase
- Within stories: provenance metadata, tests, and documentation can be parallel
- JSON validation and performance testing can be parallel

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and JSON migration infrastructure

- [X] T001 Create src/sadie/reference/data/ directory for canonical JSON location
- [X] T002 [P] Validate existing JSON schema structure in src/sadie/germlines/builders/data/j_gene_motif.json
- [X] T003 [P] Install jsonschema package for validation (already available via pytest ecosystem)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core JSON migration infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Move j_gene_motif.json from src/sadie/germlines/builders/data/ to src/sadie/reference/data/
- [X] T005 [P] Create JSON validation utilities in src/sadie/reference/validation.py
- [X] T006 [P] Add provenance metadata structure to JSON for all 37 species
- [X] T007 Implement JSON loader with provenance filtering in src/sadie/reference/settings.py

**Checkpoint**: JSON foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Document Motif Provenance (Priority: P1) 🎯 MVP

**Goal**: Answer user questions about motif pattern origins and reliability through comprehensive provenance metadata

**Independent Test**: User can import MOTIF_PROVENANCE, access source information for any species, and distinguish between IMGT-validated and legacy patterns

### Implementation for User Story 1

- [X] T008 [P] [US1] Add provenance metadata for human (IMGT-validated) in src/sadie/reference/data/j_gene_motif.json
- [X] T009 [P] [US1] Add provenance metadata for rat (IMGT-validated) in src/sadie/reference/data/j_gene_motif.json
- [X] T010 [P] [US1] Add provenance metadata for remaining 35 species (legacy) in src/sadie/reference/data/j_gene_motif.json
- [X] T011 [US1] Update src/sadie/reference/settings.py to load and filter provenance metadata
- [X] T012 [US1] Export MOTIF_PROVENANCE dict in src/sadie/reference/__init__.py
- [X] T013 [US1] Validate JSON structure against contracts/motif-registry.schema.json
- [X] T014 [US1] Add logging for motif registry loading operations

**Checkpoint**: At this point, User Story 1 should be fully functional - users can access provenance metadata independently

---

## Phase 4: User Story 2 - Add Empirical Coverage Testing (Priority: P1)

**Goal**: Implement regression tests that validate motif patterns against actual J gene sequences to ensure pattern accuracy

**Independent Test**: Coverage tests run successfully, showing match rates for each species/locus with clear pass/fail status based on validation thresholds

### Implementation for User Story 2

- [ ] T015 [P] [US2] Create test_motif_coverage.py framework in tests/unit/reference/
- [ ] T016 [P] [US2] Implement J gene sequence loader from FASTA sources in tests/unit/reference/test_motif_coverage.py
- [ ] T017 [P] [US2] Implement Biopython sequence translation utilities in tests/unit/reference/test_motif_coverage.py
- [ ] T018 [US2] Create parameterized test structure for species/locus combinations in tests/unit/reference/test_motif_coverage.py
- [ ] T019 [US2] Implement threshold-based validation (95% for IMGT-validated, 80% for legacy) in tests/unit/reference/test_motif_coverage.py
- [ ] T020 [US2] Add graceful handling for missing FASTA data (xfail/skip) in tests/unit/reference/test_motif_coverage.py
- [ ] T021 [US2] Generate coverage test reports matching contracts/coverage-test-result.schema.json format
- [ ] T022 [US2] Validate test results against JSON schema in tests/unit/reference/test_motif_coverage.py

**Checkpoint**: Coverage testing framework complete and validates current motif patterns against available data

---

## Phase 5: User Story 3 - Maintain Backward Compatibility (Priority: P1)

**Goal**: Ensure existing code continues to work unchanged while providing enhanced metadata access

**Independent Test**: Run existing Sadie test suite - all MOTIF_LOOKUP consumers should work without modification

### Implementation for User Story 3

- [ ] T023 [P] [US3] Update src/sadie/germlines/builders/j_gene_data.py path reference to new JSON location
- [ ] T024 [US3] Add backward compatibility validation in tests/unit/reference/test_motif_lookup.py
- [ ] T025 [US3] Test MOTIF_LOOKUP dict structure preservation in tests/unit/reference/test_motif_lookup.py
- [ ] T026 [US3] Test j_gene_data.py functionality with new JSON source in tests/unit/germlines/test_j_gene_data.py
- [ ] T027 [US3] Add integration test for full pipeline with new MOTIF_LOOKUP in tests/integration/test_motif_integration.py
- [ ] T028 [US3] Verify performance requirements (<50ms JSON loading) in tests/unit/reference/test_motif_performance.py

**Checkpoint**: All existing integrations confirmed working, no breaking changes introduced

---

## Phase 6: User Story 4 - JSON Migration & Data Quality (Priority: P2)

**Goal**: Complete migration to JSON-based system with comprehensive validation and quality assurance

**Independent Test**: JSON file validates against all schemas, data integrity checks pass, and migration is fully documented

### Implementation for User Story 4

- [ ] T029 [P] [US4] Add comprehensive JSON validation in src/sadie/reference/validation.py
- [ ] T030 [P] [US4] Create data integrity validation utilities in src/sadie/reference/validation.py
- [ ] T031 [US4] Implement regex pattern validation for all motifs in src/sadie/reference/validation.py
- [ ] T032 [US4] Add validation for all 37 species against contracts/motif-registry.schema.json
- [ ] T033 [US4] Create migration validation script in scripts/validate_motif_migration.py
- [ ] T034 [US4] Update quickstart.md with migration examples and new API usage
- [ ] T035 [US4] Add error handling for malformed JSON in src/sadie/reference/settings.py

**Checkpoint**: JSON migration complete with full validation and documentation

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories and final validation

- [ ] T036 [P] Add comprehensive docstrings to all new functions in src/sadie/reference/
- [ ] T037 [P] Update CHANGELOG.md with new MOTIF_PROVENANCE API and migration notes
- [ ] T038 Run full test suite validation (pytest tests/unit/reference/ tests/integration/)
- [ ] T039 Validate all JSON schemas against example data (contracts validation)
- [ ] T040 [P] Performance testing with large-scale coverage validation
- [ ] T041 Run quickstart.md examples validation for new API usage

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (US1 → US2 → US3 → US4)
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - Uses provenance data from US1 for test thresholds
- **User Story 3 (P1)**: Can start after Foundational (Phase 2) - Tests compatibility with US1 changes
- **User Story 4 (P2)**: Can start after Foundational (Phase 2) - Validates all previous work

### Within Each User Story

- Provenance metadata before API updates
- JSON structure before validation utilities
- Core implementation before integration tests
- Schema validation before performance testing
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- Provenance metadata for different species marked [P] can run in parallel
- Test implementations marked [P] can run in parallel
- Documentation updates marked [P] can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch provenance metadata tasks together:
Task: "Add provenance metadata for human (IMGT-validated) in src/sadie/reference/data/j_gene_motif.json"
Task: "Add provenance metadata for rat (IMGT-validated) in src/sadie/reference/data/j_gene_motif.json"
Task: "Add provenance metadata for remaining 35 species (legacy) in src/sadie/reference/data/j_gene_motif.json"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test provenance metadata access independently
5. Deliver answerable user questions about motif origins

### Incremental Delivery

1. Complete Setup + Foundational → JSON foundation ready
2. Add User Story 1 → Test independently → Deliverable: Provenance documentation
3. Add User Story 2 → Test independently → Deliverable: Empirical validation framework
4. Add User Story 3 → Test independently → Deliverable: Backward compatibility confirmed
5. Add User Story 4 → Test independently → Deliverable: Complete JSON migration
6. Each story adds value without breaking previous functionality

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (Provenance)
   - Developer B: User Story 2 (Coverage Testing)
   - Developer C: User Story 3 (Backward Compatibility)
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- JSON schema validation ensures data integrity throughout
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- 37 species scope provides comprehensive coverage
- Performance requirements: <50ms JSON loading, <30s test suite
- Backward compatibility is non-negotiable for existing API consumers

**Goal**: Enable bioinformaticians in air-gapped environments to annotate sequences without internet

**Independent Test**: Populate data once, disconnect network, run full Sadie pipeline successfully

**Duration**: 2-3 hours

**Prerequisites**: Phase 3 (US1), Phase 4 (US6) complete

### US2 Tasks

- [X] T035 [US2] Verify pipeline operates without network calls in src/sadie/germlines/pipeline.py
- [X] T036 [US2] Add offline mode detection and logging in src/sadie/germlines/pipeline.py
- [X] T037 [US2] Implement clear error messages for missing data in src/sadie/germlines/providers/base.py
- [X] T038 [US2] Add README references in error messages for data population in src/sadie/germlines/manager.py
- [X] T039 [P] [US2] Write offline integration test (network disabled) in src/sadie/germlines/tests/test_offline_operation.py
- [X] T040 [US2] Verify cached data usage (6 months old) works correctly in src/sadie/germlines/pipeline.py

**Acceptance Criteria**:
- [X] IMGT and OGRDB data populated in src/sadie/germlines/sources/
- [X] Sadie annotation completes without internet access
- [X] Empty src/sadie/germlines/sources/ gives clear error with remediation steps
- [X] Pipeline uses cached data without update checks

---

## Phase 6: User Story 4 - Integrate with Existing Sadie Workflows (P1)

**Goal**: Ensure existing Sadie users' workflows work transparently with new germlines module

**Independent Test**: Run existing Sadie IgBLAST test suite, all tests pass without modification

**Duration**: 4-5 hours

**Prerequisites**: Phase 3 (US1) complete

### US4 Tasks

- [X] T041 [US4] Update IgBLAST germline paths to new module structure in src/sadie/airr/igblast/germline.py
- [X] T042 [US4] Add feature flag check to IgBLAST integration in src/sadie/airr/igblast/germline.py
- [X] T043 [US4] Update Reference system to query germlines module in src/sadie/reference/reference.py
- [X] T044 [US4] Implement G3 API response format adapter (regions fields) in src/sadie/reference/reference.py
- [X] T045 [US4] Add feature flag check to Reference system in src/sadie/reference/reference.py
- [X] T046 [US4] Update HMM builder to use germlines module in src/sadie/renumbering/aligners/hmmer.py
- [X] T047 [US4] Add feature flag check to HMM builder in src/sadie/renumbering/aligners/hmmer.py
- [X] T048 [US4] Verify gapped sequences available for Stockholm alignment in src/sadie/germlines/builders/gapper.py
- [X] T049 [P] [US4] Run existing Sadie IgBLAST test suite (regression test)
- [X] T050 [P] [US4] Test feature flag SADIE_USE_GERMLINES_MODULE=false (G3 mode)
- [X] T051 [US4] Document backward compatibility approach in src/sadie/germlines/INTEGRATION_GUIDE.md

**Acceptance Criteria**:
- [X] `GermlineData("human")` resolves to new database locations
- [X] Reference system returns G3-compatible format
- [X] HMM builder gets gapped sequences successfully
- [X] Feature flag=false falls back to G3 without errors

---

## Phase 7A: User Story 3 - Priority-Based Database Selection (P2)

**Goal**: Allow researchers to use OGRDB preferentially over IMGT with fallback

**Independent Test**: Configure `["ogrdb", "imgt"]`, run annotation, verify OGRDB used when present, IMGT for missing genes

**Duration**: 1-2 hours

**Prerequisites**: Phase 2 complete (independent from US1)

### US3 Tasks

- [X] T052 [P] [US3] Verify priority ordering logic in GermlineManager in src/sadie/germlines/manager.py
- [X] T053 [P] [US3] Write unit test for priority ordering scenarios in src/sadie/germlines/tests/test_priority_ordering.py
- [X] T054 [P] [US3] Test deduplication rules (same name, same sequence, novel) in src/sadie/germlines/tests/test_priority_ordering.py
- [X] T055 [US3] Document priority configuration in src/sadie/germlines/README.md
- [X] T056 [US3] Add logging for priority-based gene selection in src/sadie/germlines/manager.py

**Acceptance Criteria**:
- [X] Both OGRDB and IMGT have IGHV1-69*01, OGRDB version used with priority `["ogrdb", "imgt"]`
- [X] Gene in IMGT but not OGRDB is included in merged database
- [X] Two providers with same sequence but different names keeps both

---

## Phase 7B: User Story 5 - Add VDJbase Provider (P2)

**Goal**: Enable researchers to use VDJbase genotype data for population-specific analysis

**Independent Test**: Populate VDJbase sample data, configure `["vdjbase", "imgt"]`, verify VDJbase sequences used

**Duration**: 2-3 hours

**Prerequisites**: Phase 2 complete (independent from US1)

### US5 Tasks

- [X] T057 [P] [US5] Complete VDJbase provider implementation in src/sadie/germlines/providers/vdjbase.py
- [X] T058 [P] [US5] Add VDJbase to default provider list in src/sadie/germlines/manager.py (verified: manager.py DEFAULT_PROVIDERS includes vdjbase, __init__.py exports VDJbaseProvider, data exists for human/rhesus_macaque)
- [X] T059 [P] [US5] Write unit tests for VDJbase provider in src/sadie/germlines/tests/test_vdjbase_provider.py
- [X] T060 [P] [US5] Create VDJbase test data in src/sadie/germlines/tests/data/vdjbase/human/
- [X] T061 [US5] Test VDJbase in priority ordering in src/sadie/germlines/tests/test_priority_ordering.py
- [X] T062 [US5] Add VDJbase error handling for format changes in src/sadie/germlines/providers/vdjbase.py

*Note: T063 removed - duplicates T030 (VDJbase README created in Phase 4)*

**Acceptance Criteria**:
- [X] VDJbase FASTA files in src/sadie/germlines/sources/vdjbase/human/ are parsed successfully
- [X] VDJbase allele used instead of IMGT when priority includes vdjbase first
- [X] Format errors show clear message with documentation link

---

## Phase 8: Polish & Cross-Cutting Concerns

**Goal**: Finalize integration, testing, and documentation

**Duration**: 3-4 hours

**Prerequisites**: All user story phases complete

### Polish Tasks

- [ ] T064 Run full Sadie test suite and ensure 100% pass rate
- [ ] T065 Verify SC-001: Custom germline injection in <5 minutes (stopwatch test)
- [ ] T066 Verify SC-002: Offline operation works (network disabled test)
- [ ] T067 Verify SC-003: Download scripts <10 minutes for human (timing test)
- [ ] T068 Verify SC-005: Disk usage <500MB for human data (du -sh test)
- [ ] T069 Verify SC-009: Change detection triggers rebuild correctly (file modification test)
- [ ] T070 Verify SC-010: Clear error messages for all failure modes (error handling review)
- [ ] T071 Verify SC-011: Timing metrics logged for major operations (log inspection)
- [ ] T072 Verify SC-012: CI tests complete in <5 minutes (GitHub Actions check)
- [X] T073 Update main germlines README with completion status in src/sadie/germlines/README.md
- [X] T074 Update INTEGRATION_GUIDE with actual integration points in src/sadie/germlines/INTEGRATION_GUIDE.md
- [X] T075 Add performance profiling for critical paths in src/sadie/germlines/pipeline.py
- [ ] T076 Run pre-commit hooks and fix any linting issues
- [ ] T077 Update CHANGELOG or release notes with germlines module completion
- [ ] T099 Benchmark rebuild time (<2 minutes for human dataset) and record timing logs to satisfy SC-001/SC-011 in specs/001-germline-completion/validation-tracking.md

### Supplemental Tasks (Added 2026-01-15)

The following tasks were added after initial task generation to address IgBLAST auxiliary requirements (FR-037-039) and logging standardization (FR-032, FR-035, FR-036).

- [X] T078 [P] Complete AuxFileBuilder CDR/FWR boundary detection and IgBLAST format output in src/sadie/germlines/builders/aux.py
- [X] T079 [P] Update BlastDBBuilder to use -hash_index and validate output naming/paths per FR-038/FR-038a in src/sadie/germlines/builders/blast.py
- [X] T080 [P] Generate igblast/internal_data/organism.yaml per FR-039/FR-039a in src/sadie/germlines/pipeline.py
- [X] T081 [P] Enforce structured logging format and key-value fields per FR-032a/FR-032b in src/sadie/germlines/__init__.py
- [X] T082 [P] Add change-detection log details (path/hash/change type) per FR-035a in src/sadie/germlines/pipeline.py
- [X] T083 [P] Standardize error message templates per FR-036a/FR-036b in src/sadie/germlines/providers/*.py and src/sadie/germlines/builders/blast.py
- [X] T084 [P] Add legacy GermlineData API compatibility tests in src/sadie/germlines/tests/test_germline_data_legacy.py
- [X] T085 [P] Add regression tests comparing germlines vs G3 output in src/sadie/germlines/tests/test_g3_regression.py
- [X] T086 [P] Replace .specify/memory/constitution.md placeholder with actual constitution text
- [X] T087 [US4] Create validation period tracking document at specs/001-germline-completion/validation-tracking.md with: start date, release count, bug tracker, performance baseline comparison template
- [X] T088 [US4] Add deprecation warning log when SADIE_USE_GERMLINES_MODULE=false: "G3 API is deprecated. Set SADIE_USE_GERMLINES_MODULE=true. G3 will be removed after {date}."
- [X] T089 [P] [US6] Verify OGRDB provider correctly loads _gapped.fasta files alongside ungapped files in src/sadie/germlines/providers/ogrdb.py
- [X] T092 [US4] Enforce validation period per FR-017a/b: track start/end, release counts, success criteria, and deprecation notice schedule; log metrics and update validation-tracking.md
- [X] T100 [P] Consolidate G3 regression parity into a single test at src/sadie/germlines/tests/test_g3_regression.py (supersedes T004b and T085)
- [X] T101 [P] Implement HMM builder for Stockholm alignment generation per FR-013a-c in src/sadie/germlines/builders/hmm.py

### Backlog (Post-Validation Period)

These tasks execute after validation period success criteria (FR-017b) are met:

- [ ] T-BACKLOG-001 Issue deprecation notice per FR-019a (CHANGELOG entry, GitHub discussion, runtime warning active)
- [ ] T-BACKLOG-002 Remove G3 dependencies per FR-019b (src/sadie/renumbering/clients/g3.py, all G3 imports, feature flag code, G3-related tests)

---

## Parallel Execution Plan

### Within Phases (Independent Work)

**Phase 1 Setup**:
- T003, T004 (test data) parallel with T001, T002 (directories)

**Phase 2 Foundational**:
- T009 (gapper), T010 (logging), T011 (manager update), T015 (timing) - all parallel
- New: T091 (normalized outputs), T094 (AA→codon gapping), T095 (utility reuse) can run in parallel with T009/T015

**Phase 3 US1**:
- T020, T021 (tests) parallel with T023 (docs)

**Phase 4 US6**:
- T030, T031, T032 (documentation) - all parallel
- New: T090 (OGRDB resume) and T093 (logging cadence) parallel with T026 (IMGT resume)

**Phase 7 (Independent Stories)**:
- US3 (T052-T056) and US5 (T057-T063) can be done in parallel

### Across Phases (Team Distribution)

```
Developer 1: US1 → US2 → US4
Developer 2: US6 → US3 → US5
 Developer 3: Phase 1 → Phase 2 → Phase 8 (support + polish; owns T096-T098 deliverables and T099 benchmark)
```

---

## Testing Strategy

### Unit Tests

- Test each provider in isolation with curated test dataset
- Test priority ordering with various configurations
- Test gapping service with sample sequences
- Test feature flag toggling

### Integration Tests

- End-to-end custom sequence addition
- Full pipeline with multiple providers
- Offline operation (network disabled)
- Feature flag mode uses G3 when false (no automatic fallback)

### Regression Tests

- Existing Sadie IgBLAST test suite
- Reference system compatibility
- HMM builder with new paths

**Test Data**: Curated dataset in `src/sadie/germlines/tests/data/` with 5-10 genes per segment covering edge cases

---

## Success Metrics Checklist

From spec.md success criteria (SC-001 to SC-015):

- [ ] SC-001: Custom germline in <5 minutes (T065)
- [ ] SC-002: Offline operation works (T066)
- [ ] SC-003: Download scripts <10 minutes (T067)
- [ ] SC-004: 100% test pass rate (T064)
- [ ] SC-005: <500MB disk usage (T068)
- [ ] SC-006: Priority ordering verified (T053, T054)
- [ ] SC-007: Feature flag works (T050)
- [ ] SC-008: Setup in <30 minutes (user testing post-release)
- [ ] SC-009: Change detection works (T069)
- [ ] SC-010: Clear error messages (T070)
- [ ] SC-011: Timing metrics logged (T071)
- [ ] SC-012: CI tests <5 minutes (T072)
- [ ] SC-013-015: Qualitative (code review + user testing)

---

## Risk Mitigation Checklist

- [ ] Biopython gapping accuracy: T009 aligns to IMGT templates; fallback to ungapped on failure
- [ ] VDJbase format changes: T062 adds error handling with clear remediation
- [ ] G3 parity: T044 adapter maintains format, T050 tests G3 mode
- [ ] Test data completeness: T004 curated dataset, documented limitations
- [ ] Performance: T075 profiling, T065 <5min verification

---

## Notes for Implementation

**MVP First**: Implement US1 + US6 first for fastest time-to-value

**Test Coverage**: Unit tests cover ~80% with curated test dataset; full-scale testing with complete reference data done manually

**Feature Flag Timeline**:
1. Initial: SADIE_USE_GERMLINES_MODULE=true (default), G3 available via feature flag (no automatic fallback)
2. Validation period: Monitor usage, collect feedback
3. Deprecation: Announce G3 removal timeline
4. Removal: Delete G3 client code after validation complete

**Documentation**: Update germlines README and INTEGRATION_GUIDE as implementation progresses, not just at end

---

**Generated**: 2026-01-08
**Total Duration Estimate**: 24-28 hours
**MVP Estimate**: 8-10 hours (US1 + US6)
