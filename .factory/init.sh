#!/usr/bin/env bash
set -euo pipefail

cd /Users/tmsincomb/sadie

# Install dependencies (idempotent)
poetry install --with dev 2>/dev/null || true

echo "SADIE environment ready"
