# Unified Germline Pipeline Tutorial

This tutorial covers the refactored SADIE germline pipeline that replaces the two parallel
paths to IgBLAST databases with a single, cached, config-driven flow.

---

## What Changed (Summary)

**Before:** `Airr()` used two independent code paths to reach IgBLAST databases -- a direct
`germlines/pipeline.py` path and a `reference/reference.py` config-driven path. They had
separate deduplication logic, separate error handling, and no caching.

**After:** `Airr(providers=[...])` routes through a single pipeline:

```
Airr(providers=["imgt", "ogrdb"])
  → auto-generate reference.yml (if missing)
  → filter config by species + providers
  → check database cache (~/.sadie/cache/)
  → on miss: build via Reference module → cache atomically
  → IgBLAST annotation
```

Backward compatibility is preserved: `database=` and `references=` parameters still work
exactly as before.

---

## 1. The New Data Flow

The `Airr` constructor now has three mutually exclusive branches:

| Branch | When | What Happens |
|--------|------|--------------|
| **Prebuilt** | `database=<path>` provided | Uses path directly, no resolution |
| **Custom References** | `references=<References>` provided | Builds fresh from the References object |
| **Unified pipeline** | Neither provided (default) | Auto-generates config, checks cache, builds if needed |

### Default path (unified pipeline)

```python
from sadie.airr import Airr

# Uses the unified pipeline: auto-generate config → cache → annotate
airr = Airr("human", providers=["imgt"])
result = airr.run_single("my_seq", "CAGGTGCAGCTGGTGGAG...")

# Multiple providers with priority ordering (first provider wins on duplicates)
airr = Airr("human", providers=["ogrdb", "imgt"])

# Prebuilt database (bypasses everything)
airr = Airr("human", database="/path/to/my/igblast/db")
```

The `providers` parameter controls two things:
1. **Which alleles** are included in the database
2. **Priority ordering** -- when the same allele name exists in multiple providers, the first
   provider in the list wins (first-come-first-serve deduplication)

---

## 2. Auto-Generation of reference.yml

The reference config (`reference.yml`) is auto-generated from three sources:

### Generation rules

| Source | Curated species | Uncurated species |
|--------|----------------|-------------------|
| **IMGT** | Only alleles listed in `reference.g3.yml` | ALL alleles |
| **OGRDB** | ALL alleles | ALL alleles |
| **VDJbase** | ALL alleles | ALL alleles |

**Curated species** are those with entries in `reference.g3.yml` (human, mouse, dog, etc.).
These have hand-picked IMGT allele lists to filter out noisy/problematic alleles (especially
relevant for macaque).

**Uncurated species** get everything from IMGT -- the assumption is that filtering hasn't been
done yet, so all available data is included.

OGRDB and VDJbase are always fully included regardless of curation status.

### CLI commands

```bash
# Generate reference.yml from germline sources
sadie reference generate

# Force overwrite existing
sadie reference generate --force

# Custom output path
sadie reference generate --output /path/to/reference.yml

# Custom g3 baseline
sadie reference generate --g3-yaml /path/to/custom_g3.yml
```

### Python API

```python
from sadie.reference.generate import generate_reference_yaml, get_g3_curated_species

# Generate and get the parsed config
config = generate_reference_yaml()

# See which species are curated
curated = get_g3_curated_species()
```

---

## 3. Database Caching

Compiled IgBLAST databases are cached to avoid slow recompilation on repeated use.

### Cache location

```
~/.sadie/cache/<sha256_hex>/
    blastdb/
    aux_db/
    internal_data/
    .sadie_cache_complete    # sentinel file
```

Override with `SADIE_CACHE_DIR` environment variable:
```bash
export SADIE_CACHE_DIR=/fast/disk/sadie_cache
```

### Cache key computation

The cache key is a SHA-256 hash of three components:
1. `reference_name` (e.g., "human")
2. `sorted(providers)` tuple (e.g., `("imgt", "ogrdb")`)
3. Full text content of the filtered YAML config

This means:
- Same species + same providers + same allele lists = cache hit
- Change any provider = new cache entry
- Edit `reference.yml` (add/remove alleles) = new cache entry
- Provider order doesn't affect the key (sorted before hashing)

### Concurrency safety

Cache builds use an atomic pattern:
1. Build into a temporary directory (same filesystem)
2. Write `.sadie_cache_complete` sentinel
3. `os.rename()` temp dir to final path (atomic on same filesystem)
4. If another process finished first, discard temp dir and use the winner's cache

### Python API

```python
from sadie.reference.cache import DatabaseCache, compute_cache_key

cache = DatabaseCache()  # uses ~/.sadie/cache/
cache = DatabaseCache("/custom/path")

key = compute_cache_key("human", ["imgt", "ogrdb"], yaml_content_string)

if cache.is_cached(key):
    db_path = cache.get_cached_path(key)
else:
    db_path = cache.build_and_cache(key, references_object)

# Or use the convenience method
db_path = cache.get_or_build(key, references_object)

# Clear all cached databases
cache.clear()
```

---

## 4. Cross-Provider Duplicate Handling

When multiple providers supply the same allele name, the Reference module uses
**first-come-first-serve** deduplication:

```yaml
# reference.yml
human:
  ogrdb:              # processed first (higher priority)
    human:
      - IGHV1-2*01    # kept
      - IGHV1-2*04    # kept (unique to ogrdb)
  imgt:               # processed second
    human:
      - IGHV1-2*01    # SKIPPED (duplicate, ogrdb already has it)
      - IGHV1-2*02    # kept (unique to imgt)
```

Provider order in `reference.yml` determines priority. When using the Python API, the
`providers` list order controls this:

```python
# ogrdb alleles take priority over imgt
airr = Airr("human", providers=["ogrdb", "imgt"])

# imgt alleles take priority over ogrdb
airr = Airr("human", providers=["imgt", "ogrdb"])
```

Duplicates are silently dropped with a DEBUG-level log message.

---

## 5. BLAST ID Length Handling

BLAST local IDs have a 50-character maximum. Some VDJbase allele names exceed this
(e.g., names with multiple SNP annotations).

The Reference module handles this transparently:

1. Allele names longer than 50 characters are truncated to `<first 38 chars>_<11-char SHA-256>`
2. A reverse mapping is saved as `.allele_name_mapping.json` alongside the database
3. After IgBLAST annotation, truncated names are automatically mapped back to originals in the
   results DataFrame
4. If two different names produce the same truncated form, a `ValueError` is raised (collision
   detection)

This is fully automatic -- users don't need to handle this.

---

## 6. CLI Commands

### Full workflow

```bash
# Step 1: Download germline data from IMGT, OGRDB, VDJbase
sadie germlines populate

# Step 2: Generate reference.yml from downloaded data
sadie reference generate

# Step 3a: Rebuild IgBLAST databases (all species)
sadie germlines rebuild

# Step 3b: Rebuild for specific species only
sadie germlines rebuild --species human --species mouse

# Step 4: Annotate sequences (uses cached databases automatically)
sadie airr input.fasta
sadie airr -n mouse input.fasta
```

### Checking status

```bash
# Check germline database status
sadie germlines status

# Check what's in the cache
ls ~/.sadie/cache/
```

---

## 7. Error Handling

### Germlines not populated

```python
from sadie.airr import Airr

# If germlines aren't downloaded yet:
airr = Airr("human")
# Raises: BadDataSet("Germlines not populated for 'human'.
#   Run 'sadie germlines populate' first.")
```

### Invalid species

```python
airr = Airr("se09")
# Raises: ValueError (se09 is not a valid species for the unified pipeline
#   and has no legacy germlines data)
```

### No matching providers

```python
airr = Airr("human", providers=["custom"])
# Raises: ValueError("None of the requested providers ['custom'] are
#   available in the reference config. Available: ['imgt', 'ogrdb']")
```

### Fallback behavior

If the unified Reference pipeline fails for any reason (build errors, missing data, etc.),
the constructor falls back to the legacy direct germlines module path with a warning:

```
WARNING: Reference pipeline failed for 'rhesus_macaque', falling back to direct germlines path
```

This ensures existing workflows don't break even if the new pipeline encounters unexpected
data issues.

---

## 8. New Module Layout

```
src/sadie/reference/
├── __init__.py
├── cache.py              # NEW: DatabaseCache, compute_cache_key
├── generate.py           # NEW: generate_reference_yaml, get_g3_curated_species
├── models.py             # unchanged
├── reference.py          # MODIFIED: name truncation, mapping, annotation fix
├── yaml.py               # MODIFIED: cross-provider deduplication
└── data/
    └── reference.g3.yml  # NEW location: curated IMGT baseline

src/sadie/airr/
└── airr.py               # MODIFIED: 3-branch constructor, unified pipeline routing

src/sadie/germlines/
└── cli.py                # MODIFIED: rebuild_germlines function
```

---

## 9. Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `SADIE_CACHE_DIR` | `~/.sadie/cache/` | Override database cache location |
| `SADIE_USE_GERMLINES_MODULE` | `true` | Use local germlines (vs deprecated G3 API) |

---

## 10. Migration from Old Workflow

If you were using the old workflow:

```python
# OLD: Direct database path
airr = Airr("human", database="/path/to/db")
# STILL WORKS: No changes needed

# OLD: Direct References object
refs = References.from_yaml("reference.yml")
airr = Airr("human", references=refs)
# STILL WORKS: No changes needed

# NEW: Let the unified pipeline handle everything
airr = Airr("human", providers=["imgt"])
# Automatically generates config, caches database, annotates
```

The old CLI commands also still work, but the recommended workflow is now:
```bash
sadie germlines populate      # download data
sadie reference generate      # generate config
sadie germlines rebuild       # compile databases
```
