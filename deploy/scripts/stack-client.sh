#!/usr/bin/env bash
# Operações no stack Docker: cliente (deploy/clients/<slug>/) ou painel ops (deploy/admin-center/).
set -euo pipefail

CMD="${1:-}"
SLUG="${2:-}"

usage() {
  echo "Uso: $0 <comando> <slug|admin-center>"
  echo "Comandos: migrate | up | down | logs | seed | health"
  echo "Painel ops: $0 migrate admin-center"
  exit 1
}

[[ -n "$CMD" && -n "$SLUG" ]] || usage

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
if [[ "$SLUG" == "admin-center" ]]; then
  CLIENT_DIR="$ROOT/deploy/admin-center"
else
  CLIENT_DIR="$ROOT/deploy/clients/$SLUG"
fi
COMPOSE_FILE="$CLIENT_DIR/docker-compose.yml"
PROJECT="dx-connect-$SLUG"

if [[ ! -f "$COMPOSE_FILE" ]]; then
  if [[ "$SLUG" == "admin-center" ]]; then
    echo "Erro: não encontrado $COMPOSE_FILE — rode deploy/scripts/provision-control-plane.sh primeiro."
  else
    echo "Erro: não encontrado $COMPOSE_FILE — rode provision-client.sh primeiro."
  fi
  exit 1
fi

cd "$ROOT"

load_env() {
  set -a
  # shellcheck disable=SC1090
  source "$CLIENT_DIR/client.env"
  set +a
  export DX_CONNECT_GIT_SHA="${DX_CONNECT_GIT_SHA:-$(git rev-parse --short HEAD 2>/dev/null || echo unknown)}"
}

dc() {
  docker compose -f "$COMPOSE_FILE" --project-name "$PROJECT" "$@"
}

case "$CMD" in
  migrate)
    load_env
    dc run --rm backend alembic upgrade head
    ;;
  up)
    load_env
    dc up -d --build
    echo "API em 127.0.0.1:${CLIENT_API_PORT:-?} (ver client.env)"
    ;;
  down)
    load_env
    dc down
    ;;
  logs)
    load_env
    dc logs -f backend
    ;;
  seed)
    load_env
    dc exec backend python -m app.seed
    ;;
  health)
    load_env
    PORT="${CLIENT_API_PORT:?CLIENT_API_PORT ausente em client.env}"
    curl -sf "http://127.0.0.1:${PORT}/health" | python3 -m json.tool 2>/dev/null || curl -sf "http://127.0.0.1:${PORT}/health"
    echo ""
    ;;
  *)
    echo "Comando desconhecido: $CMD"
    usage
    ;;
esac
