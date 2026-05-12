# Quickstart: Germlines Module

## Basic Usage

```python
from sadie.germlines import get_germline_genes, GermlineManager

genes = get_germline_genes("human", "V", "H")

for gene in genes[:5]:
    print(f"{gene.name}: {gene.sequence[:30]}...")
```

## Setup (First Time)

```bash
cd src/sadie/germlines

python scripts/download_imgt.py --species human
python scripts/download_ogrdb.py --species human

python scripts/validate.py human
```

## Add Custom Sequences

```bash
mkdir -p sources/custom/human

cat > sources/custom/human/IGHV.fasta << 'EOF'
>IGHV-CUSTOM*01|Homo sapiens|F
CAGGTGCAGCTGGTGCAGTCTGGGGCTGAGGTGAAG
EOF
```

Custom sequences take priority over database sources.

## Priority Configuration

```python
manager = GermlineManager(providers=["custom", "ogrdb", "imgt"])

genes = manager.get_genes("human", "V", "H")
```

Default: `["custom", "ogrdb", "vdjbase", "imgt"]`

## Offline Usage

Once data is downloaded, the module works offline:

```python
import socket
socket.setdefaulttimeout(0.1)

genes = get_germline_genes("human", "V", "H")
```

## Integration Points

### IgBLAST

```python
from sadie.airr.igblast.germline import GermlineData

gd = GermlineData("human")
print(gd.v_gene_dir)
```

### Get Specific Gene

```python
from sadie.germlines import get_gene_by_name

gene = get_gene_by_name("IGHV1-69*01", "human")
print(gene.sequence_gapped)
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| SADIE_USE_GERMLINES_MODULE | true | Use new module |

## MOTIF_LOOKUP Usage (Added 2026-05-07)

### Basic Motif Pattern Access

```python
# Backward-compatible usage (unchanged)
from sadie.reference import MOTIF_LOOKUP

# Get J-gene FWR4 motifs for human
human_motifs = MOTIF_LOOKUP["human"]
print(f"IGHJ motif: {human_motifs['IGHJ']}")  # WG.G
print(f"IGKJ motif: {human_motifs['IGKJ']}")  # FG
print(f"IGLJ motif: {human_motifs['IGLJ']}")  # FG.G
```

### Provenance Metadata Access

```python
# New provenance API
from sadie.reference import MOTIF_LOOKUP, MOTIF_PROVENANCE

# Check motif origin and validation status
human_prov = MOTIF_PROVENANCE["human"]
print(f"Source: {human_prov['source']}")
print(f"IMGT validated: {human_prov['imgt_validated']}")
print(f"Last reviewed: {human_prov['last_reviewed']}")

# Find all IMGT-validated species
validated_species = [
    species for species, meta in MOTIF_PROVENANCE.items()
    if meta["imgt_validated"]
]
print(f"Validated species: {validated_species}")
```

### Empirical Coverage Testing

```python
# Run coverage tests to validate motif patterns
import pytest

# Test specific species/locus combination
pytest.tests.unit.reference.test_motif_coverage::test_motif_coverage[human-IGHJ] -v

# Test all available combinations
pytest tests/unit/reference/test_motif_coverage.py -v

# Test with custom threshold reporting
pytest tests/unit/reference/test_motif_coverage.py --motif-report
```

### Pattern Validation Example

```python
import re
from Bio.Seq import Seq
from sadie.reference import MOTIF_LOOKUP

def validate_j_sequence(sequence: str, species: str, locus: str) -> bool:
    """Check if J sequence matches expected motif pattern."""

    # Get pattern for species/locus
    pattern = MOTIF_LOOKUP[species][locus]

    # Translate to amino acid (J genes typically in frame 1)
    aa_seq = str(Seq(sequence).translate()).rstrip('*')

    # Search for motif pattern
    return bool(re.search(pattern, aa_seq))

# Example usage
j_sequence = "TGGGGCCAGGGAACCCTGGTCACCGTCTCCTCAG"  # Example IGHJ4*01
matches = validate_j_sequence(j_sequence, "human", "IGHJ")
print(f"Sequence matches human IGHJ motif: {matches}")
```

### Species and Locus Coverage

```python
# List all available species
species_list = list(MOTIF_LOOKUP.keys())
print(f"Total species: {len(species_list)}")
print(f"First 10: {species_list[:10]}")

# Check locus coverage per species
for species in ["human", "mouse", "rat"]:
    loci = list(MOTIF_LOOKUP[species].keys())
    print(f"{species}: {loci}")
```

### Migration Guide from Legacy Code

```python
# OLD: Direct dict access (still works)
pattern = MOTIF_LOOKUP["human"]["IGHJ"]

# NEW: With provenance awareness
pattern = MOTIF_LOOKUP["human"]["IGHJ"]
confidence = MOTIF_PROVENANCE["human"]["imgt_validated"]

if confidence:
    print(f"High-confidence pattern: {pattern}")
else:
    print(f"Legacy pattern (validate empirically): {pattern}")
```

### Migration Validation

Validate the complete migration using the provided script:

```bash
# Basic validation
python scripts/validate_motif_migration.py

# Comprehensive validation with performance benchmarks
python scripts/validate_motif_migration.py --verify-all --performance --verbose

# Save validation report
python scripts/validate_motif_migration.py --verify-all --report-file migration_report.json
```

This validates:
- ✅ File structure and JSON integrity
- ✅ Data loading and backward compatibility
- ✅ Schema compliance for all 37 species
- ✅ Performance requirements (<50ms loading)
- ✅ Integration with existing j_gene_data module

## Troubleshooting

**No data found**: Run download scripts first
**Import error**: Check BioPython installed
**Permission denied**: Check sources/ directory permissions
**MOTIF_LOOKUP KeyError**: Check species name spelling (lowercase with underscores)
**Coverage test failures**: Check FASTA data availability in `src/sadie/germlines/sources/`
**JSON validation errors**: Verify schema compliance using `contracts/*.schema.json`
