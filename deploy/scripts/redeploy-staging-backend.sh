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

COMPOSE="docker compose --env-file backend/.env -f docker-compose.prod.yml"
$COMPOSE build --no-cache backend
$COMPOSE run --rm backend alembic upgrade head
$COMPOSE up -d --build --force-recreate

sleep 3
echo "==> Health local:"
curl -sf "http://127.0.0.1:8000/health" | python3 -m json.tool || curl -sf "http://127.0.0.1:8000/health"
