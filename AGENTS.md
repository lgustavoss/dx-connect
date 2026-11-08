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
| `pt-br` | Sempre — português do Brasil (você; UI, chat, Expo, CHANGELOG, MCP) |
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
| `/testar-ui` | Smoke test no navegador (login, rotas, console); sem MCP de navegador, valida por HTTP |
| `/criar-pr` | PR → watch CI → approve → **merge automático em main** (nunca staging) |
| `/release-staging` | Abre PR `main → staging` (não mergeia); após deploy, sync CHANGELOG na `main` (Passo 5) |
| `/listar-solicitacoes` | Fila SaaS pendente no chat (MCP `deskrudder-saas`; cada dev configura o próprio `mcp.json`) |
| `/proximos-passos` | Analisa fila SaaS + issues abertas + estado do repo e recomenda o próximo lote (skill `analisar-backlog`) |

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
0. /proximos-passos                    → qual lote agora (fila SaaS + issues)
1. /planejar-feature #322
2. revisar plano (RBAC, SSE, migrations) — decisões → comentário na issue
3. /iniciar-feature                    → branch feat/...
4. /implementar-issue #336-340         → lote
5. /revisar-e-testar
6. /criar-pr                           → PR + CI + approve + merge em main
```

O `/criar-pr` monitora Actions, aprova e **mergeia em `main`** quando CI passa (main = branch de testes). Em falha, corrige e re-monitora (skill **babysit**). Opt-out: pedir `/criar-pr sem merge`.

Release para produção: `/release-staging` — abre PR `main → staging` (merge manual no GitHub); depois do Deploy, **Passo 5** alinha CHANGELOG na `main`.

Para desenvolvimento local: `/subir-local` → `/testar-ui` (navegador; sem MCP, por HTTP).

## Skills

| Skill | Quando |
|-------|--------|
| `design-feature` | Planejar épicos/features (usado por `/planejar-feature`) |
| `deploy-cliente` | Deploy/atualização de instância por cliente |
| `browser-qa` | Smoke tests no navegador (`/testar-ui`) |
| `analisar-backlog` | Priorizar o próximo lote: fila SaaS × issues × estado do repo (usado por `/proximos-passos`) |

Skills futuras sugeridas:

- `alembic-recovery` — troubleshooting de heads/revisions

## Pastas que o agente não deve varrer

`node_modules`, `.git`, `dist`, `release`, `.venv`, `__pycache__`, extensões do editor e logs de sessão **não** devem ser varridos com `glob`/`grep`/`read` nem com `dir /s` / `grep -r` — o `package.json`/lockfile já descrevem o que está instalado. Ao buscar, escopar em `backend/`, `frontend/src`, `scripts/`, `deploy/` e usar `include` para restringir extensão.

- Regra pessoal completa (DSH, vale para todos os workspaces desta máquina): `%USERPROFILE%\.dsh\AGENTS.md`
- Segredos: não ler `.env`, `.cursor/mcp.json` ou credenciais sem pedido explícito.

## DeepSeek Harness (DSH)

Além do Cursor, o time pode trabalhar no DSH. O DSH carrega skills do workspace em `.dsh/skills/` e as expõe como `/nome` no chat — mesmo fluxo dos commands do Cursor.

| Item | Onde |
|------|------|
| Fonte única dos comandos/skills | `.cursor/commands/*.md`, `.cursor/skills/*/SKILL.md` |
| Skills versionadas para o DSH | `.dsh/skills/` — espelho das skills do projeto; a fonte é o `.cursor/` (não editar à mão) |
| MCP | `deskrudder-saas` e `hostinger-vps` no profile do DSH (fora do repo, com tokens) |
| Rules | continuam em `.cursor/rules/*.mdc` — leia a rule relevante no contexto (RBAC, SSE, migrations, git, release) |
| Hooks | não portados (bloqueio de `main`/`staging` e ESLint `--fix` não rodam no DSH) |

## Docs de referência

- `docs/BACKEND_RBAC.md`
- `docs/REALTIME_SSE.md`
- `docs/ALEMBIC_MIGRATIONS.md`
- `docs/DEPLOYMENT_ARCHITECTURE.md`
- Issues e decisões de produto no **GitHub**
- Índice opcional: `.github/planning-issue-bodies/ISSUES_CRIADAS.md`
