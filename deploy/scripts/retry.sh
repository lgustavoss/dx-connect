#!/usr/bin/env bash
# Repete um comando até sucesso ou esgotar tentativas (deploy via GitHub Actions → VPS).
# Se stdin não for TTY, grava uma vez e reutiliza em cada tentativa (ex.: heredoc → ssh bash -s).
set -euo pipefail

max="${RETRY_MAX:-5}"
delay="${RETRY_DELAY:-15}"
attempt=1
stdin_tmp=""

if ! [ -t 0 ]; then
  stdin_tmp="$(mktemp)"
  cat > "$stdin_tmp"
  trap 'rm -f "$stdin_tmp"' EXIT
fi

run_cmd() {
  if [ -n "$stdin_tmp" ]; then
    "$@" < "$stdin_tmp"
  else
    "$@"
  fi
}

while true; do
  if run_cmd "$@"; then
    exit 0
  fi
  status=$?
  if [ "$attempt" -ge "$max" ]; then
    echo "::error::Comando falhou após ${max} tentativa(s): $*"
    exit "$status"
  fi
  echo "Tentativa ${attempt}/${max} falhou (exit ${status}). Nova tentativa em ${delay}s..."
  sleep "$delay"
  attempt=$((attempt + 1))
done
