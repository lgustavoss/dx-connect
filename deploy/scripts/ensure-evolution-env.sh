#!/usr/bin/env bash
# Garante variáveis mínimas da Evolution em backend/.env (idempotente).
# Uso: WEBHOOK_BASE_URL=https://api.exemplo.com ./deploy/scripts/ensure-evolution-env.sh

set -euo pipefail

ENV_FILE="${1:-backend/.env}"
WEBHOOK_BASE_URL="${WEBHOOK_BASE_URL:-}"

touch "$ENV_FILE"

append_if_missing() {
  local key="$1"
  local value="$2"
  if ! grep -qE "^${key}=" "$ENV_FILE" 2>/dev/null; then
    echo "${key}=${value}" >>"$ENV_FILE"
    echo "==> ${key} adicionado em ${ENV_FILE}"
  fi
}

rand_hex() {
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex "$1"
  else
    head -c "$1" /dev/urandom | od -An -tx1 | tr -d ' \n'
  fi
}

append_if_missing "EVOLUTION_INTERNAL_BASE_URL" "http://127.0.0.1:8080"
append_if_missing "EVOLUTION_POSTGRES_USER" "evolution"
append_if_missing "EVOLUTION_POSTGRES_DB" "evolution"
append_if_missing "EVOLUTION_POSTGRES_PASSWORD" "$(rand_hex 16)"
append_if_missing "EVOLUTION_GLOBAL_API_KEY" "$(rand_hex 24)"
append_if_missing "EVOLUTION_SERVER_URL" "http://127.0.0.1:8080"

if [ -n "$WEBHOOK_BASE_URL" ]; then
  append_if_missing "DX_CONNECT_WEBHOOK_BASE_URL" "${WEBHOOK_BASE_URL%/}"
fi
