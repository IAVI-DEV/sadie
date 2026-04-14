# Environment

**What belongs here:** Required env vars, external API keys/services, dependency quirks, platform-specific notes.
**What does NOT belong here:** Service ports/commands (use `.factory/services.yaml`).

---

## Python Environment

- Python 3.14.4 via Poetry
- `poetry install --with dev` for full dev environment
- Use `poetry run` prefix or `python` (not `python3`) per project conventions
- Use `pytest` (not `python -m pytest`) for running tests
- Use `pre-commit run --all-files` for formatting

## Key Environment Variable

- `SADIE_USE_GERMLINES_MODULE`: Use local germlines (default: true) vs deprecated G3 API

## Dependencies

- IgBLAST: bundled/built by SADIE reference system
- HMMER: used by renumbering module for HMM alignment
- Pre-commit hooks: black (line-length 120), isort, trailing-whitespace, end-of-file-fixer, check-yaml
