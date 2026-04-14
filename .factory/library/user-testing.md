# User Testing

## Validation Surface

This is a pure Python library with no web UI or services. Validation surfaces:

1. **Python API** — Import and call `Airr`, `Renumbering` classes directly. Assert correct output values.
2. **CLI** — `sadie airr`, `sadie germlines status`, `sadie --help`. Assert exit codes and output.
3. **pytest** — Run test suites to verify behavior. Assert all tests pass.

Testing tool: Shell commands (`poetry run python -c "..."`, `poetry run pytest ...`, `sadie ...`)

No browser testing (agent-browser) or TUI testing (tuistory) needed.

## Validation Concurrency

Machine: 128GB RAM, 16 cores.

Each validation instance runs a Python script or pytest command — lightweight (~200MB per process).

**Max concurrent validators: 5** (well within resource budget)

## Testing Notes

- pytest is configured with `-x` (fail-fast) in pytest.ini
- For validation, run without `-x` to see all failures: `poetry run pytest tests/ --tb=short`
- Macaque tests take ~10-15 seconds due to IgBLAST database construction
- Renumbering tests are fast (~2-3 seconds)
