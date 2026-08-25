#!/usr/bin/env bash
# Cria deploy/clients/<slug>/ a partir de _template (Fase 1 — #191).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TEMPLATE="$ROOT/deploy/clients/_template"

SLUG=""
BASE_DOMAIN=""
API_PORT=""

usage() {
  echo "Uso: $0 --slug <slug> --base-domain <deskrudder.com.br> --api-port <porta>"
  echo "Ex.: $0 --slug cliente01 --base-domain deskrudder.com.br --api-port 8001"
  echo "  App:  https://cliente01.deskrudder.com.br"
  echo "  API:  https://api-cliente01.deskrudder.com.br"
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --slug) SLUG="${2:-}"; shift 2 ;;
    --base-domain) BASE_DOMAIN="${2:-}"; shift 2 ;;
    --api-port) API_PORT="${2:-}"; shift 2 ;;
    -h|--help) usage ;;
    *) echo "Argumento desconhecido: $1"; usage ;;
  esac
done

[[ -n "$SLUG" ]] || usage
[[ -n "$BASE_DOMAIN" ]] || usage
[[ -n "$API_PORT" ]] || usage

if [[ ! "$SLUG" =~ ^[a-z][a-z0-9-]*$ ]]; then
  echo "Erro: --slug deve ser minúsculo alfanumérico com hífens (ex.: duplexsoft)."
  exit 1
fi

if [[ "$SLUG" == "deskrudder" || "$SLUG" == "admin-center" ]]; then
  echo "Erro: o painel ops fica em deploy/admin-center/. Use deploy/scripts/provision-control-plane.sh"
  exit 1
fi

if [[ ! "$API_PORT" =~ ^[0-9]+$ ]] || [[ "$API_PORT" -lt 1024 ]] || [[ "$API_PORT" -gt 65535 ]]; then
  echo "Erro: --api-port deve ser um número entre 1024 e 65535."
  exit 1
fi

DEST="$ROOT/deploy/clients/$SLUG"
if [[ -e "$DEST" ]]; then
  echo "Erro: já existe $DEST — remova ou escolha outro slug."
  exit 1
fi

mkdir -p "$DEST"

PG_PASS="$(openssl rand -hex 16)"
SECRET_KEY="$(openssl rand -hex 32)"
ADMIN_PASS="$(openssl rand -base64 18 | tr -d '/+=' | head -c 16)"

export CLIENT_SLUG="$SLUG"
export BASE_DOMAIN="$BASE_DOMAIN"
export CLIENT_API_PORT="$API_PORT"
export POSTGRES_USER="dxconnect"
export POSTGRES_PASSWORD="$PG_PASS"
export POSTGRES_DB="dxconnect_${SLUG//-/_}"
export DX_CONNECT_GIT_SHA="unknown"

substitute() {
  local src="$1" dest="$2"
  if command -v envsubst >/dev/null 2>&1; then
    envsubst <"$src" >"$dest"
  else
    sed -e "s/\${CLIENT_SLUG}/$CLIENT_SLUG/g" \
        -e "s/\${BASE_DOMAIN}/$BASE_DOMAIN/g" \
        -e "s/\${CLIENT_API_PORT}/$CLIENT_API_PORT/g" \
        -e "s/CLIENT_SLUG/$CLIENT_SLUG/g" \
        -e "s/BASE_DOMAIN/$BASE_DOMAIN/g" \
        -e "s/CLIENT_API_PORT/$CLIENT_API_PORT/g" \
        "$src" >"$dest"
  fi
}

substitute "$TEMPLATE/docker-compose.stack.yml" "$DEST/docker-compose.yml"

# client.env — substituições fixas no example
APP_ORIGIN="https://${SLUG}.${BASE_DOMAIN}"
API_HOST="api-${SLUG}.${BASE_DOMAIN}"

sed -e "s/^CLIENT_SLUG=.*/CLIENT_SLUG=$SLUG/" \
    -e "s/^CLIENT_API_PORT=.*/CLIENT_API_PORT=$API_PORT/" \
    -e "s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$PG_PASS/" \
    -e "s/^POSTGRES_DB=.*/POSTGRES_DB=$POSTGRES_DB/" \
    -e "s/^SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" \
    -e "s|^CORS_ORIGINS=.*|CORS_ORIGINS=$APP_ORIGIN,https://localhost|" \
    -e "s/^ALLOWED_HOSTS=.*/ALLOWED_HOSTS=$API_HOST,127.0.0.1,localhost/" \
    -e "s/^CONNECT_APP_BASE_DOMAIN=.*/CONNECT_APP_BASE_DOMAIN=$BASE_DOMAIN/" \
    -e "s/^SEED_ADMIN_PASSWORD=.*/SEED_ADMIN_PASSWORD=$ADMIN_PASS/" \
    -e "s/exemplo/${SLUG}/g" \
    -e "s/deskrudder\.com\.br/${BASE_DOMAIN}/g" \
    "$TEMPLATE/client.env.example" >"$DEST/client.env"

substitute "$TEMPLATE/nginx.site.conf.example" "$DEST/nginx.site.conf"
sed -i.bak "s|FRONTEND_DIST|/var/www/dx-connect/clients/$SLUG/dist|g" "$DEST/nginx.site.conf" 2>/dev/null \
  || sed -i '' "s|FRONTEND_DIST|/var/www/dx-connect/clients/$SLUG/dist|g" "$DEST/nginx.site.conf"
rm -f "$DEST/nginx.site.conf.bak"

substitute "$TEMPLATE/frontend.env.production.example" "$DEST/frontend.env.production.example"

chmod 600 "$DEST/client.env" 2>/dev/null || true

echo ""
echo "Cliente provisionado em: $DEST"
echo ""
echo "  App:  $APP_ORIGIN"
echo "  API:  https://$API_HOST"
echo "  Porta local API: 127.0.0.1:$API_PORT"
echo ""
echo "  POSTGRES_DB=$POSTGRES_DB"
echo "  SEED_ADMIN_EMAIL=admin@email.com (ajuste em client.env se quiser)"
echo "  SEED_ADMIN_PASSWORD=$ADMIN_PASS  (guarde em local seguro)"
echo ""
echo "Próximos passos:"
echo "  1. Edite $DEST/client.env (Resend, e-mail, token de ingest SaaS, etc.)"
echo "  2. bash deploy/scripts/stack-client.sh migrate $SLUG"
echo "  3. bash deploy/scripts/stack-client.sh up $SLUG"
echo "  4. bash deploy/scripts/stack-client.sh seed $SLUG"
echo "  5. Build frontend + Nginx (ver deploy/clients/README.md)"
