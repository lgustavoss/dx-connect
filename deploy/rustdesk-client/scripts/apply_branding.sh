#!/usr/bin/env bash
# Aplica nome DeskRudder + ícones + servidor Duplex num clone do rustdesk (Windows build).
# Uso (Git Bash / Linux / macOS):
#   git clone --recurse-submodules https://github.com/rustdesk/rustdesk.git
#   bash deploy/rustdesk-client/scripts/apply_branding.sh /caminho/para/rustdesk
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="${1:-}"
if [[ -z "$SRC" || ! -d "$SRC/.git" ]]; then
  echo "Uso: $0 /caminho/para/clone/rustdesk" >&2
  exit 1
fi

CFG="$ROOT/server.config.json"
BRAND="$ROOT/branding"
HOST="$(python3 -c "import json; print(json.load(open('$CFG'))['host'])")"
KEY="$(python3 -c "import json; print(json.load(open('$CFG'))['key'])")"

echo ">> Branding em $SRC"
echo "   host=$HOST"

# Ícones
cp -f "$BRAND/icon.ico" "$SRC/res/icon.ico"
cp -f "$BRAND/32x32.png" "$SRC/res/32x32.png"
cp -f "$BRAND/128x128.png" "$SRC/res/128x128.png"
cp -f "$BRAND/128x128@2x.png" "$SRC/res/128x128@2x.png"
# Outros PNG comuns no res/
for f in 16 32 48 64 128 256; do
  if [[ -f "$BRAND/deskrudder-$f.png" ]]; then
    cp -f "$BRAND/deskrudder-$f.png" "$SRC/res/" 2>/dev/null || true
  fi
done

# Cargo.toml — nome do pacote / bundle (Windows exe)
python3 - <<PY
from pathlib import Path
import re
p = Path("$SRC") / "Cargo.toml"
text = p.read_text(encoding="utf-8")
text2 = text
text2 = re.sub(r'(?m)^name = "rustdesk"', 'name = "deskrudder"', text2, count=1)
text2 = re.sub(r'(?m)^default-run = "rustdesk"', 'default-run = "deskrudder"', text2, count=1)
text2 = re.sub(
    r'(?m)^name = "RustDesk"',
    'name = "DeskRudder"',
    text2,
)
text2 = re.sub(
    r'(?m)^identifier = "[^"]+"',
    'identifier = "br.com.deskrudder.remote"',
    text2,
    count=1,
)
if text2 == text:
    print("AVISO: Cargo.toml — padrões não encontrados; revise manualmente.", flush=True)
else:
    p.write_text(text2, encoding="utf-8")
    print("Cargo.toml atualizado", flush=True)
PY

# libs/hbb_common — APP_NAME + servidor + chave
CFG_RS="$SRC/libs/hbb_common/src/config.rs"
if [[ ! -f "$CFG_RS" ]]; then
  echo "Não achei $CFG_RS — estrutura do upstream mudou?" >&2
  exit 1
fi

python3 - <<PY
from pathlib import Path
import re
p = Path("$CFG_RS")
text = p.read_text(encoding="utf-8")
orig = text

# APP_NAME
text = re.sub(
    r'Arc::new\(RwLock::new\("RustDesk"\.to_owned\(\)\)\)',
    'Arc::new(RwLock::new("DeskRudder".to_owned()))',
    text,
    count=1,
)
# RENDEZVOUS_SERVERS — várias formas no histórico do projeto
text = re.sub(
    r'pub const RENDEZVOUS_SERVERS:\s*&\[&str\]\s*=\s*&\[.*?\];',
    'pub const RENDEZVOUS_SERVERS: &[&str] = &["$HOST"];',
    text,
    count=1,
    flags=re.S,
)
text = re.sub(
    r'pub const RENDEZVOUS_SERVERS:\s*&\'static\s+\[&\'static\s+str\]\s*=\s*&\[.*?\];',
    'pub const RENDEZVOUS_SERVERS: &\'static [&\'static str] = &["$HOST"];',
    text,
    count=1,
    flags=re.S,
)
# RS_PUB_KEY
text = re.sub(
    r'pub const RS_PUB_KEY:\s*&str\s*=\s*"[^"]*";',
    'pub const RS_PUB_KEY: &str = "$KEY";',
    text,
    count=1,
)
text = re.sub(
    r'pub const RS_PUB_KEY:\s*&\'static\s+str\s*=\s*"[^"]*";',
    'pub const RS_PUB_KEY: &\'static str = "$KEY";',
    text,
    count=1,
)

if text == orig:
    print("AVISO: config.rs — revise RENDEZVOUS_SERVERS / RS_PUB_KEY / APP_NAME manualmente.", flush=True)
else:
    p.write_text(text, encoding="utf-8")
    print("config.rs atualizado", flush=True)
PY

echo ">> Pronto. No Windows (Git Bash), siga docs/RUSTDESK_CLIENT_WINDOWS.md para compilar."
echo "   Licença AGPL-3.0: publique o fork/diff se distribuir o .exe."
