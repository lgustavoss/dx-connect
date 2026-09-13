# Release staging

Abre Pull Request **`main` → `staging`** para o usuário **analisar e aprovar no GitHub**. Após merge e deploy, **sincroniza o CHANGELOG na `main`** (higiene pós-release).

> **`staging` = produção.** O agente **NUNCA** faz `gh pr merge` no PR **`main → staging`** — nem com CI verde, nem “para facilitar”. O PR de sync **`→ main`** (Passo 5) **pode** ser mergeado automaticamente como em `/criar-pr`.

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

## Passo 2 — Conflitos no GitHub?

O CI **não** simula `git merge` do repositório (isso falhava em todo release: o deploy esvazia `[Unreleased]` na staging). Ele compõe `[Unreleased]` da head + histórico da base.

O GitHub ainda pode marcar conflito em `CHANGELOG.md` neste PR se o Passo 5 do release **anterior** foi só cópia de arquivos (sem merge `staging → main`). Nesse caso:

1. Branch a partir de `origin/staging`: `merge/main-into-staging-YYYYMMDD`
2. `git merge origin/main` e resolver (**obrigatório:** manter bullets de `[Unreleased]` da `main` — não aceitar `[Unreleased]` vazio da `staging`)
3. Validar localmente: `python scripts/check_changelog.py --base origin/staging --head HEAD`
4. Push da branch e **um** PR → `staging`
5. **Pare** — entregue o URL; **não** mergeie

Depois de **um** Passo 5 com `git merge origin/staging` na `main`, o próximo `main → staging` tende a auto-mergear o CHANGELOG (merge-base já tem `[Unreleased]` vazio).

Não manter dois PRs de release abertos sem explicar; preferir **um** PR mergeável.

### Checklist CHANGELOG antes do merge release

```bash
git fetch origin
python scripts/check_changelog.py --base origin/staging --head origin/main
```

Deve imprimir `OK` com bullets (Unreleased da head). Se a head tiver `[Unreleased]` vazio, não mergeie.

## Passo 3 — Criar PR (sem merge)

```bash
gh pr create --base staging --head main --title "release: main → staging" --body-file .cursor/pr-body-temp.md
```

Corpo do PR: Summary do lote (`[Unreleased]`) + test plan. **Sem** avisos sobre quem aprova/mergeia (isso é óbvio e irrelevante no GitHub).

## Passo 4 — Entrega (pré-merge)

No chat: URL do PR (base `staging`). Sem sermão sobre “merge só no GitHub”.

**Não** executar: `gh pr merge` (base `staging`), push para `staging`.

---

## Passo 5 — Higiene do CHANGELOG na `main` (pós-merge)

**Quando:** o usuário confirmou merge do release **ou** o PR `main → staging` está `MERGED`, e o workflow **Deploy** em `staging` concluiu com sucesso (inclui o commit `chore(release): publica v… [skip ci]`).

**Por quê:** o deploy consome `[Unreleased]` só na `staging`. A `main` continua com bullets já publicados até este passo — isso confunde o próximo lote e o `/release-staging` seguinte.

### 5.1 — Verificar

```bash
git fetch origin
gh pr view <número-do-release> --json state,mergedAt
gh run list --branch staging --workflow deploy.yml --limit 5
```

Só prossiga com Deploy **verde** no commit de release. Se ainda estiver rodando, monitore (`gh run watch`) e retome depois.

### 5.2 — Branch de sync

```bash
git checkout main
git pull origin main
git checkout -b chore/sync-changelog-YYYYMMDD
```

### 5.3 — Merge `staging` na branch de sync (obrigatório)

Não copiar só os arquivos. O **merge** atualiza o merge-base: o próximo `main → staging` deixa de conflitar no `CHANGELOG.md`.

Arquivos que o deploy finaliza na `staging`:

- `CHANGELOG.md` (nova seção CalVer + `[Unreleased]` vazio)
- `VERSION`
- `docs/releases/manifest.json`
- `backend/app/data/release_notes.json`
- `frontend/public/release-notes.json`

```bash
git merge origin/staging --no-edit
python scripts/sync_changelog_from_staging.py
```

O script deve rodar **sempre** (mesmo sem conflito): tira da `[Unreleased]` o que o deploy acabou de publicar.

Se o Git parou com conflito:

```bash
git checkout --theirs VERSION docs/releases/manifest.json \
  backend/app/data/release_notes.json frontend/public/release-notes.json
git add CHANGELOG.md VERSION docs/releases/manifest.json \
  backend/app/data/release_notes.json frontend/public/release-notes.json
git commit --no-edit
```

Se o merge concluiu e o script alterou o CHANGELOG:

```bash
git add CHANGELOG.md
git commit -m "chore(release): alinha CHANGELOG da main com vXX.XX.XXX publicada"
```

Não duplicar bullets que já entraram na seção versionada do release.

### 5.4 — PR → `main`

```bash
git push -u origin HEAD
gh pr create --base main --title "chore(release): sync CHANGELOG pós vXX.XX.XXX" --body "$(cat <<'EOF'
## Summary

- Mergeia `staging` na `main` (atualiza merge-base) e alinha `CHANGELOG.md`, `VERSION` e artefatos de release notes com o deploy.
- `[Unreleased]` na `main` fica só com o que ainda não foi para produção.

## Test plan

- [ ] `## [Unreleased]` sem bullets já publicados na CalVer do release
- [ ] Nova seção `## [XX.XX.XXX]` espelha a `staging`
- [ ] Se havia delta `staging..main`, bullets novos permanecem em `[Unreleased]`

EOF
)"
```

Merge automático em `main` **permitido** quando CI verde (mesmo fluxo de `/criar-pr`).

### 5.5 — Entrega final

No chat: versão publicada (`VERSION`), URL do PR de sync (se aberto) e confirmação de que `[Unreleased]` na `main` reflete só o próximo lote.

**Opcional no mesmo turno** (se o usuário pediu): fechar issues do release, atualizar painel SaaS (#S… → Concluída com versão) — ver `/listar-solicitacoes`.
