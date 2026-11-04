#!/usr/bin/env bash
# Operações no stack Docker: cliente (deploy/clients/<slug>/) ou painel ops (deploy/admin-center/).
set -euo pipefail

CMD="${1:-}"
SLUG="${2:-}"

usage() {
  echo "Uso: $0 <comando> <slug|admin-center> [args...]"
  echo "Comandos: migrate | backup | up | down | logs | seed | health | exec | run"
  echo "Backup pré-migração: $0 backup admin-center  (grava em backups/ e mantém as 5 últimas)"
  echo "Painel ops: $0 migrate admin-center"
  echo "Exec no backend (stack já no ar): $0 exec admin-center python scripts/foo.py"
  exit 1
}

[[ -n "$CMD" && -n "$SLUG" ]] || usage
shift 2

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
  backup)
    load_env
    # Backup lógico antes de migrations, dentro do próprio Postgres do stack
    # (mesma versão do servidor) e copiado para o host. Falha = deploy para.
    BACKUP_DIR="${BACKUP_DIR:-$ROOT/backups}"
    mkdir -p "$BACKUP_DIR"
    TS="$(date -u +%Y%m%dT%H%M%SZ)"
    OUT="$BACKUP_DIR/pre-deploy-${SLUG}-${TS}.dump"
    TMP="/tmp/pre-deploy-${SLUG}-${TS}.dump"
    dc exec -T db sh -c "pg_dump -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" --format=custom --file='${TMP}'"
    dc exec -T db sh -c "pg_restore --list '${TMP}' > /dev/null"
    CID="$(dc ps -q db)"
    docker cp "${CID}:${TMP}" "$OUT"
    dc exec -T db rm -f "$TMP"
    test -s "$OUT"
    ls -1t "$BACKUP_DIR"/pre-deploy-"${SLUG}"-*.dump 2>/dev/null | tail -n +6 | xargs -r rm -f
    echo "==> Backup pré-deploy OK: $OUT ($(du -h "$OUT" | cut -f1))"
    ;;
  migrate)
    load_env
    # -T + stdin fechado: em SSH/`bash -s` o attach do compose consumiria o resto do script
    # (mesmo padrão de gha-deploy-vps.sh na stack DuplexSoft).
    dc run --rm -T backend alembic upgrade head </dev/null
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
  exec)
    load_env
    # -T: GitHub Actions / SSH sem TTY. Sempre --project-name dx-connect-<slug>
    # (compose na pasta admin-center sozinho cria projeto "admin-center" e conflita com o Postgres).
    dc exec -T backend "$@"
    ;;
  run)
    load_env
    dc run --rm -T backend "$@" </dev/null
    ;;
  *)
    echo "Comando desconhecido: $CMD"
    usage
    ;;
esac
