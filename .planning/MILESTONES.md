# Project Milestones: Germline Database Integration

## v1.4 G3-Germlines Parity Validation (Shipped: 2026-01-28)

**Delivered:** Automated parity test infrastructure validating G3 and Germlines backends produce identical AIRR output when built with same alleles.

**Phases completed:** 33 (1 phase, 1 plan, 12 requirements)

**Key accomplishments:**

- **Test Infrastructure** — Created `tests/migration/` package with session-scoped fixtures
- **Parity Validation** — Parametrized test comparing all AIRR columns across 5 FASTA files
- **Fail-Fast Reporting** — Detailed mismatch reports with column, row, sequence ID, and both values
- **Finding: j_cigar Difference** — Test correctly detected backend difference (G3: `'355S9N53M'` vs Germlines: `'355S9N53M1N'`)

**Stats:**

- 1 phase, 1 plan, 12 requirements
- 4 files created
- 2 days from start to completion

**Git range:** `bb33048c` → `592a4c3b`

**What's next:** Investigate j_cigar difference, continue parity validation across species

---

## v1.3 Test Infrastructure & Species Expansion (Shipped: 2026-01-25)

**Delivered:** Fixed skipped tests by adding macaque germlines, airr package dependency, removing deprecated G3 tests, and fixed germline priority order.

**Phases completed:** 25-28 (4 phases, 15 requirements)

**Key accomplishments:**

- **Macaque Germlines** — Built macaque IgBLAST databases, enabled 6 previously skipped tests
- **AIRR Package** — Added airr package to dependencies, enabled AIRR validation test
- **G3 Deprecation** — Removed deprecated G3 tests, created G3-Deprecation.md documentation
- **Priority Fix** — Updated default priority to ['vdjbase', 'ogrdb', 'imgt', 'custom']

**Stats:**

- 4 phases, 15 requirements
- ~50 files modified
- 1 day from start to completion

**Git range:** See archive for details

**What's next:** Parity validation between G3 and Germlines backends

---

## v1.2 Reference Module Unification (Shipped: 2026-01-25)

**Delivered:** Enable reference.yml to select alleles from all germline sources, using germlines module as data provider instead of G3 API.

**Phases completed:** 19-24 (6 phases, 12 requirements)

**Key accomplishments:**

- **Source Validation** — Expanded VALID_SOURCES to include ogrdb, vdjbase
- **Integration** — Added use_germlines parameter to References.from_yaml()
- **Build CLI** — Added `sadie reference build` command
- **Runtime Usage** — Added Airr(database=path) parameter
- **Documentation** — Created reference-sample.yml and workflow docs

**Stats:**

- 6 phases, 12 requirements
- 3 days from start to completion

**Git range:** See archive for details

**What's next:** Test infrastructure cleanup, species expansion

---

## v1.1 Audit (Shipped: 2026-01-23)

**Delivered:** Backend parity audit and fixes achieving 98.29% structural parity between germlines module and G3 legacy backend.

**Phases completed:** 13-18 (6 phases, 12 requirements)

**Key accomplishments:**

- **C Region Integration** — Added 704 C gene sequences from IMGT GENE-DB, generated IgBLAST databases
- **J Gene Fix** — Corrected aux file format (3→5 columns), enabling CDR3/junction annotation
- **FWR3 End Fix** — Fixed ndm.imgt column 11 to use IMGT position 312 instead of sequence length
- **complete_vdj Fix** — Implemented AIRR-standard recalculation, now MORE accurate than G3
- **IMGT Variance Documentation** — Documented 1.71% difference as acceptable (40 vs 34 D alleles)

**Parity progression:**

| Phase | Structural Parity |
|-------|------------------|
| 13 (Baseline) | 72.19% |
| 15 (J Gene Fix) | 77.60% |
| 16 (FWR3 Fix) | 86.71% |
| 17 (complete_vdj) | 98.29% |
| 18 (Final) | 98.29% ✓ |

**Stats:**

- 6 phases, 12 requirements
- 4 code fixes + documentation
- 2 days from start to completion

**Git range:** `a5631a84` → `d8838d2a`

**What's next:** T-cell receptor (TR) germlines, multi-species audit, GUI for provider selection

---

## v1.0 MVP (Shipped: 2026-01-22)

**Delivered:** Connect SADIE's germline database module to AIRR annotation and renumbering, enabling provider selection (IMGT, OGRDB, VDJbase, custom) and offline operation.

**Phases completed:** 1-12 (92 tasks total)

**Key accomplishments:**

- Integrated germlines module with AIRR annotation — users can select germline provider
- Integrated germlines module with renumbering — LocalHMMBuilder generates HMMs from germlines data
- Expanded species coverage to 29 species with full IgBLAST databases
- Created CLI command `sadie germlines populate` for programmatic data population
- Implemented offline operation capability — no network required for analysis
- Built comprehensive test suite (88 tests) validating all integration paths

**Stats:**

- 52 Python files created/modified
- ~12,440 lines of Python (10,678 module + 1,762 tests)
- 12 phases, 12 plans, 92 tasks
- 14 days from start to ship

**Git range:** `4278f421` → `dd83c38b`

**What's next:** T-cell receptor (TR) germlines, multi-provider blending, GUI for provider selection

---
