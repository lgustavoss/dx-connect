# Testar UI

Execute **smoke test** da aplicação no navegador. Com MCP de navegador (ex.: `cursor-ide-browser` no Cursor), valide com snapshot/console/network. Sem MCP de navegador (caso do DSH hoje), valide por HTTP (`curl`) e peça as evidências visuais ao usuário.

## Quando usar

- Após `/subir-local` ou antes de abrir PR
- Validar feature implementada (ex.: chat interno IC)
- Investigar tela branca, erro no console ou 500 no Vite

## Pré-requisitos

1. Ambiente local no ar (`/subir-local` ou equivalente)
2. API: http://localhost:8000/health → 200
3. Frontend: http://localhost:5173 → 200
4. Se Vite foi iniciado **antes** de `npm install`, **reinicie** `npm run dev`

## Escopo do teste

Se o usuário passou rota ou feature, foque nela. Senão, rode o **smoke padrão** abaixo.

## Fluxo

Com MCP de navegador: `browser_navigate` → `browser_snapshot` → `browser_console_messages` → `browser_network_requests`.

Sem MCP de navegador: use `curl -s -o NUL -w "%{http_code}" <url>` por rota e inspecione os logs do Vite/backend.

### 1 — Smoke inicial

```
GET http://localhost:5173/
```

Verificar:
- [ ] Página carrega (não fica preta/vazia)
- [ ] Console **sem** erros `Failed to resolve import`
- [ ] Network: scripts principais com status 200 (não 500 em `.tsx`)

Se tela preta: inspecionar network por arquivos com **500** (ex.: `DashboardTickets.tsx` → `recharts` faltando → `cd frontend && npm install` e reiniciar Vite).

### 2 — Login admin

Navegar: http://localhost:5173/login

Credenciais dev:
- E-mail: `admin@email.com`
- Senha: `admin123`

- [ ] Formulário visível
- [ ] Login redireciona para dashboard/home
- [ ] Sem erro 401/403 inesperado na network (`/api/v1/auth/login`)

Com MCP: `browser_fill` + `browser_click` ou interação por refs do snapshot. Sem MCP: valide `POST /api/v1/auth/login` por `curl` e confirme o redirecionamento descrito pelo usuário.

### 3 — Navegação mínima pós-login

- [ ] Sidebar/menu carrega
- [ ] Abrir **Tickets** (ou rota indicada pelo usuário)
- [ ] Página renderiza sem erro no console

### 4 — Feature sob teste (se informada)

Exemplos:

| Feature | Rota |
|---------|------|
| Chat interno IC | `/chat-interno` |
| Dashboard | `/dashboard` |
| WhatsApp | `/whatsapp` |

Checklist:
- [ ] Rota abre sem 404/403 indevido
- [ ] Elementos principais visíveis no snapshot
- [ ] Chamadas API relevantes retornam 2xx (network)

### 5 — Screenshot e relatório

Com MCP, tire `browser_take_screenshot` em caso de falha. Sem MCP, registre status HTTP e trechos de erro.

Entregue:

```markdown
## Resultado UI

| Etapa | Status | Observação |
|-------|--------|------------|
| Smoke / | ✅/❌ | ... |
| Login | ✅/❌ | ... |
| Navegação | ✅/❌ | ... |
| Feature X | ✅/❌ | ... |

## Erros de console
- ...

## Requests com falha
- ...

## Correção sugerida
- ...
```

## Se encontrar bug

1. Corrija **se estiver no escopo** da sessão (ex.: deps faltando, erro óbvio)
2. Reexecute o teste afetado
3. Não commitar sem pedido do usuário

## Subagent

Para testes longos em paralelo com implementação, pode delegar exploração de rotas ao subagent `explore` — mas **interação no browser** faça neste agent (MCP browser não é delegável de forma confiável).

## Referências

- `/subir-local` — subir ambiente
- Login dev: `README.md`
- Credenciais só local — nunca produção
