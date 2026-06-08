#!/usr/bin/env bash
# Diagnóstico rápido do backend em produção (rodar no VPS).
set -euo pipefail

echo "=== Health local ==="
curl -s http://127.0.0.1:8000/health | python3 -m json.tool 2>/dev/null || curl -s http://127.0.0.1:8000/health || echo "(sem resposta)"

echo ""
echo "=== Health público (se configurado) ==="
if [ -n "${PUBLIC_API_URL:-}" ]; then
  curl -s "${PUBLIC_API_URL%/}/health" | python3 -m json.tool 2>/dev/null || true
else
  echo "Defina PUBLIC_API_URL=https://api... para testar URL pública"
fi

echo ""
echo "=== Porta 8000 ==="
ss -tlnp 2>/dev/null | grep ':8000 ' || echo "(nada escutando em 8000)"

echo ""
echo "=== Container dx-connect-api ==="
docker ps -a --filter name=dx-connect-api --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}' 2>/dev/null || echo "(docker indisponível)"
docker inspect -f 'StartedAt={{.State.StartedAt}} Image={{.Config.Image}}' dx-connect-api 2>/dev/null || true

echo ""
echo "=== Compose (cwd: $(pwd)) ==="
if [ -f docker-compose.prod.yml ]; then
  docker compose -f docker-compose.prod.yml ps backend 2>/dev/null || true
else
  echo "docker-compose.prod.yml não encontrado neste diretório"
fi
