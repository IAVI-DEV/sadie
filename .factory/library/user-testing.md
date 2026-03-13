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
- `tests/unit/reference/test_reference.py::test_yaml` - count assertion drift (456 vs 479)
- `tests/unit/airr/test_airr.py::test_adaptable_correction` - pre-existing assertion failure
