# MOTIF_LOOKUP API Contracts

This directory contains JSON Schema definitions for the MOTIF_LOOKUP implementation.

## Schemas

### motif-registry.schema.json

Validates the complete motif registry JSON file structure including:
- Species-level organization
- `_provenance` metadata for each species
- Regex patterns for each locus (IGHJ, IGKJ, IGLJ, etc.)
- Required and optional fields

**Usage**: Validate `src/sadie/reference/data/j_gene_motif.json`

### coverage-test-result.schema.json

Validates empirical coverage test results including:
- Test execution metadata
- Per-species/locus results
- Match rates and thresholds
- Pass/fail status for each test

**Usage**: Validate output from coverage testing framework

### motif-api-response.schema.json

Validates the public API response structure:
- Backward-compatible `MOTIF_LOOKUP` dict
- New `MOTIF_PROVENANCE` metadata
- Summary statistics

**Usage**: Validate responses from `from sadie.reference import MOTIF_LOOKUP, MOTIF_PROVENANCE`

## Validation Examples

### Python Usage

```python
import json
import jsonschema

# Validate motif registry file
with open('motif-registry.schema.json') as f:
    schema = json.load(f)

with open('src/sadie/reference/data/j_gene_motif.json') as f:
    data = json.load(f)

jsonschema.validate(data, schema)
```

### Command Line Usage

```bash
# Install jsonschema CLI tool
pip install jsonschema

# Validate motif registry
jsonschema -i ../../../src/sadie/reference/data/j_gene_motif.json motif-registry.schema.json

# Validate test results
jsonschema -i test-results.json coverage-test-result.schema.json
```

## Schema Versioning

All schemas use JSON Schema Draft 7 and include:
- `$schema`: JSON Schema version
- `$id`: Unique schema identifier
- `title`: Human-readable schema name
- `description`: Purpose and usage

## Field Conventions

- **Species names**: lowercase with underscores (e.g., `human`, `crab_eating_macaque`)
- **Locus names**: uppercase standard format (e.g., `IGHJ`, `IGKJ`, `IGLJ`)
- **Dates**: ISO 8601 format (`YYYY-MM-DD` for dates, full RFC 3339 for timestamps)
- **Regex patterns**: Standard regex syntax, validated for basic structure
- **Match rates**: Decimal values 0.0-1.0 (not percentages)

## Maintenance

When updating the MOTIF_LOOKUP data model:

1. Update relevant schema files
2. Update this README with changes
3. Test validation against existing data
4. Version bump schema `$id` if breaking changes