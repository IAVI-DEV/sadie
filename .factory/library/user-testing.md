# User Testing

Testing surface, resource cost classification, and validation approach.

**What belongs here:** How to validate user-facing functionality, testing tools, resource constraints.

---

## Validation Surface

### Surface 1: pytest
- **Tool**: `poetry run pytest`
- **What it tests**: Unit tests, integration tests, migration/parity tests
- **Setup**: `poetry install --with dev` (already done via init.sh)
- **Key commands**:
  - `poetry run pytest tests/unit/reference/ -x --tb=short` (reference module)
  - `poetry run pytest tests/unit/germlines/ -x --tb=short` (germlines module)
  - `poetry run pytest tests/unit/airr/ -x --tb=short` (airr module)
  - `poetry run pytest tests/integration/ -x --tb=short` (integration)
  - `poetry run pytest tests/migration/ -x --tb=short` (migration parity)

### Surface 2: CLI Commands
- **Tool**: Shell execution
- **What it tests**: `sadie reference generate`, `sadie germlines rebuild`, `sadie germlines status`
- **Setup**: Poetry environment activated
- **Key commands**:
  - `poetry run sadie reference generate --help`
  - `poetry run sadie germlines rebuild --species human`
  - `poetry run sadie germlines status`

### Surface 3: Python API
- **Tool**: Python script execution
- **What it tests**: `Airr("human", providers=[...]).run_single(seq)` 
- **Setup**: Poetry environment
- **Key pattern**: Write a small Python script, run with `poetry run python script.py`

## Validation Concurrency

- Machine: 128GB RAM, 16 cores
- pytest runs are CPU-bound (IgBLAST compilation + annotation)
- Each test run uses ~500MB RAM
- Max concurrent validators: **5** (plenty of headroom)

## Pre-Existing Test Failures

These failures exist before this mission and should be noted but not fixed:
- `tests/unit/airr/test_airr.py::test_adaptable_correction` - pre-existing assertion failure
- `tests/unit/airr/test_airr.py::test_hard_igl_seqs` - pre-existing failure
- `tests/unit/airr/test_airr.py::test_source_lookup_method` - pre-existing cache identity assertion failure
- `tests/unit/germlines/test_airr_integration.py::test_source_lookup_method` - pre-existing failure
- `tests/unit/reference/test_reference.py::test_make_from_empty` - pre-existing G3 API unavailable
- `tests/unit/reference/test_reference.py::test_cli` - pre-existing failure
- `tests/unit/reference/test_reference.py::test_reference_class` - pre-existing failure
- `tests/migration/test_valid_parity.py::test_mixed_source_parity` - pre-existing 1-char diff in germline_alignment

## Flow Validator Guidance: pytest-cli

**Surface**: pytest + CLI (shell execution). No web browser or TUI needed.

**Isolation rules**:
- Each validator should run tests in the same repo checkout (`/Users/tmsincomb/sadie`)
- pytest tests are read-only against the source code (they use tmp_path for writes)
- CLI tests use `--output <tmp_path>` flags to avoid writing to the repo
- Validators can run concurrently safely since tests use isolated tmp dirs
- Do NOT run `sadie reference generate` without `--output <tmp_path>` to avoid mutating the repo

**Testing approach**:
- Run specific test files/functions that correspond to the assigned assertion IDs
- For each assertion, run the corresponding test and check exit code + output
- Report pass/fail for each assertion based on test results
- Capture stderr/stdout as evidence

**Test file mapping**:
- VAL-DUP-001, VAL-DUP-002, VAL-DUP-003 → `tests/unit/reference/test_duplicate_handling.py`
- VAL-GEN-001 through VAL-GEN-005, VAL-GEN-007 → `tests/unit/reference/test_auto_generation.py`
- VAL-CLI-003 → `tests/unit/reference/test_generate_cli.py`
- VAL-CLEAN-001 → `tests/unit/reference/test_generate_cli.py::TestOldReferenceYmlDeleted`
- VAL-CLEAN-002 → `tests/unit/reference/test_generate_cli.py::TestReferenceG3YmlPreserved`
- VAL-CLEAN-003 → `tests/migration/test_valid_parity.py::test_airr_parity` (uses reference.g3.yml)

**Known pre-existing failures** (ignore these):
- `test_mixed_source_parity` - pre-existing 1-char diff in germline_alignment
- `test_adaptable_correction`, `test_hard_igl_seqs`, `test_source_lookup_method` in airr tests

**IMPORTANT**: Reference tests (auto_generation, generate_cli) can take 30-120 seconds since they exercise the full germline manager loading IMGT/OGRDB/VDJbase data.

### Unified-Pipeline Milestone Test Mapping

**Cache assertions (VAL-CACHE-001 through VAL-CACHE-008)**:
- VAL-CACHE-001 → `tests/unit/reference/test_cache.py::TestCacheHitMiss::test_cache_hit_with_sentinel` + `TestPartialCompilationSafety::test_build_and_cache_writes_sentinel_on_success`
- VAL-CACHE-002 → `tests/unit/reference/test_cache.py::TestCacheSecondCallSkipsCompilation`
- VAL-CACHE-003 → `tests/unit/reference/test_cache.py::TestComputeCacheKey::test_different_providers_produce_different_keys` + `TestCacheHitMiss::test_different_providers_produce_different_cache_entries`
- VAL-CACHE-004 → `tests/unit/reference/test_cache.py::TestComputeCacheKey::test_different_config_content_produces_different_keys` + `TestCacheInvalidation`
- VAL-CACHE-005 → `tests/unit/reference/test_cache.py::TestDatabaseCacheDefaults::test_custom_cache_dir_via_constructor` + `test_custom_cache_dir_via_env_var`
- VAL-CACHE-006 → `tests/unit/reference/test_cache.py::TestDatabaseCacheDefaults::test_default_cache_location`
- VAL-CACHE-007 → `tests/unit/reference/test_cache.py::TestCacheAutoCreation`
- VAL-CACHE-008 → `tests/unit/reference/test_cache.py::TestPartialCompilationSafety`

**Unified Airr pipeline assertions (VAL-AIRR-001 through VAL-AIRR-008)**:
- VAL-AIRR-001 → `tests/unit/airr/test_unified_pipeline.py::TestUnifiedPipelineRouting`
- VAL-AIRR-002 → `tests/unit/airr/test_unified_pipeline.py::TestDatabaseParamBackwardCompat`
- VAL-AIRR-003 → `tests/unit/airr/test_unified_pipeline.py::TestAnnotationCorrectness`
- VAL-AIRR-004 → `tests/unit/airr/test_unified_pipeline.py::TestProviderPriority`
- VAL-AIRR-005 → `tests/unit/airr/test_unified_pipeline.py::TestSourceColumns`
- VAL-AIRR-006 → `tests/unit/airr/test_unified_pipeline.py::TestReferencesParamBackwardCompat`
- VAL-AIRR-007 → `tests/unit/airr/test_unified_pipeline.py::TestNonHumanSpecies`
- VAL-AIRR-008 → `tests/unit/airr/test_unified_pipeline.py::TestPartialProviderCoverage`

**Error handling assertions (VAL-ERR-001, VAL-ERR-002)**:
- VAL-ERR-001 → `tests/unit/airr/test_unified_pipeline.py::TestErrorHandling::test_unknown_species_raises_error`
- VAL-ERR-002 → `tests/unit/airr/test_unified_pipeline.py::TestErrorHandling::test_unpopulated_germlines_raises_error`

**Auto-generation assertions (VAL-GEN-006, VAL-GEN-007)**:
- VAL-GEN-006 → `tests/unit/airr/test_unified_pipeline.py::TestCacheIntegration::test_auto_generates_reference_if_missing`
- VAL-GEN-007 → `tests/unit/reference/test_auto_generation.py::TestReferenceYamlAutoGeneration::test_output_loadable_by_references_from_yaml`

**CLI assertions (VAL-CLI-001, VAL-CLI-002)**:
- VAL-CLI-001 → `tests/unit/germlines/test_rebuild_cli.py::TestRebuildUsesReferenceModule` (all tests)
- VAL-CLI-002 → `tests/unit/germlines/test_rebuild_cli.py::TestPopulateUnchanged`

**Cross-area flow assertions (VAL-CROSS-001 through VAL-CROSS-003)**:
- VAL-CROSS-001 → Run sequential: `sadie reference generate --output <tmp>` → verify YAML → run Airr("human").run_single(seq) → verify results
- VAL-CROSS-002 → `tests/unit/airr/test_unified_pipeline.py::TestAnnotationCorrectness::test_human_annotation_with_imgt_default` (tests full pipeline)
- VAL-CROSS-003 → `tests/unit/reference/test_cache.py::TestCacheInvalidation::test_config_change_invalidates_cache`
