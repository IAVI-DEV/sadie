# Data Model: Germlines Module

## Entities

### GermlineGene

Core entity representing a single germline gene sequence.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | str | Y | Gene name (IGHV1-69*01) |
| species | str | Y | Species (human, mouse) |
| segment | str | Y | V, D, or J |
| chain | str | Y | H, K, or L |
| sequence | str | Y | Ungapped nucleotide |
| sequence_gapped | str | N | IMGT-gapped nucleotide |
| sequence_aa | str | N | Ungapped amino acid |
| sequence_aa_gapped | str | N | IMGT-gapped amino acid |
| is_functional | bool | Y | Functional status |
| functionality | str | Y | F, ORF, or P |
| regions | dict | N | CDR/FWR regions |
| region_positions | dict | N | Region boundaries |
| source | str | Y | imgt, ogrdb, vdjbase, custom |
| source_version | str | N | Version/date |
| allele | str | N | Allele designation |
| gene_family | str | N | Gene family |
| accession | str | N | GenBank accession |

### ProviderMetadata

Tracks provider information.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | str | Y | Provider name |
| version | str | Y | Version identifier |
| last_updated | datetime | Y | Update timestamp |
| species_available | List[str] | Y | Available species |
| url | str | N | Source URL |

### ProcessingMetadata

Tracks processed file state.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| source_file | str | Y | Source path |
| processed_at | datetime | Y | Processing time |
| num_sequences | int | Y | Sequence count |
| file_hash | str | Y | MD5 hash |
| sequences | List[dict] | Y | Sequence summaries |

## Relationships

```
Provider (1) --- (*) GermlineGene
GermlineGene --- (0..1) ProcessingMetadata
Provider --- (1) ProviderMetadata
```

## Directory Structure

```
germlines/
├── sources/           # Raw data by provider
│   ├── imgt/human/   # IMGT FASTA files
│   ├── ogrdb/human/  # OGRDB FASTA files
│   ├── vdjbase/human/# VDJbase FASTA files
│   └── custom/human/ # User custom files
├── normalized/        # Merged output
│   └── human/
│       ├── gapped/   # IMGT-gapped FASTA
│       └── ungapped/ # Plain FASTA
└── igblast/          # BLAST databases
    ├── blastdb/      # makeblastdb output
    ├── aux_db/       # CDR/FWR boundaries
    └── internal_data/# organism.yaml
```

## Provider Priority

Default: `["custom", "ogrdb", "vdjbase", "imgt"]`

Resolution rules:
1. Same name, different sequence: Use higher priority
2. Same name, same sequence: Keep one, track source
3. Novel gene: Include from any source

## File Naming

Sources: `{SEGMENT}.fasta`, `{SEGMENT}_gapped.fasta`
- IGHV.fasta, IGHV_gapped.fasta
- IGHD.fasta, IGHJ.fasta

Normalized: `{species}_{segment}.fasta`
- human_V.fasta, human_V_gapped.fasta

BLAST: `{species}_{segment}`
- human_V.nhr, human_V.nin, human_V.nsq

## MOTIF_LOOKUP Data Model (Added 2026-05-07)

### MotifRegistry

JSON structure for J-gene FWR4 motif patterns with provenance metadata.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| species_name | str | Y | Species key (human, mouse, etc.) |
| _provenance | MotifProvenance | Y | Metadata about motif origin |
| locus_patterns | dict | Y | Locus → regex pattern mapping |

### MotifProvenance

Metadata documenting motif pattern origins and validation status.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| source | str | Y | Literature/database source |
| imgt_validated | bool | Y | IMGT canonical status |
| last_reviewed | str | Y | ISO date of last review |
| notes | str | N | Historical context, limitations |
| validation_count | int | N | Number of sequences validated against |
| validation_rate | float | N | Match percentage in validation |

### JSON Schema Structure

```json
{
  "species_name": {
    "_provenance": {
      "source": "string",
      "imgt_validated": "boolean",
      "last_reviewed": "YYYY-MM-DD",
      "notes": "string (optional)",
      "validation_count": "integer (optional)",
      "validation_rate": "float (optional)"
    },
    "IGHJ": "regex_pattern",
    "IGKJ": "regex_pattern",
    "IGLJ": "regex_pattern",
    "TRAJ": "regex_pattern (optional)",
    "TRBJ": "regex_pattern (optional)"
  }
}
```

### Coverage Test Data

Supporting data structure for empirical coverage validation.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| species | str | Y | Species identifier |
| locus | str | Y | Locus (IGHJ, IGKJ, IGLJ) |
| sequence_source | str | Y | FASTA file path |
| total_sequences | int | Y | Number of J sequences |
| matched_sequences | int | Y | Sequences matching pattern |
| match_rate | float | Y | matched/total percentage |
| failed_sequences | List[str] | N | Non-matching sequence IDs |

### File Locations

```
src/sadie/reference/
├── data/
│   └── j_gene_motif.json     # Canonical motif registry
└── settings.py               # Loader with provenance filtering

tests/unit/reference/
└── test_motif_coverage.py    # Empirical validation tests
```

### Backward Compatibility

Legacy `MOTIF_LOOKUP` dict maintains exact structure:
```python
MOTIF_LOOKUP = {
    "human": {
        "IGHJ": "WG.G",
        "IGKJ": "FG",
        "IGLJ": "FG.G"
    }
}
```

New `MOTIF_PROVENANCE` dict provides metadata:
```python
MOTIF_PROVENANCE = {
    "human": {
        "source": "Lefranc IMGT-ONTOLOGY",
        "imgt_validated": True,
        "last_reviewed": "2026-05-01"
    }
}
```

## Validation Rules

1. Segment: Must be V, D, or J
2. Chain: Must be H, K, or L
3. Sequence: Valid nucleotides (ACGTN) and IUPAC ambiguous
4. Functionality: F (functional), ORF, or P (pseudogene)
5. Gapped sequences: Use dots (.) for gaps per IMGT
6. **Motif patterns: Valid regex syntax, tested against J sequences**
7. **Provenance metadata: Required for all species in registry**
