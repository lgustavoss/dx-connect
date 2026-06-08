#!/usr/bin/env bash
# Redeploy manual do backend (branch staging) no VPS — use se /health não listar capabilities de e-mail/tenant.
set -euo pipefail

REPO_DIR="${1:-$(cd "$(dirname "$0")/../.." && pwd)}"
BRANCH="${2:-staging}"

cd "$REPO_DIR"
echo "==> Diretório: $REPO_DIR"
echo "==> Branch: $BRANCH"

git fetch origin
git checkout "$BRANCH"
git pull origin "$BRANCH"
export DX_CONNECT_GIT_SHA="$(git rev-parse --short HEAD)"
echo "==> Commit: $DX_CONNECT_GIT_SHA"

WEBHOOK_BASE_URL="${WEBHOOK_BASE_URL:-}" bash deploy/scripts/ensure-evolution-env.sh backend/.env
COMPOSE="docker compose --env-file backend/.env -f docker-compose.prod.yml"
$COMPOSE build --no-cache backend
$COMPOSE run --rm backend alembic upgrade head
$COMPOSE stop backend || true
$COMPOSE rm -f backend || true
if command -v fuser >/dev/null 2>&1; then
  fuser -k 8000/tcp 2>/dev/null || true
  sleep 2
fi
$COMPOSE up -d --build --force-recreate

sleep 10
echo "==> Container:"
docker ps --filter name=dx-connect-api --format '{{.Names}} {{.Status}}'
echo "==> Health local:"
curl -sf "http://127.0.0.1:8000/health" | python3 -m json.tool || curl -sf "http://127.0.0.1:8000/health"
