---
name: python-bugfix-worker
description: Fixes Python library bugs with TDD — regression tests first, then implementation fix, then verification
---

# Python Bugfix Worker

NOTE: Startup and cleanup are handled by `worker-base`. This skill defines the WORK PROCEDURE.

## When to Use This Skill

Use for features that fix bugs in the SADIE Python library. Each feature targets a specific bug with clear symptoms and expected behavior documented in the feature description.

## Required Skills

- `python-library-worker` — Invoke for general Python library implementation patterns if needed.
- `sadie-airr` — Invoke when working on Airr module bugs (P1 macaque fix) for API reference.

## Work Procedure

### 1. Understand the Bug

- Read the feature description thoroughly — it contains the bug symptoms, root cause, and expected fix.
- Read the referenced source files to understand the current code.
- Read existing tests to understand what's already covered and what's missing.
- If the feature references Bug-Priority.md, read the relevant section for investigation plan details.

### 2. Write Regression Tests First (RED)

- Write tests that demonstrate the bug (they should FAIL with the current code).
- For each `expectedBehavior` in the feature, write at least one test case.
- Run the tests to confirm they fail: `poetry run pytest <test_file>::<test_name> -v`
- Record the failure output in your handoff.

### 3. Implement the Fix (GREEN)

- Make the minimal code change that fixes the bug.
- Follow existing code conventions: type hints, NumPy docstrings, line length 120.
- Do not refactor unrelated code — stay focused on the bug.
- Run the new tests to confirm they pass: `poetry run pytest <test_file>::<test_name> -v`

### 4. Verify No Regressions

- Run the full test file: `poetry run pytest <test_file> -v`
- Run related module tests: `poetry run pytest tests/unit/<module>/ -v`
- Run type checking: `poetry run pyright src/sadie/<module>/`
- Run formatting: `pre-commit run --all-files`
- Fix any failures before completing.

### 5. Manual Verification

- For API bugs: Write a small Python script that exercises the fix and verify correct output.
- For config/script bugs: Run the relevant command and verify correct behavior.
- Record what you verified in `interactiveChecks`.

## Example Handoff

```json
{
  "salientSummary": "Fixed IMGT position 10 gap insertion in FWR1 for heavy chains. The gap was lost during _number_regions() due to an off-by-one in the position 10 insertion index. Added 4 regression tests covering human, dog, cat heavy chains and light chain no-gap invariant. All 12 renumbering tests pass, pyright clean.",
  "whatWasImplemented": "Fixed gap insertion logic in src/sadie/numbering/schemes.py:number_imgt() to correctly insert gap at IMGT position 10 for heavy chain FWR1. The bug was an off-by-one error introduced when the numbering pipeline was refactored.",
  "whatWasLeftUndone": "",
  "verification": {
    "commandsRun": [
      {
        "command": "poetry run pytest tests/unit/renumbering/test_renumbering.py -v",
        "exitCode": 0,
        "observation": "12 passed — all fwr1_aa_gaps assertions now pass for human, dog, cat"
      },
      {
        "command": "poetry run pyright src/sadie/numbering/",
        "exitCode": 0,
        "observation": "0 errors, 0 warnings"
      },
      {
        "command": "pre-commit run --all-files",
        "exitCode": 0,
        "observation": "All hooks passed"
      }
    ],
    "interactiveChecks": [
      {
        "action": "Ran python -c to test Renumbering.run_single() on DupulimabH",
        "observed": "fwr1_aa_gaps = 'EVQLVESGG-GLEQPGGSLRLSCAGS' — gap at position 10 confirmed"
      }
    ]
  },
  "tests": {
    "added": [
      {
        "file": "tests/unit/renumbering/test_renumbering.py",
        "cases": [
          { "name": "test_fwr1_gap_position_10_human_vh", "verifies": "IMGT position 10 gap in human VH FWR1" },
          { "name": "test_fwr1_no_gap_human_vl", "verifies": "No gap at position 10 in human VL FWR1" }
        ]
      }
    ]
  },
  "discoveredIssues": []
}
```

## When to Return to Orchestrator

- The bug requires changes to germline reference data files (not just code)
- The root cause is different from what the feature description suspects
- Fixing the bug would break other tests that cannot be easily resolved
- The investigation reveals the bug is in a dependency (IgBLAST, HMMER) not in SADIE code
- The feature depends on another bug being fixed first
