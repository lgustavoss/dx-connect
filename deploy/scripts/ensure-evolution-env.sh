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

legacy_runtime_url() {
  case "$1" in
    *duplexsoft.com.br*) return 0 ;;
    *) return 1 ;;
  esac
}

if [ -n "$WEBHOOK_BASE_URL" ]; then
  value="${WEBHOOK_BASE_URL%/}"
  if legacy_runtime_url "$value"; then
    echo "::error::DX_CONNECT_WEBHOOK_BASE_URL legado recusado (${value}). Use https://api-<slug>.deskrudder.com.br."
    exit 1
  fi
  if grep -qE '^DX_CONNECT_WEBHOOK_BASE_URL=' "$ENV_FILE" 2>/dev/null; then
    current="$(grep -E '^DX_CONNECT_WEBHOOK_BASE_URL=' "$ENV_FILE" | tail -n 1 | cut -d= -f2- | tr -d '\r')"
    if legacy_runtime_url "$current"; then
      tmp="$(mktemp)"
      awk -v value="$value" '
        BEGIN { done = 0 }
        /^DX_CONNECT_WEBHOOK_BASE_URL=/ {
          if (!done) {
            print "DX_CONNECT_WEBHOOK_BASE_URL=" value
            done = 1
          }
          next
        }
        { print }
      ' "$ENV_FILE" >"$tmp"
      mv "$tmp" "$ENV_FILE"
      echo "==> DX_CONNECT_WEBHOOK_BASE_URL legado substituído em ${ENV_FILE}"
    fi
  else
    echo "DX_CONNECT_WEBHOOK_BASE_URL=${value}" >>"$ENV_FILE"
    echo "==> DX_CONNECT_WEBHOOK_BASE_URL adicionado em ${ENV_FILE}"
  fi
fi
