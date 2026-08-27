#!/usr/bin/env bash
# Deploy remoto no VPS a partir do runner GitHub Actions (#734 / #880).
# Atualiza stack DuplexSoft (compose legado) + stack admin-center em separado.
# Exit 42 = SSH Connection timed out (o workflow dispara um segundo job noutro runner).
# Exit 1 = falha que NÃO deve repetir (credencial, git, alembic, health, etc.).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

: "${DEPLOY_HOST:?}"
: "${DEPLOY_USER:?}"
: "${DEPLOY_PATH:?}"
: "${DEPLOY_FRONTEND_DIST:?}"
: "${DEPLOY_FRONTEND_DIST_ADMIN:?}"
: "${DEPLOY_SSH_KEY:?}"
: "${VITE_API_URL:?}"
: "${VITE_API_URL_ADMIN:?}"

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
echo "API DuplexSoft (cliente): ${VITE_API_URL}"
echo "API admin-center:         ${VITE_API_URL_ADMIN}"

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

# --- Stack DuplexSoft (compose legado + backend/.env; NÃO reativa control-plane) ---
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

# Guarda: não reativar control-plane no cliente
if grep -Eq '^SAAS_CONTROL_PLANE=true' backend/.env 2>/dev/null; then
  echo "::error::backend/.env da DuplexSoft tem SAAS_CONTROL_PLANE=true — cutover #878 exige false."
  exit 1
fi

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
echo "Health DuplexSoft: ${PUBLIC_HEALTH}"
echo "${PUBLIC_HEALTH}" | DX_CONNECT_GIT_SHA="${DX_CONNECT_GIT_SHA}" python3 -c "
import json, os, sys
body = json.load(sys.stdin)
caps = body.get('capabilities') or {}
if caps.get('saas_control_plane'):
    print('::error::DuplexSoft respondeu saas_control_plane=true (não pode após #878).', file=sys.stderr)
    sys.exit(1)
missing = [k for k in ('pdv_catalogos', 'empresa_pdvs') if not caps.get(k)]
if missing:
    print(f'::error::URL DuplexSoft sem rotas PDV: faltam {missing}', file=sys.stderr)
    sys.exit(1)
expected = os.environ.get('DX_CONNECT_GIT_SHA', '')
actual = (body.get('git_sha') or '') or ''
if expected and actual and actual != expected:
    print(f'::error::git_sha DuplexSoft {actual!r} != commit {expected!r}', file=sys.stderr)
    sys.exit(1)
print('OK: DuplexSoft', actual, 'saas_control_plane=false')
"
for i in 1 2 3 4 5 6; do
  curl -sf "http://127.0.0.1:8080" >/dev/null && { echo "Evolution API: OK (8080)"; break; }
  sleep 5
done
curl -sf "http://127.0.0.1:8080" >/dev/null || echo "Evolution API: aguardar ou conferir logs (docker logs dx-connect-evolution-api)"
REMOTE_SCRIPT

# --- Stack admin-center (Postgres + API comerciais) ---
retry_net "${SSH_BASE[@]}" "${DEPLOY_USER}@${DEPLOY_HOST}" \
  "REF='${REF}' DEPLOY_PATH='${DEPLOY_PATH}' SKIP_MIGRATIONS='${SKIP_MIGRATIONS}' ADMIN_API_URL='${VITE_API_URL_ADMIN}' DX_CONNECT_VERSION='${DX_CONNECT_VERSION:-}' bash -s" << 'REMOTE_SCRIPT'
set -ex
cd "$DEPLOY_PATH"
export DX_CONNECT_GIT_SHA="$(git rev-parse --short HEAD)"
if [ -z "${DX_CONNECT_VERSION:-}" ] && [ -f VERSION ]; then
  export DX_CONNECT_VERSION="$(tr -d '\n\r' < VERSION)"
fi

if [ ! -f deploy/admin-center/client.env ] || [ ! -f deploy/admin-center/docker-compose.yml ]; then
  echo "::error::deploy/admin-center não provisionado no VPS (falta client.env / docker-compose.yml)."
  exit 1
fi

if [ "$SKIP_MIGRATIONS" != "true" ]; then
  bash deploy/scripts/stack-client.sh migrate admin-center
fi
bash deploy/scripts/stack-client.sh up admin-center

# Health loopback (fonte de verdade; público pode falhar via Cloudflare no runner)
for _ in 1 2 3 4 5 6 7 8 9 10; do
  if curl -sf http://127.0.0.1:8001/health >/tmp/admin_health.json; then
    break
  fi
  sleep 3
done
test -s /tmp/admin_health.json
echo "Health admin-center (loopback): $(cat /tmp/admin_health.json)"
DX_CONNECT_GIT_SHA="${DX_CONNECT_GIT_SHA}" python3 -c "
import json, os, sys
body = json.load(open('/tmp/admin_health.json'))
caps = body.get('capabilities') or {}
if not caps.get('saas_control_plane'):
    print('::error::admin-center sem saas_control_plane=true.', file=sys.stderr)
    sys.exit(1)
expected = os.environ.get('DX_CONNECT_GIT_SHA', '')
actual = (body.get('git_sha') or '') or ''
if expected and actual and actual != expected:
    print(f'::error::git_sha admin-center {actual!r} != commit {expected!r}', file=sys.stderr)
    sys.exit(1)
print('OK: admin-center', actual, 'saas_control_plane=true')
"
# G4: mesmo projeto Compose do stack (dx-connect-admin-center). `compose run` na pasta
# admin-center sem --project-name tentava criar outro Postgres e falhava por nome duplicado.
if [ -n "${DX_CONNECT_VERSION:-}" ]; then
  bash deploy/scripts/stack-client.sh exec admin-center \
    python scripts/concluir_solicitacoes_release.py --version "${DX_CONNECT_VERSION}" \
    || echo "::warning::concluir_solicitacoes_release falhou (deploy continua)"
fi
if [ -n "${ADMIN_API_URL:-}" ]; then
  if PUBLIC_HEALTH="$(curl -sf --max-time 20 "${ADMIN_API_URL%/}/health")"; then
    echo "Health admin-center (público): ${PUBLIC_HEALTH}"
  else
    echo "::warning::Health público admin-center falhou (Cloudflare/rede); loopback OK."
  fi
fi
REMOTE_SCRIPT

# --- Frontends (dois artefactos) ---
retry_net rsync -avz --delete -e "$RSYNC_E" \
  frontend/dist-duplexsoft/ "${DEPLOY_USER}@${DEPLOY_HOST}:${DEPLOY_FRONTEND_DIST}/"

retry_net rsync -avz --delete -e "$RSYNC_E" \
  frontend/dist-admin-center/ "${DEPLOY_USER}@${DEPLOY_HOST}:${DEPLOY_FRONTEND_DIST_ADMIN}/"

check_health() {
  local label="$1" url="$2" expect_saas="$3"
  local json
  echo "GET ${url}/health (${label})"
  if ! json="$(curl -sf --max-time 20 "${url%/}/health")"; then
    echo "::error::${label}: curl health falhou (${url%/}/health)."
    return 1
  fi
  echo "$json"
  EXPECTED_DEPLOY_SHA="${EXPECTED_DEPLOY_SHA:-}" LABEL="$label" EXPECT_SAAS="$expect_saas" HEALTH_JSON="$json" python3 <<'PY'
import json, os, sys
body = json.loads(os.environ["HEALTH_JSON"])
caps = body.get("capabilities") or {}
label = os.environ["LABEL"]
expect = os.environ["EXPECT_SAAS"].lower() == "true"
got = bool(caps.get("saas_control_plane"))
if got != expect:
    print(
        f"::error::{label}: saas_control_plane={got} (esperado {expect}).",
        file=sys.stderr,
    )
    sys.exit(1)
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
        f"::error::{label}: faltam capabilities {missing}. git_sha={body.get('git_sha')!r}",
        file=sys.stderr,
    )
    sys.exit(1)
expected_sha = os.environ.get("EXPECTED_DEPLOY_SHA", "") or os.environ.get("GITHUB_SHA", "")[:7]
actual_sha = (body.get("git_sha") or "") or ""
if expected_sha and actual_sha and actual_sha != expected_sha:
    print(
        f"::error::{label}: git_sha {actual_sha!r} != {expected_sha!r}.",
        file=sys.stderr,
    )
    sys.exit(1)
print(f"OK: {label} capabilities", caps.get("saas_control_plane"), "git_sha", actual_sha)
PY
}

check_health "DuplexSoft" "${VITE_API_URL}" "false"
# admin-center: validação forte já foi no loopback (SSH). Público é soft — Cloudflare
# no runner GHA às vezes devolve não-200 (curl exit 22) mesmo com API saudável.
if ! check_health "admin-center" "${VITE_API_URL_ADMIN}" "true"; then
  echo "::warning::Health público admin-center falhou no runner; loopback SSH já validou saas=true."
fi
