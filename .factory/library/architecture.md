# Architecture

## Species Flow Through the Pipeline

```
User input: species name (e.g., "macaque", "rhesus", "cow")
    │
    ▼
LAYER 1: Species Typing (src/sadie/typing/species.py)
    SPECIES dict normalizes input → canonical name
    e.g., "rhesus" → "macaque", "bos_taurus" → "cow"
    │
    ▼
LAYER 2: Airr Class (src/sadie/airr/airr.py)
    Airr(reference_name=<canonical>) → builds IgBLAST DB
    reference_name stored in AirrTable output
    │
    ▼
LAYER 3: Reference Module (src/sadie/reference/)
    References.from_yaml() → GermlineManager → GermlineToG3Adapter
    Builds IgBLAST database files (blastdb, aux_db, internal_data)
    │
    ▼
LAYER 4: Renumbering (src/sadie/renumbering/renumbering.py)
    Renumbering(allowed_species=[...])
    get_allowed_species() = allowlist of supported species
    │
    ▼
LAYER 5: HMMER Aligner (src/sadie/renumbering/aligners/hmmer.py)
    get_hmm_models() priority chain:
      1. Custom HMM dir
      2. LocalHMMBuilder (germlines module, modern)
      3. G3 API HMMs when the species/chain is supported there
      4. Legacy ANARCI HMMs only when G3 lacks support or numbering HMMs are forced
    Backward-compat alias: "rhesus" is resolved to "macaque" before custom/local HMM lookup
    `HMMER` is also a directly exported/tested API surface, not just an internal `Renumbering` helper,
    so feature contracts that name `HMMER.get_hmm_models()` must be enforced at this layer too.
    HMM name format: {species}_{chain}.hmm
    │
    ▼
LAYER 6: Numbering (src/sadie/numbering/numbering.py)
    _SPECIES_ALIASES resolves species for all_germlines lookup
    run_germline_assignment() → all_germlines[segment][chain][species]
    │
    ▼
LAYER 7: Germline Data (src/sadie/numbering/germlines.py)
    all_germlines dict: {segment: {chain: {species: {gene: sequence}}}}
    Hand-maintained dict from ANARCI, ~2089 lines
```

## HMM File Locations (3 directories)

| Directory | Source | Naming |
|-----------|--------|--------|
| `src/sadie/germlines/hmms/` | LocalHMMBuilder output | macaque_H.hmm |
| `src/sadie/renumbering/data/hmms/` | Newer renumbering HMMs | macaque_H.hmm |
| `src/sadie/renumbering/data/anarci/HMMs/` | Legacy ANARCI | rhesus_H.hmm |

## Key Modules

| Module | Purpose |
|--------|---------|
| `airr/` | AIRR-standard annotation, main entry point |
| `airr/methods.py` | run_mutational_analysis(), species detection from reference_name |
| `germlines/` | Multi-source germline manager with provider priority |
| `germlines/renumbering_integration.py` | LocalHMMBuilder — builds HMMs from germline data |
| `reference/` | YAML config → IgBLAST database builder |
| `renumbering/` | Antibody numbering (IMGT, Kabat schemes) |
| `renumbering/aligners/hmmer.py` | HMM model loading with priority fallback chain |
| `numbering/numbering.py` | Numbering logic, germline assignment, species aliases |
| `numbering/germlines.py` | all_germlines dict (hand-maintained) |
| `typing/species.py` | SPECIES dict for name normalization |

## Critical Invariants

1. Species names must be consistent across all layers — canonical name is used everywhere
2. HMM selection must match the species of the input sequence (never silently use human HMMs for non-human)
3. Germline assignment must use germlines from the same species as the HMM alignment
4. Backward compat: old species names (e.g., "rhesus") must be accepted as aliases
