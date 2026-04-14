# User Testing

## Validation Surface

This is a Python library with no web UI. The testing surface is:
- **pytest**: Primary validation tool. All assertions are verified by running pytest tests.
- **CLI**: `sadie airr`, `sadie renumbering` commands can be used for spot checks.

No browser testing, no services to start.

## Validation Concurrency

- **Surface: pytest** — Max concurrent validators: 5
  - Machine: 128GB RAM, 16 cores
  - pytest uses minimal resources (~200MB per test process)
  - No services to run alongside tests
  - Tests are CPU-bound (HMM alignment), not I/O-bound

## Testing Tools

- `poetry run pytest` — test runner
- `poetry run pytest -v` — verbose output
- `poetry run pytest -k "test_name"` — specific test
- `poetry run pytest tests/unit/renumbering/test_species_contract.py` — species contract tests
- `poetry run pytest -o addopts='' --ignore=tests/unit/renumbering/test_renumbering.py --ignore=tests/migration/ --no-header` — AGENTS-approved full-suite command for milestone-level validation when pre-existing exclusions apply

## Known Constraints

- Tests requiring germline databases may skip if `sadie germlines populate` hasn't been run
- Some tests are gated behind `skip_no_macaque`/`skip_no_mouse` fixtures
- `tests/conftest.py:get_monkey_edge_seq()` is a macaque lambda/light-chain sequence, not a VH/heavy-chain fixture
- Legacy ANARCI HMMs exist at `src/sadie/renumbering/data/anarci/HMMs/` and should not be modified
- Guard-rail tests for intentionally unsupported species/chain pairs may print `Local HMM builder failed ... Falling back to G3/Numbering` warnings before the expected `ValueError` is asserted; if the targeted pytest command exits `0` and the descriptive-error tests pass, treat those warnings as expected friction rather than assertion failure.

## Flow Validator Guidance: pytest

- Use `poetry run pytest` for all validation commands.
- For assertion-specific checks, run only targeted tests that map to the assigned assertions.
- For milestone-level "full suite" assertions, use the AGENTS-approved command `poetry run pytest -o addopts='' --ignore=tests/unit/renumbering/test_renumbering.py --ignore=tests/migration/ --no-header`.
- Treat the repository as read-only except for writing the assigned flow report JSON and evidence files in the provided paths.
- Stay inside the shared project checkout at `/Users/tmsincomb/sadie`; do not create copies or alternate worktrees.
- Running targeted pytest commands concurrently is safe on this machine. Avoid mutating caches/config and do not install dependencies or edit source files.
- Do not run the milestone-level full-suite command concurrently with other pytest validators.
- Long-running milestone-level pytest commands may outlast the `user-testing-flow-validator` inactivity window; if that happens, run the full-suite command via direct `Execute`/background monitoring from the main validator and then write the flow report yourself with the collected evidence.
- Capture the exact pytest command, exit code, and the assertion-specific observations needed to support pass/fail decisions.
- If the contract requires evidence that committed repo tests do not print explicitly, create an evidence-only pytest helper under the assigned mission evidence directory and run it from there; do not add helper tests to the repository source tree.
