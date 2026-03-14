# BLAST Local ID Limit

BLAST's `makeblastdb` enforces a **50-character limit** on sequence local IDs in FASTA files.

## Impact

Some allele names (especially from VDJbase with SNP annotations) exceed this limit.
The Reference module (`src/sadie/reference/reference.py`) handles this via:

1. `_BLAST_MAX_ID_LEN = 50` — constant defining the limit
2. `_truncate_allele_name()` — truncates long names using SHA-256 hash suffix
3. `_build_name_mapping()` — builds original→truncated mapping for a set of alleles
4. `.allele_name_mapping.json` — written alongside compiled database for reverse lookup

## Cross-Module Coupling

The **Reference module** writes `.allele_name_mapping.json` (via `_NAME_MAPPING_FILENAME` constant).
The **Airr module** reads it (imports `_NAME_MAPPING_FILENAME` from `sadie.reference.reference`)
to reverse-map truncated IgBLAST results back to original allele names.

## When This Matters

Any code that writes allele names to FASTA files for `makeblastdb` must respect this limit.
New providers or custom allele sources with long names will trigger truncation automatically
through the existing `_build_name_mapping()` pipeline in `References.make_airr_database()`.
