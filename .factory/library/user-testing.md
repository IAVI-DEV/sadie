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
- The full `commands.test` suite (`poetry run pytest tests/ -x --tb=short`) can take well over 10 minutes and may spend time in later-milestone AIRR/macaque paths before reaching quick-fixes-relevant checks, so user-testing validators should favor assertion-specific commands.

## Flow Validator Guidance: shell

- Use the shared checkout at `/Users/tmsincomb/sadie` as read-only except for your assigned flow report and evidence files.
- Prefer direct inspection commands for these assertions: `grep`, `poetry check`, and `poetry run pytest --collect-only`.
- Do not run formatters, broad mutation/regeneration scripts, or any git write commands.
- Save command output to evidence files under your assigned evidence directory when practical so synthesis can reference concrete logs.

## Flow Validator Guidance: python-api

- Use the shared checkout at `/Users/tmsincomb/sadie` as read-only except for your assigned flow report and evidence files.
- Run API checks with one-off `poetry run python - <<'PY'` scripts.
- Keep checks side-effect-free: instantiate classes, inspect return values, and capture exceptions/messages only.
- Do not edit source files, install dependencies, or write temporary files outside your assigned evidence directory.
