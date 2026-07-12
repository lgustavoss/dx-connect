---
name: browser-qa
description: Executa smoke tests e validação visual do DX Connect no navegador integrado do Cursor. Use após subir ambiente local, antes de PR, ou quando o usuário reportar tela branca/erro na UI.
---

# Browser QA — DX Connect

Playbook para testes manuais assistidos via MCP `cursor-ide-browser`.

## Pré-check (terminal)

```bash
curl -s http://localhost:8000/health
curl -s -o NUL -w "%{http_code}" http://localhost:5173/
```

Se falhar → `/subir-local` primeiro.

## Problemas comuns

| Sintoma | Causa | Correção |
|---------|-------|----------|
| Tela preta | Vite 500 em `.tsx` | Ver network; `npm install`; reiniciar `npm run dev` |
| `Failed to resolve import "recharts"` | deps não instaladas | `cd frontend && npm install` |
| 401 após login | seed não rodou | `docker compose exec backend python -m app.seed` |
| API lenta no /health | IBGE sync no startup | Aguardar ~10s e retry |

## Rotas smoke

| Rota | Esperado |
|------|----------|
| `/login` | Form login |
| `/` ou `/dashboard` | Redirect se autenticado |
| `/tickets` | Lista tickets |
| `/chat-interno` | Inbox IC (se implementado) |

## Sequência login

1. `browser_navigate` → `/login`
2. `browser_snapshot` → refs dos campos
3. `browser_fill` e-mail e senha
4. `browser_click` botão entrar
5. `browser_console_messages` + `browser_network_requests`

## Critério de sucesso

- Zero erros críticos no console
- Nenhum script `.tsx` com status 500
- Login admin funciona
- Rota da feature renderiza conteúdo no snapshot

## Ferramentas MCP

- `browser_navigate`, `browser_snapshot`
- `browser_console_messages`, `browser_network_requests`
- `browser_take_screenshot` (evidência)
- `browser_fill`, `browser_click` (fluxos)

Command associado: `/testar-ui`
