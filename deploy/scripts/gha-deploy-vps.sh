#!/usr/bin/env bash
# Deploy remoto no VPS a partir do runner GitHub Actions (#734).
# Exit 42 = SSH Connection timed out (o workflow dispara um segundo job noutro runner).
# Exit 1 = falha que NÃO deve repetir (credencial, git, alembic, health, etc.).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

: "${DEPLOY_HOST:?}"
: "${DEPLOY_USER:?}"
: "${DEPLOY_PATH:?}"
: "${DEPLOY_FRONTEND_DIST:?}"
: "${DEPLOY_SSH_KEY:?}"
: "${VITE_API_URL:?}"

SSH_PORT="${SSH_PORT:-22}"
mkdir -p "${HOME}/.ssh"
DEPLOY_KEY_PATH="${HOME}/.ssh/deploy_key"
SSH_MUX_PATH="${HOME}/.ssh/cm-%r@%h:%p"
printf '%s\n' "$DEPLOY_SSH_KEY" > "$DEPLOY_KEY_PATH"
chmod 600 "$DEPLOY_KEY_PATH"

echo "Runner IPv4 público (cruzar com firewall Hostinger):"
curl -4 -fsS --max-time 15 https://api.ipify.org || echo "(api.ipify.org indisponível)"
echo

echo "ssh-keyscan IPv4 ${DEPLOY_HOST} porta ${SSH_PORT}..."
keyscan_out="$(mktemp)"
keyscan_err="$(mktemp)"
set +e
ssh-keyscan -4 -p "$SSH_PORT" -T 20 -H "$DEPLOY_HOST" >"$keyscan_out" 2>"$keyscan_err"
keyscan_st=$?
set -e
if [ "$keyscan_st" -ne 0 ] || ! grep -q . "$keyscan_out"; then
  echo "::error::ssh-keyscan falhou (não se obteve a host key)."
  cat "$keyscan_err" || true
  if grep -Eqi 'timed out|timeout|Connection timed out' "$keyscan_err"; then
    echo "::error::Causa aparente: timeout de rede (não é Permission denied)."
    rm -f "$keyscan_out" "$keyscan_err"
    echo "::error::SSH Connection timed out (rede runner→VPS). O workflow vai tentar noutro runner."
    exit 42
  fi
  if grep -Eqi 'Name or service not known|Could not resolve' "$keyscan_err"; then
    echo "::error::Causa aparente: DNS — confira DEPLOY_HOST."
  elif grep -Eqi 'Connection refused' "$keyscan_err"; then
    echo "::error::Causa aparente: porta recusada (sshd / DEPLOY_SSH_PORT)."
  fi
  rm -f "$keyscan_out" "$keyscan_err"
  exit 1
fi
cat "$keyscan_out" >> "${HOME}/.ssh/known_hosts"
cat "$keyscan_err" || true
rm -f "$keyscan_out" "$keyscan_err"

REF="${EVENT_REF:-${DEPLOY_GIT_REF:-staging}}"
SKIP_MIGRATIONS="${SKIP_MIGRATIONS:-false}"
RETRY_MAX="${RETRY_MAX:-5}"
RETRY_DELAY="${RETRY_DELAY:-15}"

SSH_BASE=(
  ssh -4
  -i "$DEPLOY_KEY_PATH"
  -p "$SSH_PORT"
  -o StrictHostKeyChecking=yes
  -o AddressFamily=inet
  -o ConnectTimeout=20
  -o ServerAliveInterval=15
  -o ServerAliveCountMax=3
  -o ControlMaster=auto
  -o "ControlPath=${SSH_MUX_PATH}"
  -o ControlPersist=120
)
RSYNC_E="ssh -4 -i ${DEPLOY_KEY_PATH} -p ${SSH_PORT} -o StrictHostKeyChecking=yes -o AddressFamily=inet -o ConnectTimeout=20 -o ControlMaster=auto -o ControlPath=${SSH_MUX_PATH} -o ControlPersist=120"

fail_timeout() {
  echo "::error::SSH Connection timed out (rede runner→VPS). O workflow vai tentar noutro runner."
  exit 42
}

retry_net() {
  local attempt=1 delay="$RETRY_DELAY" log stdin_tmp=""
  log="$(mktemp)"
  if ! [ -t 0 ]; then
    stdin_tmp="$(mktemp)"
    cat > "$stdin_tmp"
  fi
  while true; do
    local ok=0
    if [ -n "$stdin_tmp" ]; then
      if "$@" >"$log" 2>&1 <"$stdin_tmp"; then ok=1; fi
    else
      if "$@" >"$log" 2>&1; then ok=1; fi
    fi
    cat "$log"
    if [ "$ok" -eq 1 ]; then
      rm -f "$log" "$stdin_tmp"
      return 0
    fi
    if grep -Eqi 'Connection timed out|Connection timed out during banner exchange' "$log"; then
      if [ "$attempt" -ge "$RETRY_MAX" ]; then
        rm -f "$log" "$stdin_tmp"
        fail_timeout
      fi
    else
      rm -f "$log" "$stdin_tmp"
      echo "::error::Comando falhou sem timeout de SSH (não há retry noutro runner)."
      return 1
    fi
    echo "Tentativa ${attempt}/${RETRY_MAX} com timeout SSH; nova em ${delay}s..."
    sleep "$delay"
    attempt=$((attempt + 1))
    delay=$((delay + 15))
  done
}

echo "Deploy ref no VPS: ${REF}"

retry_net "${SSH_BASE[@]}" "${DEPLOY_USER}@${DEPLOY_HOST}" \
  "REF='${REF}' DEPLOY_PATH='${DEPLOY_PATH}' bash -s" << 'REMOTE_SCRIPT'
set -ex
cd "$DEPLOY_PATH"
echo "==> Deploy branch/ref: $REF"
git fetch origin
git checkout "$REF"
git reset --hard "origin/$REF"
REMOTE_SCRIPT

ssh_rsync_release() {
  retry_net rsync -avz -e "$RSYNC_E" "$1" "${DEPLOY_USER}@${DEPLOY_HOST}:${DEPLOY_PATH}/$2"
}

ssh_rsync_release "VERSION" ""
ssh_rsync_release "CHANGELOG.md" ""
ssh_rsync_release "docs/releases/manifest.json" "docs/releases/"
ssh_rsync_release "backend/app/data/release_notes.json" "backend/app/data/"
ssh_rsync_release "frontend/public/release-notes.json" "frontend/public/"

retry_net "${SSH_BASE[@]}" "${DEPLOY_USER}@${DEPLOY_HOST}" \
  "REF='${REF}' DEPLOY_PATH='${DEPLOY_PATH}' SKIP_MIGRATIONS='${SKIP_MIGRATIONS}' WEBHOOK_BASE_URL='${VITE_API_URL}' DX_CONNECT_VERSION='${DX_CONNECT_VERSION:-}' bash -s" << 'REMOTE_SCRIPT'
set -ex
cd "$DEPLOY_PATH"
export DX_CONNECT_GIT_SHA="$(git rev-parse --short HEAD)"
echo "==> Commit: $DX_CONNECT_GIT_SHA"
if [ -z "${DX_CONNECT_VERSION:-}" ] && [ -f VERSION ]; then
  export DX_CONNECT_VERSION="$(tr -d '\n\r' < VERSION)"
fi
echo "==> Versão: ${DX_CONNECT_VERSION:-n/a}"
WEBHOOK_BASE_URL="${WEBHOOK_BASE_URL:-}" bash deploy/scripts/ensure-evolution-env.sh backend/.env
COMPOSE="docker compose --env-file backend/.env -f docker-compose.prod.yml"
if [ "$SKIP_MIGRATIONS" != "true" ]; then
  $COMPOSE build --no-cache backend
  $COMPOSE run --rm -T backend alembic upgrade head < /dev/null
else
  $COMPOSE build --no-cache backend
fi
WEBHOOK_BASE_URL="${WEBHOOK_BASE_URL:-}" bash deploy/scripts/restart-backend-prod.sh "$DEPLOY_PATH"
PUBLIC_HEALTH="$(curl -sf "${WEBHOOK_BASE_URL%/}/health")"
echo "Health publico (mesmo host): ${PUBLIC_HEALTH}"
echo "${PUBLIC_HEALTH}" | DX_CONNECT_GIT_SHA="${DX_CONNECT_GIT_SHA}" python3 -c "
import json, os, sys
body = json.load(sys.stdin)
caps = body.get('capabilities') or {}
missing = [k for k in ('pdv_catalogos', 'empresa_pdvs') if not caps.get(k)]
if missing:
    print(f'::error::URL publica sem rotas PDV: faltam {missing}', file=sys.stderr)
    sys.exit(1)
expected = os.environ.get('DX_CONNECT_GIT_SHA', '')
actual = (body.get('git_sha') or '') or ''
if expected and actual and actual != expected:
    print(f'::error::git_sha publico {actual!r} != commit {expected!r}', file=sys.stderr)
    sys.exit(1)
print('OK: health publico no VPS', actual, caps)
"
for i in 1 2 3 4 5 6; do
  curl -sf "http://127.0.0.1:8080" >/dev/null && { echo "Evolution API: OK (8080)"; break; }
  sleep 5
done
curl -sf "http://127.0.0.1:8080" >/dev/null || echo "Evolution API: aguardar ou conferir logs (docker logs dx-connect-evolution-api)"
REMOTE_SCRIPT

retry_net rsync -avz --delete -e "$RSYNC_E" \
  frontend/dist/ "${DEPLOY_USER}@${DEPLOY_HOST}:${DEPLOY_FRONTEND_DIST}/"

API_BASE="${VITE_API_URL%/}"
echo "GET ${API_BASE}/health"
export HEALTH_JSON EXPECTED_DEPLOY_SHA
HEALTH_JSON="$(curl -sf "${API_BASE}/health")"
echo "$HEALTH_JSON"
python3 <<'PY'
import json, os, sys
body = json.loads(os.environ["HEALTH_JSON"])
caps = body.get("capabilities") or {}
need = (
    "settings_empresa_sistema",
    "tenant_atual",
    "settings_email",
    "pdv_catalogos",
    "empresa_pdvs",
)
missing = [k for k in need if not caps.get(k)]
if missing:
    print(
        f"::error::API sem rotas esperadas (backend antigo?): faltam {missing}. git_sha={body.get('git_sha')!r}",
        file=sys.stderr,
    )
    sys.exit(1)
expected_sha = os.environ.get("EXPECTED_DEPLOY_SHA", "") or os.environ.get("GITHUB_SHA", "")[:7]
actual_sha = (body.get("git_sha") or "") or ""
if expected_sha and actual_sha and actual_sha != expected_sha:
    print(
        f"::error::git_sha em producao ({actual_sha!r}) difere do commit deployado ({expected_sha!r}). "
        "Processo antigo pode ainda estar na porta 8000.",
        file=sys.stderr,
    )
    sys.exit(1)
print("OK: capabilities", caps, "git_sha", body.get("git_sha"), "expected", expected_sha)
PY
