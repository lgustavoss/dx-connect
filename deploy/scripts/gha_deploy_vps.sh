#!/usr/bin/env bash
# Deploy SSH no VPS a partir do GitHub Actions (#734).
# Força IPv4, diagnostica keyscan/IP do runner e classifica timeout (exit 75)
# vs falha de credencial/comando (exit 1).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RETRY_SH="${ROOT}/deploy/scripts/retry.sh"
LOG="${DEPLOY_SSH_LOG:-${RUNNER_TEMP:-/tmp}/deploy-ssh.log}"
mkdir -p "$(dirname "$LOG")"
: >"$LOG"

EXIT_TIMEOUT=75

die_timeout() {
  echo "::error::$*" | tee -a "$LOG"
  exit "$EXIT_TIMEOUT"
}

die_other() {
  echo "::error::$*" | tee -a "$LOG"
  exit 1
}

classify_and_exit() {
  local rc="${1:-1}"
  if grep -qiE 'permission denied \(publickey\)|permission denied \(keyboard-interactive,publickey\)' "$LOG"; then
    die_other "SSH: Permission denied (publickey) — não é timeout de rede. Sem retry noutro runner. Confira DEPLOY_SSH_KEY / authorized_keys."
  fi
  if grep -qiE 'connection timed out|connect timed out|operation timed out' "$LOG"; then
    die_timeout "SSH: Connection timed out neste runner (IPv4 ${RUNNER_PUBLIC_IPV4:-desconhecido}). O workflow pode repetir noutro job."
  fi
  die_other "Deploy SSH falhou (exit ${rc}) — não classificado como timeout de rede. Ver log."
}

retry() {
  bash "$RETRY_SH" "$@"
}

run_logged() {
  local rc=0
  set +e
  set -o pipefail
  "$@" 2>&1 | tee -a "$LOG"
  rc=${PIPESTATUS[0]}
  set +o pipefail
  set -e
  if [ "$rc" -ne 0 ]; then
    classify_and_exit "$rc"
  fi
}

if [ -z "${DEPLOY_HOST:-}" ] || [ -z "${DEPLOY_USER:-}" ] || [ -z "${DEPLOY_PATH:-}" ] || [ -z "${DEPLOY_FRONTEND_DIST:-}" ]; then
  die_other "Defina DEPLOY_HOST, DEPLOY_USER, DEPLOY_PATH e DEPLOY_FRONTEND_DIST."
fi
if [ -z "${DEPLOY_SSH_KEY:-}" ]; then
  die_other "Defina DEPLOY_SSH_KEY."
fi
if [ ! -f "$RETRY_SH" ]; then
  die_other "Script de retry em falta: ${RETRY_SH}"
fi

if [ -f "${ROOT}/deploy-meta.env" ]; then
  # shellcheck disable=SC1091
  set -a
  # Valores gerados no job prepare (SHA / CalVer); não contém secrets.
  source "${ROOT}/deploy-meta.env"
  set +a
fi

P="${SSH_PORT:-22}"
DEPLOY_KEY_PATH="${DEPLOY_KEY_PATH:-${HOME}/.ssh/deploy_key}"
SSH_MUX_PATH="${SSH_MUX_PATH:-${HOME}/.ssh/cm-%r@%h:%p}"
SSH_CONFIG="${HOME}/.ssh/deploy_config"
REF="${EVENT_REF:-${DEPLOY_GIT_REF:-staging}}"
SKIP_MIGRATIONS="${SKIP_MIGRATIONS:-false}"
API_BASE="${VITE_API_URL:-}"
API_BASE="${API_BASE%/}"

echo "Deploy ref no VPS: ${REF}" | tee -a "$LOG"

# --- IP público IPv4 do runner (cruzar com firewall Hostinger)
RUNNER_PUBLIC_IPV4="$(curl -4 -fsS --max-time 10 https://api.ipify.org || true)"
if [ -z "$RUNNER_PUBLIC_IPV4" ]; then
  RUNNER_PUBLIC_IPV4="$(curl -4 -fsS --max-time 10 https://ipv4.icanhazip.com | tr -d '\n\r' || true)"
fi
RUNNER_PUBLIC_IPV4="${RUNNER_PUBLIC_IPV4:-desconhecido}"
echo "IP público IPv4 do runner: ${RUNNER_PUBLIC_IPV4}" | tee -a "$LOG"
echo "DEPLOY_HOST=${DEPLOY_HOST} SSH_PORT=${P} AddressFamily=inet (ssh -4)" | tee -a "$LOG"

mkdir -p ~/.ssh
chmod 700 ~/.ssh
printf '%s\n' "$DEPLOY_SSH_KEY" >"$DEPLOY_KEY_PATH"
chmod 600 "$DEPLOY_KEY_PATH"

cat >"$SSH_CONFIG" <<EOF
Host deploy-vps
  HostName ${DEPLOY_HOST}
  User ${DEPLOY_USER}
  Port ${P}
  IdentityFile ${DEPLOY_KEY_PATH}
  IdentitiesOnly yes
  AddressFamily inet
  ConnectTimeout 20
  ServerAliveInterval 15
  ServerAliveCountMax 3
  StrictHostKeyChecking accept-new
  ControlMaster auto
  ControlPath ${SSH_MUX_PATH}
  ControlPersist 120
EOF
chmod 600 "$SSH_CONFIG"

# --- ssh-keyscan IPv4: falha explícita (sem || true)
KEYSCAN_OUT="$(mktemp)"
KEYSCAN_ERR="$(mktemp)"
set +e
ssh-keyscan -4 -p "$P" -T 20 -H "$DEPLOY_HOST" >"$KEYSCAN_OUT" 2>"$KEYSCAN_ERR"
KS_RC=$?
set -e
tee -a "$LOG" <"$KEYSCAN_ERR"
if [ ! -s "$KEYSCAN_OUT" ]; then
  echo "::error::ssh-keyscan não obteve host key de ${DEPLOY_HOST} (porta ${P}, IPv4, timeout 20s). exit=${KS_RC}" | tee -a "$LOG"
  if grep -qiE 'timed out|timeout' "$KEYSCAN_ERR"; then
    die_timeout "Causa: timeout TCP no keyscan (rede/firewall/IPv6). IP do runner: ${RUNNER_PUBLIC_IPV4}."
  fi
  if grep -qiE 'name or service not known|could not resolve|temporary failure in name resolution|no address associated' "$KEYSCAN_ERR"; then
    die_other "Causa: DNS não resolveu ${DEPLOY_HOST}."
  fi
  if grep -qiE 'connection refused' "$KEYSCAN_ERR"; then
    die_other "Causa: conexão recusada (sshd ou porta ${P})."
  fi
  die_other "Causa: keyscan sem host key (ver stderr). IP do runner: ${RUNNER_PUBLIC_IPV4}."
fi
cat "$KEYSCAN_OUT" >>~/.ssh/known_hosts
echo "ssh-keyscan OK (IPv4): $(wc -l <"$KEYSCAN_OUT") chave(s)" | tee -a "$LOG"
rm -f "$KEYSCAN_OUT" "$KEYSCAN_ERR"

ssh_base() {
  ssh -4 -F "$SSH_CONFIG" deploy-vps "$@"
}

ssh_rsync() {
  local src="$1" dest="$2"
  rsync -avz \
    -e "ssh -4 -F ${SSH_CONFIG} -o AddressFamily=inet" \
    "$src" "deploy-vps:${dest}"
}

export SSH_CONFIG
export -f ssh_base ssh_rsync

# --- Git pull
run_logged retry ssh_base \
  "REF='${REF}' DEPLOY_PATH='${DEPLOY_PATH}' bash -s" <<'REMOTE_SCRIPT'
set -ex
cd "$DEPLOY_PATH"
echo "==> Deploy branch/ref: $REF"
git fetch origin
git checkout "$REF"
git reset --hard "origin/$REF"
REMOTE_SCRIPT

# --- Artefatos de release
run_logged retry ssh_rsync "${ROOT}/VERSION" "${DEPLOY_PATH}/"
run_logged retry ssh_rsync "${ROOT}/CHANGELOG.md" "${DEPLOY_PATH}/"
run_logged retry ssh_rsync "${ROOT}/docs/releases/manifest.json" "${DEPLOY_PATH}/docs/releases/"
run_logged retry ssh_rsync "${ROOT}/backend/app/data/release_notes.json" "${DEPLOY_PATH}/backend/app/data/"
run_logged retry ssh_rsync "${ROOT}/frontend/public/release-notes.json" "${DEPLOY_PATH}/frontend/public/"

# --- Alembic + compose
run_logged retry ssh_base \
  "REF='${REF}' DEPLOY_PATH='${DEPLOY_PATH}' SKIP_MIGRATIONS='${SKIP_MIGRATIONS}' WEBHOOK_BASE_URL='${API_BASE}' DX_CONNECT_VERSION='${DX_CONNECT_VERSION:-}' bash -s" <<'REMOTE_SCRIPT'
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

# --- Frontend dist
if [ ! -d "${ROOT}/frontend/dist" ]; then
  die_other "frontend/dist em falta no runner — o job prepare tem de enviar o artefacto."
fi
run_logged retry rsync -avz --delete \
  -e "ssh -4 -F ${SSH_CONFIG} -o AddressFamily=inet" \
  "${ROOT}/frontend/dist/" "deploy-vps:${DEPLOY_FRONTEND_DIST}/"

# --- Health público
if [ -z "$API_BASE" ]; then
  die_other "VITE_API_URL vazio — não dá para verificar /health."
fi
echo "GET ${API_BASE}/health" | tee -a "$LOG"
HEALTH_JSON="$(curl -sf "${API_BASE}/health")"
echo "$HEALTH_JSON" | tee -a "$LOG"
EXPECTED_DEPLOY_SHA="${EXPECTED_DEPLOY_SHA:-}"
export HEALTH_JSON EXPECTED_DEPLOY_SHA
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

echo "Deploy VPS concluído (runner IPv4 ${RUNNER_PUBLIC_IPV4})."
