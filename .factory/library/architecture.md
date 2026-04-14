# Architecture

## Subsystems Affected by This Mission

### Airr Module (`src/sadie/airr/`)

The main annotation entry point. `Airr(species_name)` constructs an IgBLAST runner.

**Database resolution flow:**
1. `Airr.__init__()` calls `_resolve_database_via_reference()` which tries `References.from_yaml()` → `make_airr_database()`
2. If reference build fails, falls back to `GermlineData(name, receptor, None, scheme)` (direct germlines path)
3. The fallback is at `airr.py:362-372` — catches any exception, logs warning, uses direct path

**Bug P1 impact:** For macaque, step 1 fails because `make_airr_database()` at `reference.py:591-609` requires IMGT position columns (`imgt.fwr1_start` through `imgt.fwr3_end`) that the macaque germline dataframe lacks. The fallback produces annotations missing `j_call` and alignment fields.

### Reference Module (`src/sadie/reference/`)

Builds IgBLAST databases from YAML configuration.

**`make_airr_database()` flow:**
1. Loads germline genes from `GermlineManager`
2. Checks for required IMGT position columns in the dataframe
3. If columns are missing, raises `ValueError` — this is where macaque fails
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
