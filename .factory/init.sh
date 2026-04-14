#!/bin/bash
set -e

cd /Users/tmsincomb/sadie

# Install dependencies (idempotent)
poetry install --with dev 2>/dev/null || true

echo "Environment ready."
