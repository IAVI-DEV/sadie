# Environment

Environment variables, external dependencies, and setup notes.

**What belongs here:** Required env vars, external API keys/services, dependency quirks, platform-specific notes.
**What does NOT belong here:** Service ports/commands (use `.factory/services.yaml`).

---

## Python Environment

- Python >=3.10, managed via Poetry
- Dev dependencies: pytest, black, pyright, pre-commit
- Key dependencies: biopython, pydantic v2, pandas, PyYAML, click

## Environment Variables

- `SADIE_USE_GERMLINES_MODULE`: Controls whether to use local germlines module (default: true) vs deprecated G3 API. This mission aims to unify paths so this flag may become less relevant.
- `SADIE_CACHE_DIR`: (NEW) User-configurable cache directory for compiled databases. Default: `~/.sadie/cache/`

## External Dependencies

- IgBLAST: `igblastn` binary must be available (bundled in `src/sadie/airr/bin/`)
- `makeblastdb`: Required for building BLAST databases (bundled)
- No network services required at runtime (germline data is pre-downloaded)

## Germline Data

- Raw germline data lives in `src/sadie/germlines/sources/{provider}/{species}/`
- Normalized data in `src/sadie/germlines/normalized/{species}/`
- IgBLAST databases in `src/sadie/germlines/igblast/`
- Downloaded via `sadie germlines populate`
