#!/usr/bin/env bash
# Reinicia o backend de produção (dx-connect-api) e valida /health local.
# Requer: cwd no clone do repo; DX_CONNECT_GIT_SHA exportado (opcional, valida git_sha).
set -euo pipefail

REPO_DIR="${1:-$(pwd)}"
cd "$REPO_DIR"

WEBHOOK_BASE_URL="${WEBHOOK_BASE_URL:-}" bash deploy/scripts/ensure-evolution-env.sh backend/.env
COMPOSE="docker compose --env-file backend/.env -f docker-compose.prod.yml"

echo "==> Parando backend antigo (compose + container por nome)"
$COMPOSE stop backend 2>/dev/null || true
$COMPOSE rm -f backend 2>/dev/null || true
docker rm -f dx-connect-api 2>/dev/null || true

echo "==> Liberando porta 8000"
if command -v fuser >/dev/null 2>&1; then
  fuser -k 8000/tcp 2>/dev/null || sudo fuser -k 8000/tcp 2>/dev/null || true
  sleep 2
fi
if command -v ss >/dev/null 2>&1 && ss -tlnp 2>/dev/null | grep -q ':8000 '; then
  echo "::error::Porta 8000 ainda em uso. Processos:"
  ss -tlnp | grep ':8000 ' || true
  exit 1
fi

echo "==> Subindo backend (imagem: ${DX_CONNECT_GIT_SHA:-unknown})"
$COMPOSE up -d --build --no-deps --force-recreate backend

echo "==> Aguardando /health"
HEALTH=""
for _ in 1 2 3 4 5 6 7 8 9 10 11 12; do
  if HEALTH="$(curl -sf http://127.0.0.1:8000/health 2>/dev/null)"; then
    break
  fi
  sleep 3
done
if [ -z "${HEALTH}" ]; then
  echo "::error::Backend não respondeu em http://127.0.0.1:8000/health"
  docker ps --filter name=dx-connect-api --format '{{.Names}} {{.Status}}' || true
  docker logs dx-connect-api --tail 40 2>&1 || true
  exit 1
fi

echo "Local health: ${HEALTH}"
echo "${HEALTH}" | DX_CONNECT_GIT_SHA="${DX_CONNECT_GIT_SHA:-}" python3 -c "
import json, os, sys
body = json.load(sys.stdin)
caps = body.get('capabilities') or {}
missing = [k for k in ('pdv_catalogos', 'empresa_pdvs') if not caps.get(k)]
if missing:
    print(f'::error::Backend sem rotas PDV: faltam {missing}', file=sys.stderr)
    sys.exit(1)
expected = os.environ.get('DX_CONNECT_GIT_SHA', '')
actual = (body.get('git_sha') or '') or ''
if expected and actual and actual != expected:
    print(f'::error::git_sha local {actual!r} != commit {expected!r}', file=sys.stderr)
    sys.exit(1)
print('OK: backend local', actual, caps)
"

echo "==> Container:"
docker ps --filter name=dx-connect-api --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}'
docker inspect -f 'StartedAt={{.State.StartedAt}}' dx-connect-api 2>/dev/null || true
