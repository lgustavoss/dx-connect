# Agentes — DX Connect

Guia para desenvolvimento assistido por IA no Cursor (time 2–3 devs).

## Estrutura `.cursor/`

| Pasta | Função |
|-------|--------|
| `rules/` | Padrões automáticos por contexto (sempre ativos ou por glob) |
| `commands/` | Workflows invocáveis com `/` no chat |
| `skills/` | Playbooks profundos (criar conforme necessidade) |
| `hooks/` | Automação em eventos do agente |

## Rules ativas

| Rule | Quando |
|------|--------|
| `project-core` | Sempre |
| `pt-br` | Sempre — português do Brasil (UI, chat, MCP, mensagem ao cliente) |
| `planning-github-source` | Sempre — planos/decisões no GitHub, sem `.md` locais de rascunho |
| `backend-fastapi` | Arquivos em `backend/**` |
| `frontend-react` | Arquivos em `frontend/**` |
| `rbac-setor-scope` | `backend/app/api/**`, `backend/app/core/**` |
| `alembic-migrations` | `backend/alembic/**` |
| `git-workflow` | Sempre — branch por feature, PR para `main` |
| `staging-release-approval` | Sempre — staging = produção; merge só humano |
| `sse-realtime` | Arquivos SSE/realtime (backend + frontend) |

## Hooks

| Hook | Evento | Função |
|------|--------|--------|
| `block_main_branch.py` | `beforeShellExecution` (`git` / `gh`) | Bloqueia commit/push em `main`/`staging` e **`gh pr merge` com base staging** |
| `format_frontend.py` | `afterFileEdit` | ESLint `--fix` em `.ts/.tsx` do frontend |

Config: `.cursor/hooks.json`

## Commands do dia a dia

| Comando | Uso |
|---------|-----|
| `/planejar-feature` | Planejar feature antes de codar (escopo, RBAC, ordem) |
| `/iniciar-feature` | Criar branch a partir de `main` atualizada |
| `/implementar-issue` | Implementar issue/épico com checklist completo |
| `/nova-migration` | Criar/validar migration Alembic |
| `/revisar-e-testar` | Revisão pré-merge com testes |
| `/subir-local` | Subir Docker, migrations, API e frontend em dev |
| `/testar-ui` | Smoke test no navegador integrado (login, rotas, console) |
| `/criar-pr` | PR → watch CI → approve → **merge automático em main** (nunca staging) |
| `/release-staging` | Abre PR `main → staging`; **não mergeia** (aprovação humana) |
| `/listar-solicitacoes` | Fila SaaS pendente no chat (MCP `deskrudder-saas`; cada dev configura o próprio `mcp.json`) |

## Subagents (Task tool)

Use subagents para **paralelizar** ou **isolar** trabalho:

| Tipo | Quando usar |
|------|-------------|
| `explore` | Mapear código, achar padrões, responder "onde fica X?" |
| `shell` | Git, docker, pytest, deploy scripts |
| `generalPurpose` | Tarefas multi-etapa que não cabem num grep |
| `best-of-n-runner` | Experimentos isolados em worktree |

**Evite** subagent para edits simples em 1–2 arquivos — faça direto.

### Padrão recomendado por feature

```
1. /planejar-feature #322
2. revisar plano (RBAC, SSE, migrations) — decisões → comentário na issue
3. /iniciar-feature                    → branch feat/...
4. /implementar-issue #336-340         → lote
5. /revisar-e-testar
6. /criar-pr                           → PR + CI + approve + merge em main
```

O `/criar-pr` monitora Actions, aprova e **mergeia em `main`** quando CI passa (main = branch de testes). Em falha, corrige e re-monitora (skill **babysit**). Opt-out: pedir `/criar-pr sem merge`.

Release para produção: `/release-staging` — **só abre** o PR; merge em `staging` é **sempre** manual no GitHub.

Para desenvolvimento local: `/subir-local` → `/testar-ui` (navegador integrado).

## Skills

| Skill | Quando |
|-------|--------|
| `design-feature` | Planejar épicos/features (usado por `/planejar-feature`) |
| `deploy-cliente` | Deploy/atualização de instância por cliente |
| `browser-qa` | Smoke tests no navegador integrado (`/testar-ui`) |

Skills futuras sugeridas:

- `alembic-recovery` — troubleshooting de heads/revisions

## Docs de referência

- `docs/BACKEND_RBAC.md`
- `docs/REALTIME_SSE.md`
- `docs/ALEMBIC_MIGRATIONS.md`
- `docs/DEPLOYMENT_ARCHITECTURE.md`
- Issues e decisões de produto no **GitHub**
- Índice opcional: `.github/planning-issue-bodies/ISSUES_CRIADAS.md`
