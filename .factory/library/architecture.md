# Architecture

## Subsystems Affected by This Mission

### Airr Module (`src/sadie/airr/`)

The main annotation entry point. `Airr(species_name)` constructs an IgBLAST runner.

**Database resolution flow:**
1. `Airr.__init__()` calls `_resolve_database_via_reference()` which tries `References.from_yaml()` → `make_airr_database()`
2. If a provider-filtered reference resolves with no V genes (the macaque failure mode fixed in milestone `macaque-fix`), `_resolve_database_via_reference()` expands to all supported sources before giving up on the reference build path
3. If reference build still fails, it falls back to `GermlineData(name, receptor, None, scheme)` (direct germlines path)
4. The fallback remains at `airr.py:362-372` — it catches exceptions, logs a warning, and uses the direct path

**Bug P1 impact:** The original macaque failure came from the reference-build path producing an incomplete database and then dropping into the direct-germlines fallback, which yielded `productive=True` rows with missing `j_call` and alignment fields. The current fix in `src/sadie/airr/airr.py` keeps macaque on the reference-build path by expanding sources when the filtered config lacks V genes.

### Reference Module (`src/sadie/reference/`)

Builds IgBLAST databases from YAML configuration.

**`make_airr_database()` flow:**
1. Loads germline genes from `GermlineManager`
2. Checks for required IMGT position columns in the dataframe
3. If columns are missing for specific V genes, those alleles are skipped from BLAST-db generation instead of crashing the entire build
4. Builds blastdb, aux_db, internal_data files

### Renumbering Module (`src/sadie/renumbering/`)

IMGT/Kabat/Chothia antibody numbering.

**Constructor flow (`__init__`):**
1. Accepts `allowed_species` and `allowed_chain` parameters
2. `allowed_chain` defaults to `["H", "K", "L"]`
3. Loads HMM models for each species+chain pair
4. Guard-rail validation at line 133: only runs when `set(allowed_chains) != set(get_allowed_chains())`
5. `get_allowed_chains()` returns full set `["H","K","L","A","B","G","D"]`

**Bug P3 impact:** When caller passes the full 7-chain set explicitly, condition is False, validation skipped.

**FWR1 gap insertion pipeline:**
1. `Renumbering.run_single()` → `Numbering.numbering()` → `number_sequence_from_alignment()`
2. IMGT scheme numbering at `schemes.py` → `number_imgt()` → `_number_regions()`
3. Region extraction: `_get_region()` → `_add_segment_regions()` builds FWR1 from numbered positions
4. IMGT position 10 gap is a conserved deletion in heavy chains

**Bug P2 impact:** The gap at IMGT position 10 in FWR1 is not being inserted — affects human, dog, cat heavy chains.

### Numbering Module (`src/sadie/numbering/`)

Low-level sequence numbering. `numbering.py` contains `number_sequence_from_alignment()` and `get_vector_state()`. `schemes.py` contains IMGT/Kabat/Chothia numbering functions.

## Data Flow Invariants

- `productive=True` should imply `j_call is not NaN` (currently violated for macaque)
- IMGT FWR1 for heavy chains is always 26 positions (25 residues + 1 gap at position 10)
- `allowed_chain` validation must fire whenever chains are explicitly requested
