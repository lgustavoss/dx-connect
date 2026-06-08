#!/usr/bin/env bash
# Redeploy manual do backend (branch staging) no VPS.
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
$COMPOSE run --rm -T backend alembic upgrade head < /dev/null

WEBHOOK_BASE_URL="${WEBHOOK_BASE_URL:-}" bash deploy/scripts/restart-backend-prod.sh "$REPO_DIR"
