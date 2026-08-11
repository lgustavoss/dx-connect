#!/usr/bin/env bash
# Cria a base/stack Docker de um cliente no host (usado em local ou VPS).
# Uso: ./deploy/scripts/saas-create-base.sh <slug> <api-port> [base-domain]
set -euo pipefail

SLUG="${1:-}"
API_PORT="${2:-}"
BASE_DOMAIN="${3:-deskrudder.com.br}"
LOCAL_DEV="${SAAS_PROVISION_LOCAL_DEV:-1}"

usage() {
  echo "Uso: $0 <slug> <api-port> [base-domain]"
  echo "Ex.: $0 codewave 8003 deskrudder.com.br"
  exit 1
}

[[ -n "$SLUG" && -n "$API_PORT" ]] || usage

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

DEST="$ROOT/deploy/clients/$SLUG"
if [[ ! -d "$DEST" ]]; then
  ./deploy/scripts/provision-client.sh --slug "$SLUG" --base-domain "$BASE_DOMAIN" --api-port "$API_PORT"
fi

# Em local, ENVIRONMENT=production bloqueia migrate sem TLS.
if [[ "$LOCAL_DEV" == "1" || "$LOCAL_DEV" == "true" ]]; then
  if [[ -f "$DEST/client.env" ]]; then
    sed -i.bak \
      -e 's/^ENVIRONMENT=production/ENVIRONMENT=development/' \
      -e 's/^DEBUG=false/DEBUG=true/' \
      "$DEST/client.env" 2>/dev/null \
      || sed -i '' \
        -e 's/^ENVIRONMENT=production/ENVIRONMENT=development/' \
        -e 's/^DEBUG=false/DEBUG=true/' \
        "$DEST/client.env"
    rm -f "$DEST/client.env.bak"
  fi
fi

./deploy/scripts/stack-client.sh migrate "$SLUG"
./deploy/scripts/stack-client.sh up "$SLUG"
./deploy/scripts/stack-client.sh seed "$SLUG" || true
./deploy/scripts/stack-client.sh health "$SLUG"

echo ""
echo "Base pronta: slug=$SLUG api=127.0.0.1:$API_PORT"
echo "Confirme no painel SaaS (Confirmar provisionamento) se ainda estiver em aguardando_ops."
