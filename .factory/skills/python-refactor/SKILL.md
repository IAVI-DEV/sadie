---
name: python-refactor
description: Refactors Python library code with TDD, covering module changes, test updates, and CLI verification
---

# Python Refactor Worker

NOTE: Startup and cleanup are handled by `worker-base`. This skill defines the WORK PROCEDURE.

## When to Use This Skill

Use for features that involve:
- Modifying Python module code (reference, germlines, airr)
- Adding or updating pytest tests
- Updating CLI command implementations
- Refactoring data flow between modules
- Adding caching infrastructure

## Work Procedure

### 1. Understand the Feature

Read the feature description, preconditions, expectedBehavior, and verificationSteps carefully. Then:
- Read AGENTS.md for mission boundaries and conventions
- Read `.factory/library/architecture.md` for the current and target data flow
- Read the specific source files mentioned in the feature description
- Identify all files that need to change

### 2. Write Tests First (TDD)

Before writing any implementation code:
- Create or update test files with failing tests that cover the expectedBehavior
- Tests should be in the appropriate test directory (`tests/unit/reference/`, `tests/unit/germlines/`, `tests/unit/airr/`)
- Run the tests to confirm they fail (red phase):
  ```
  poetry run pytest tests/unit/<module>/test_<feature>.py -x --tb=short -v
  ```
- If tests need fixtures, add them to `tests/conftest.py` or the module's conftest

### 3. Implement

Write the minimum code to make the tests pass:
- Follow existing code patterns (Pydantic v2 models, NumPy docstrings, type hints)
- Line length: 120 characters
- Import patterns: match existing imports in the module
- Use existing utilities and helpers before creating new ones

### 4. Make Tests Pass (Green Phase)

Run tests to verify implementation:
```
poetry run pytest tests/unit/<module>/ -x --tb=short -v
```

Fix until all new tests pass. Do NOT modify tests to match broken implementation.

### 5. Run Broader Test Suite

After feature tests pass, run the broader test suite to catch regressions:
```
poetry run pytest tests/unit/ -x --tb=short -q
```

Note: Pre-existing failures (`test_yaml` count assertion, `test_adaptable_correction`) should be noted but not fixed. If you encounter NEW failures caused by your changes, fix them.

### 6. Type Check

```
poetry run pyright src/sadie/<module>/
```

Fix type errors introduced by your changes. Pre-existing type errors in unmodified code can be noted but not fixed.

### 7. Manual Verification

For features involving CLI commands:
```
poetry run sadie <command> --help
poetry run sadie <command> <args>
```

For features involving the Python API, write a small verification script:
```python
# verify.py
from sadie.airr import Airr
result = Airr("human", providers=["imgt"]).run_single("ACGT...")
print(result)
```
Run with: `poetry run python verify.py`

Each manual check must be recorded as an `interactiveChecks` entry in the handoff.

### 8. Commit

Commit all changes with a descriptive message. One commit per feature.

## Example Handoff

```json
{
  "salientSummary": "Implemented first-come-first-serve duplicate handling in References.from_yaml(). When duplicate allele names appear across providers, the first provider's version wins. Added 3 test cases covering: same-name different-sequence dedup, all-unique preservation, and mixed overlap scenario. All tests pass, pyright clean.",
  "whatWasImplemented": "Modified References._process_alleles() to track seen allele names and skip duplicates. Added dedup logging. Created tests/unit/reference/test_duplicate_handling.py with 3 test cases.",
  "whatWasLeftUndone": "",
  "verification": {
    "commandsRun": [
      {
        "command": "poetry run pytest tests/unit/reference/test_duplicate_handling.py -x --tb=short -v",
        "exitCode": 0,
        "observation": "3 passed in 0.8s"
      },
      {
        "command": "poetry run pytest tests/unit/reference/ -x --tb=short -q",
        "exitCode": 0,
        "observation": "8 passed, 1 failed (pre-existing test_yaml count assertion) in 1.2s"
      },
      {
        "command": "poetry run pyright src/sadie/reference/",
        "exitCode": 0,
        "observation": "0 errors, 0 warnings"
      }
    ],
    "interactiveChecks": [
      {
        "action": "Loaded test YAML with IGHV1-2*02 in both vdjbase and imgt sections",
        "observed": "References.from_yaml() completed without error, only vdjbase version retained"
      }
    ]
  },
  "tests": {
    "added": [
      {
        "file": "tests/unit/reference/test_duplicate_handling.py",
        "cases": [
          {"name": "test_duplicate_allele_first_provider_wins", "verifies": "First provider's allele sequence is used when same name appears in multiple providers"},
          {"name": "test_unique_alleles_preserved", "verifies": "Alleles unique to each provider are all included"},
          {"name": "test_mixed_overlap_dedup", "verifies": "Mixed scenario with some overlapping and some unique alleles"}
        ]
      }
    ]
  },
  "discoveredIssues": []
}
```

## When to Return to Orchestrator

- Feature depends on code changes from another unfinished feature
- Reference module's `make_airr_database()` has undocumented behavior that contradicts the feature spec
- Germline data for a required species is not populated (missing source files)
- IgBLAST binary issues (missing, wrong version, permissions)
- Test infrastructure issues (missing fixtures, broken conftest)
- Pre-existing bugs that block this feature's implementation
