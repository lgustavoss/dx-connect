#!/usr/bin/env bash
# Alinha o 302 /acesso-remoto/download para o DeskRemote Cliente v2.
# Idempotente. Não falha o deploy se faltar sudo ou Nginx.
set -u

OLD='acesso-remoto-windows/DeskRudder-AcessoRemoto.exe'
NEW='acesso-remoto-windows-flutter/DeskRudder-AcessoRemoto-Flutter.exe'

atualizar() {
  local f="$1"
  grep -qF "$OLD" "$f" 2>/dev/null || return 2
  if [ -w "$f" ]; then
    sed -i "s|${OLD}|${NEW}|g" "$f"
  elif sudo -n sed -i "s|${OLD}|${NEW}|g" "$f" 2>/dev/null; then
    :
  else
    echo "::warning::Sem permissão para atualizar $f (DeskRemote v2 no Nginx)."
    return 1
  fi
  echo "Nginx DeskRemote v2: $f"
  return 0
}

n=0
for dir in /etc/nginx/sites-enabled /etc/nginx/sites-available /etc/nginx/conf.d; do
  [ -d "$dir" ] || continue
  shopt -s nullglob
  for f in "$dir"/*; do
    [ -f "$f" ] || continue
    if atualizar "$f"; then
      n=$((n + 1))
    fi
  done
  shopt -u nullglob
done

if [ "$n" -eq 0 ]; then
  echo "Nginx DeskRemote v2: nenhum 302 Sciter encontrado (já alinhado ou site sem a location)."
  exit 0
fi

if command -v nginx >/dev/null 2>&1; then
  if sudo -n nginx -t 2>/dev/null; then
    sudo -n systemctl reload nginx 2>/dev/null \
      || sudo -n service nginx reload 2>/dev/null \
      || echo "::warning::Nginx atualizado nos arquivos, mas o reload falhou — rode nginx -t && reload no VPS."
  else
    echo "::warning::nginx -t falhou ou sem sudo; confira o 302 do DeskRemote v2 no VPS."
  fi
fi
