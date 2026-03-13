# Architecture

Architectural decisions, patterns discovered, and key design choices.

**What belongs here:** Design patterns, module relationships, key abstractions, data flow diagrams.

---

## Current Data Flow (Pre-Refactoring)

Two parallel paths to IgBLAST databases exist:

### Path 1: Germlines Pipeline (direct)
```
sadie germlines populate → sources/{provider}/{species}/*.fasta
    ↓
GermlinePipeline._rebuild_normalized() → normalized/{species}/*.fasta
    ↓ (uses GermlineManager priority dedup)
GermlinePipeline._rebuild_igblast() → igblast/{database,aux_db,internal_data}/
```

### Path 2: Reference Module (config-driven)
```
reference.yml (YAML config: name → provider → species → [allele_list])
    ↓
References.from_yaml(yaml_path, use_germlines=True)
    ↓ (fetches alleles via GermlineToG3Adapter → GermlineManager)
References.make_airr_database(output_dir)
    ↓ (builds IgBLAST DB in output_dir)
```

### Airr Constructor (3 branches)
1. `database=<path>` → uses prebuilt database directly
2. `references=<References>` → builds via Reference module
3. Default → uses germlines/igblast/ path

## Target Data Flow (Post-Refactoring)

Single unified path:
```
Airr(reference_name, providers=[...])
    ↓
Check cache (keyed by reference_name + providers + reference.yml hash)
    ↓ (cache miss)
Load/auto-generate reference.yml
    ↓
References.from_yaml() with provider filtering
    ↓
References.make_airr_database() → ~/.sadie/cache/<hash>/
    ↓
Use cached database for IgBLAST annotation
```

## Key Classes

- **Airr**: Main annotation API, constructor routes to database
- **References**: Collection of gene references from YAML, builds IgBLAST databases
- **GermlineManager**: Priority-based gene lookup across providers
- **GermlineToG3Adapter**: Converts GermlineGene → legacy G3 format for Reference module
- **GermlinePipeline**: Current normalize+build pipeline (to be replaced by Reference path)

## Provider Trust Levels

- **OGRDB**: Fully trusted - include ALL alleles
- **VDJbase**: Fully trusted - include ALL alleles
- **IMGT**: Partially trusted - use reference.g3.yml allowlist for curated species, all alleles for uncurated
- **Custom**: Partially trusted - user-defined, included as-is

## Key Files

- `reference.g3.yml`: Curated IMGT allele allowlist (clk, dog, human, mouse) - KEEP
- `reference.yml` (repo root): Old manual attempt - DELETE
- `src/sadie/reference/data/reference.yml`: Module-internal reference config
- `src/sadie/germlines/pipeline.py`: Current pipeline orchestrator
- `src/sadie/germlines/g3_adapter.py`: Bridge between germlines and reference modules
