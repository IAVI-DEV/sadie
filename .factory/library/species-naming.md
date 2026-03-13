# Species Naming Inconsistencies

## macaque vs rhesus_macaque

The IMGT source data directory uses `macaque` as the species name (`src/sadie/germlines/sources/imgt/macaque/`), but the germlines igblast module normalizes this to `rhesus_macaque` (directory: `src/sadie/germlines/igblast/database/rhesus_macaque/`, `src/sadie/germlines/igblast/Ig/internal_data/rhesus_macaque/`).

The auto-generated `reference.yml` uses the IMGT source directory name (`macaque`), creating a mismatch when code looks up `rhesus_macaque` in the reference config.

The OGRDB download script (`download_ogrdb.py:88`) also normalizes `macaque` → `rhesus_macaque`.

**Impact**: `Airr("rhesus_macaque")` passes the available_datasets check (rhesus_macaque exists in igblast/database/) but fails when looking up in reference.yml (which uses `macaque` as the key).

**Workaround**: The unified pipeline fallback catches certain exceptions and falls back to the direct germlines path. However, `BadDataSet` is not in the exception tuple, so this mismatch causes an uncaught exception.
