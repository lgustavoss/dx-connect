#!/usr/bin/env bash
# Gera secrets em deploy/admin-center/ — stack comercial (#876).
# Hosts: deskrudder.com.br + api.deskrudder.com.br (não api-admin-center.…).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DEST="$ROOT/deploy/admin-center"
TEMPLATE_COMPOSE="$DEST/docker-compose.stack.yml"
TEMPLATE_ENV="$DEST/client.env.example"

SLUG="admin-center"
API_PORT="8001"

if [[ ! -f "$TEMPLATE_COMPOSE" || ! -f "$TEMPLATE_ENV" ]]; then
  echo "Erro: templates em falta em $DEST"
  exit 1
fi

if [[ -f "$DEST/client.env" ]]; then
  echo "Erro: já existe $DEST/client.env — a stack já foi provisionada. Edite o arquivo ou remova-o para gerar de novo."
  exit 1
fi

PG_PASS="$(openssl rand -hex 16)"
SECRET_KEY="$(openssl rand -hex 32)"
OPS_PASS="$(openssl rand -base64 18 | tr -d '/+=' | head -c 16)"

export CLIENT_SLUG="$SLUG"
export CLIENT_API_PORT="$API_PORT"
export POSTGRES_USER="dxconnect"
export POSTGRES_PASSWORD="$PG_PASS"
export POSTGRES_DB="dxconnect_admin_center"
export DX_CONNECT_GIT_SHA="unknown"

substitute() {
  local src="$1" dest="$2"
  if command -v envsubst >/dev/null 2>&1; then
    envsubst <"$src" >"$dest"
  else
    sed -e "s/\${CLIENT_SLUG}/$CLIENT_SLUG/g" \
        -e "s/\${CLIENT_API_PORT}/$CLIENT_API_PORT/g" \
        -e "s/CLIENT_SLUG/$CLIENT_SLUG/g" \
        -e "s/CLIENT_API_PORT/$CLIENT_API_PORT/g" \
        "$src" >"$dest"
  fi
}

substitute "$TEMPLATE_COMPOSE" "$DEST/docker-compose.yml"

sed -e "s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$PG_PASS/" \
    -e "s/^SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" \
    -e "s/^SEED_SAAS_OPS_PASSWORD=.*/SEED_SAAS_OPS_PASSWORD=$OPS_PASS/" \
    "$TEMPLATE_ENV" >"$DEST/client.env"

chmod 600 "$DEST/client.env" 2>/dev/null || true

echo ""
echo "Painel admin provisionado em: $DEST"
echo ""
echo "  Painel: https://deskrudder.com.br/login/admin"
echo "  API:    https://api.deskrudder.com.br"
echo "  Loopback: 127.0.0.1:$API_PORT"
echo ""
echo "  POSTGRES_DB=$POSTGRES_DB"
echo "  SEED_SAAS_OPS_EMAIL=ops@deskrudder.com.br"
echo "  SEED_SAAS_OPS_PASSWORD=$OPS_PASS  (troque no primeiro acesso; não commite)"
echo ""
echo "Próximos passos:"
echo "  1. Edite $DEST/client.env (Resend, etc.)"
echo "  2. bash deploy/scripts/stack-client.sh migrate admin-center"
echo "  3. bash deploy/scripts/stack-client.sh up admin-center"
echo "  4. bash deploy/scripts/stack-client.sh seed admin-center"
echo "  5. Nginx + DNS + TLS (deploy/admin-center/README.md)"
echo "  6. Build SPA comercial (frontend.env.production.example)"
