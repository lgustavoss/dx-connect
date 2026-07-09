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
| `backend-fastapi` | Arquivos em `backend/**` |
| `frontend-react` | Arquivos em `frontend/**` |
| `rbac-setor-scope` | `backend/app/api/**`, `backend/app/core/**` |
| `alembic-migrations` | `backend/alembic/**` |
| `git-workflow` | Sempre — branch por feature, PR para `main` |
| `sse-realtime` | Arquivos SSE/realtime (backend + frontend) |

## Hooks

| Hook | Evento | Função |
|------|--------|--------|
| `block_main_branch.py` | `beforeShellExecution` | Bloqueia commit/push em `main`/`staging` |
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
| `/criar-pr` | Commit, push e abrir PR para `main` |

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
1. /planejar-feature @IC-02-backend-api-chat-interno.md
2. revisar plano (RBAC, SSE, migrations)
3. /iniciar-feature                    → branch feat/chat-interno-api-ic02
4. /implementar-issue @IC-02-backend-api-chat-interno.md
5. /revisar-e-testar
6. /criar-pr                           → PR para main
```

## Skills

| Skill | Quando |
|-------|--------|
| `design-feature` | Planejar épicos/features (usado por `/planejar-feature`) |
| `deploy-cliente` | Deploy/atualização de instância por cliente |

Skills futuras sugeridas:

- `alembic-recovery` — troubleshooting de heads/revisions

## Docs de referência

- `docs/BACKEND_RBAC.md`
- `docs/REALTIME_SSE.md`
- `docs/ALEMBIC_MIGRATIONS.md`
- `docs/DEPLOYMENT_ARCHITECTURE.md`
- `.github/planning-issue-bodies/`
