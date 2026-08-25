# Release staging

Abre Pull Request **`main` → `staging`** para o utilizador **analisar e aprovar no GitHub**.

> **`staging` = produção.** O agente **NUNCA** faz `gh pr merge` neste fluxo — nem com CI verde, nem “para facilitar”.

## Pré-requisitos

- Lote testado na `main`
- `CHANGELOG.md` → `[Unreleased]` com o lote a publicar
- `gh` autenticado

## Passo 1 — Diagnóstico

```bash
git fetch origin
git log origin/staging..origin/main --oneline
gh pr list --base staging --head main --state open
```

Se já existir PR aberto `main` → `staging`, **reutilize** (não duplique).

## Passo 2 — Conflitos?

Se `gh pr create` / GitHub indicar conflito:

1. Branch a partir de `origin/staging`: `merge/main-into-staging-YYYYMMDD`
2. `git merge origin/main` e resolver (código da `main`; `[Unreleased]` = só o que ainda não foi publicado na staging)
3. Push da branch e **um** PR → `staging`
4. **Pare** — entregue o URL; **não** mergeie

Não manter dois PRs de release abertos sem explicar; preferir **um** PR mergeável.

## Passo 3 — Criar PR (sem merge)

```bash
gh pr create --base staging --head main --title "release: main → staging" --body-file .cursor/pr-body-temp.md
```

Corpo do PR: Summary do lote (`[Unreleased]`) + test plan. **Sem** avisos sobre quem aprova/mergeia (isso é óbvio e irrelevante no GitHub).

## Passo 4 — Entrega

No chat: URL do PR (base `staging`). Sem sermão sobre “merge só no GitHub”.

**Não** executar: `gh pr merge`, push para `staging`.
