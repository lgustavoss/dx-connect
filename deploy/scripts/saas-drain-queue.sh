#!/usr/bin/env bash
# Processa clientes SaaS em aguardando_ops/pendente via API do control-plane e cria a base no host.
# Uso (na raiz do repo, com API em :8000 e login ops):
#   SAAS_OPS_EMAIL=ops@deskrudder.local SAAS_OPS_SENHA=ops123456 ./deploy/scripts/saas-drain-queue.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

API="${SAAS_API_BASE:-http://127.0.0.1:8000}"
EMAIL="${SAAS_OPS_EMAIL:-ops@deskrudder.local}"
SENHA="${SAAS_OPS_SENHA:-ops123456}"
BASE_DOMAIN="${SAAS_PROVISION_BASE_DOMAIN:-deskrudder.com.br}"

TOKEN="$(
  curl -sf -X POST "$API/v1/auth/login" \
    -H 'Content-Type: application/json' \
    -d "{\"email\":\"$EMAIL\",\"senha\":\"$SENHA\"}" \
    | python -c "import sys,json; print(json.load(sys.stdin).get('access_token') or '')"
)"
[[ -n "$TOKEN" ]] || { echo "Falha no login ops em $API"; exit 1; }

python - "$API" "$TOKEN" "$BASE_DOMAIN" <<'PY'
import json, os, subprocess, sys, urllib.request

api, token, base = sys.argv[1], sys.argv[2], sys.argv[3]
req = urllib.request.Request(
    f"{api}/v1/saas/clientes?limit=100",
    headers={"Authorization": f"Bearer {token}"},
)
with urllib.request.urlopen(req, timeout=60) as r:
    data = json.load(r)

items = [
    i for i in data.get("items", [])
    if i.get("provisionamento_status") in ("pendente", "aguardando_ops", "falha")
    and i.get("aprovacao_status") == "aprovado"
    and i.get("api_port")
]
if not items:
    print("Nenhuma licença aprovada à espera de base.")
    sys.exit(0)

root = os.environ.get("SAAS_REPO_ROOT") or os.getcwd()
script = os.path.join(root, "deploy", "scripts", "saas-create-base.sh")

for i in items:
    slug, port, cid = i["slug"], str(i["api_port"]), i["id"]
    print(f"==> Criar base {slug} (id={cid}, port={port})")
    subprocess.run(["bash", script, slug, port, base], check=True, cwd=root)
    body = json.dumps({}).encode()
    conf = urllib.request.Request(
        f"{api}/v1/saas/clientes/{cid}/confirmar-provisionamento",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(conf, timeout=60) as r:
        out = json.load(r)
    print(f"    confirmado: {out.get('provisionamento_status')} stack={out.get('stack_status')}")
PY
