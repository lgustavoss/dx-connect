# `.dsh` — DeepSeek Harness (DSH)

Equivalente DSH do `.cursor/`: mesmo fluxo de **skills e comandos** disponível no chat.

## Como usar (chat do DSH)

Digite `/` no compositor e escolha, ou digite direto:

| Comando | Ação |
|---|---|
| `/planejar-feature #322` | Planejar feature/épico antes de codar |
| `/iniciar-feature` | Criar branch a partir de `main` atualizada |
| `/implementar-issue #336-340` | Implementar issue/épico |
| `/nova-migration` | Criar/validar migration Alembic |
| `/revisar-e-testar` | Revisão pré-merge com testes |
| `/subir-local` | Subir Docker, migrations, API e frontend |
| `/testar-ui` | Smoke test da UI |
| `/criar-pr` | PR → CI → merge em `main` (só humano) |
| `/release-staging` | PR `main → staging` (só humano) |
| `/listar-solicitacoes` | Fila SaaS pendente via MCP `deskrudder-saas` |
| `/proximos-passos` | Fila + issues abertas → próximo lote recomendado |

Além dos comandos, quatro skills ficam disponíveis para o modelo carregar sozinho: `design-feature`, `deploy-cliente`, `browser-qa` e `analisar-backlog`.

## Como funciona

O DSH carrega skills do workspace automaticamente: `<raiz-do-repo>/.dsh/skills/` é um root padrão do provider de skills. Um arquivo com frontmatter válido (`name` + `description`) vira:

- entrada no **catálogo do modelo** (se `disable-model-invocation` não for `true`), carregada pela tool `skill`; e
- comando **`/nome`** para o humano, que injeta o corpo como instruções no passo (o equivalente ao `/comando` do Cursor).

Não há plugin, instalação ou reinício: o provider observa a pasta.

## Fonte única e geração

- **Fonte:** `.cursor/commands/*.md` e `.cursor/skills/*/SKILL.md` (usadas pelo Cursor).
- **Gerado:** `.dsh/skills/` — **não edite à mão**.

Depois de mudar algo no `.cursor/`:

```bash
node .dsh/sync-skills.mjs
```

O script adiciona o frontmatter, mantém `criar-pr` e `release-staging` como **só humano** (`disable-model-invocation: true`, porque fazem merge/PR) e remove o que saiu da fonte. Mudanças são pegas pelo watcher do DSH sem restart.

## MCP

`deskrudder-saas` e `hostinger-vps` estão configurados no **profile do DSH**, fora do repositório (com tokens), nos bundles `@local/deskrudder-saas-mcp` e `@local/hostinger-vps-mcp`. As ferramentas aparecem como `mcp__deskrudder-saas__*` e `mcp__hostinger-vps__*`.

O bundle do DeskRudder fica em `%LOCALAPPDATA%\deskrudder-mcp\deskrudder-saas-mcp` e **executa o script versionado no repo** (`backend/scripts/mcp_deskrudder_saas.py`) com o Python do Windows (`%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe` — caminho fixo: o shim `python` do WindowsApps é o Python Install Manager e pode imprimir no stdout, o que quebra o protocolo stdio).

Se **mover o repositório** ou **trocar a versão do Python**, ajuste `command`/`args` no `cordis.patch.yml` do bundle. O bundle precisa constar em `dsh.profile.bundles` no `package.json` do profile; mudanças no profile valem na próxima sessão do DSH.

Se as ferramentas `mcp__deskrudder-saas__*` não aparecerem:

1. `dsh.profile.bundles` em `%USERPROFILE%\.dsh\profiles\desktop\package.json` inclui `@local/deskrudder-saas-mcp`?
2. O alvo do junction `node_modules\@local\deskrudder-saas-mcp` existe no disco?
3. `cordis.patch.yml` do bundle tem `command`/`args` apontando para o Python e o script do repo (caminhos absolutos)?
4. Reinicie o DSH (MCP é iniciado na sessão, não pelo watcher de skills).

## O que não foi portado

- **Rules** (`.cursor/rules/*.mdc`): o DSH lê `AGENTS.md`; as rules continuam sendo a referência e devem ser lidas no contexto certo (RBAC, SSE, migrations, git, release).
- **Hooks** (`.cursor/hooks/*.py`): sem equivalente automático no DSH hoje (bloqueio de commit em `main`/`staging` e ESLint `--fix` não rodam aqui).
- **Browser MCP**: o Cursor tem `cursor-ide-browser`; no DSH, `browser-qa`/`/testar-ui` caem para validação por HTTP (`curl`) + evidências do usuário até configurarmos um MCP de navegador (ex.: Playwright).
