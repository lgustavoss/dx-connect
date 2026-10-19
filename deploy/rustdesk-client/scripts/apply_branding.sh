#!/usr/bin/env bash
# Wrapper: aplica branding via apply_branding.py
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec python3 "$ROOT/scripts/apply_branding.py" "$@"
