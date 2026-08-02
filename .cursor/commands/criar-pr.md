# Criar PR

Finalize a feature, abra Pull Request para **`main`**, acompanhe o CI, aprove e **faça merge automático** quando estiver verde.

> **`main` é branch de testes** neste repo — após CI verde, merge automático é o comportamento padrão do `/criar-pr`.
> Para **só abrir PR sem merge**, o usuário deve pedir explicitamente: `/criar-pr sem merge`.
>
> **Este comando NÃO serve para `staging`.** Release para produção = `/release-staging` (abre PR `main → staging` e **para**; o utilizador mergeia no GitHub). **Nunca** `gh pr merge` com base `staging`.

## Pré-requisitos

- Feature implementada e revisada (`/revisar-e-testar` recomendado)
- Branch **não** é `main` nem `staging`
- Base do PR será **`main`** (nunca `staging`)
- Testes passando localmente
- `gh` autenticado (`gh auth status`)

## Passo 1 — Diagnóstico Git

Execute em paralelo:

```bash
git status
git diff
git diff --staged
git branch --show-current
git log origin/main..HEAD --oneline
git status -sb
```

Se estiver em `main` ou `staging`, **pare** — oriente `/iniciar-feature`.

Use **`origin/main`** como base de comparação (não `main` local desatualizado).

## Passo 2 — Commit (se necessário)

Se houver alterações não commitadas:

1. Analise o diff completo
2. **Não** incluir `.env`, credenciais ou arquivos fora do escopo da feature
3. Mensagem no estilo do repo: `feat(escopo): descrição concisa`
4. Commit com HEREDOC (PowerShell: here-string)

## Passo 3 — Push

```bash
git push -u origin HEAD
```

## Passo 4 — Criar ou reutilizar PR

Verifique se já existe PR aberto para a branch:

```bash
gh pr view --json number,url,state 2>/dev/null
```

- **Se existir** → use esse PR (não crie duplicado)
- **Se não existir** → crie com base **`main`**

### Criar PR

Preferir `--body-file` (evita problemas no PowerShell):

1. Escreva o corpo em arquivo temporário (ex.: `.cursor/pr-body-temp.md`)
2. Siga `.github/pull_request_template.md` (Summary, CHANGELOG, Test plan, Follow-ups)
3. Para mudanças internas/tooling: marque CHANGELOG como N/A

```bash
gh pr create --base main --title "título descritivo" --body-file .cursor/pr-body-temp.md
```

Apague o arquivo temporário após criar o PR.

Capture: `PR_NUMBER`, `PR_URL`.

## Passo 5 — Acompanhar CI (obrigatório)

Workflow esperado: **`CI`** (jobs: `changelog`, `backend`, `frontend`).

### Monitorar até concluir

```bash
gh pr checks --watch --interval 15
```

Alternativa:

```bash
gh run list --branch $(git branch --show-current) --limit 1 --json databaseId --jq '.[0].databaseId'
gh run watch <RUN_ID> --exit-status
```

### Status final

```bash
gh pr checks
gh pr view --json state,mergeable,reviewDecision,statusCheckRollup,url
```

**Não abandone** enquanto houver checks `pending`/`in_progress`.

## Passo 6 — Se CI falhou → corrigir e re-monitorar

Entre em loop (skill **babysit**):

1. Identifique job que falhou (`gh pr checks`, `gh run view --log-failed`)
2. Corrija **somente** o escopo deste PR — não altere workflows de CI para “passar no gato”
3. Commit + push na mesma branch
4. Volte ao **Passo 5**
5. Repita até verde ou bloqueio real

Se a branch estiver atrasada:

```bash
git fetch origin
git merge origin/main
# resolver conflitos, push, re-monitorar CI
```

## Passo 7 — CI verde → aprovar e mergear (padrão)

Quando **todos** os checks estiverem `pass`/`SUCCESS`:

### 7a — Aprovar (best-effort)

```bash
gh pr review --approve --body "CI verde. Aprovado via /criar-pr."
```

Se self-approval for bloqueada, **continue** — muitos repos permitem merge sem approval próprio.

### 7b — Merge automático em main

```bash
gh pr merge --merge --delete-branch
```

Se falhar por branch protection (ex.: review obrigatório de terceiro):
- Reporte PR verde mas **não mergeado**
- Indique quem precisa aprovar ou ajustar protection rules

### 7c — Confirmar merge

```bash
gh pr view --json state,mergedAt,mergeCommit,url
```

Estado esperado: `MERGED`.

### 7d — Atualizar local (opcional)

```bash
git fetch origin
git checkout main
git pull origin main
```

## Passo 8 — Entrega final

Reporte:

| Item | Valor |
|------|-------|
| URL do PR | ... |
| Branch → main | ... |
| CI | ✅ verde / ❌ falhou |
| Aprovação | ✅ / ⏳ bloqueada |
| Merge | ✅ merged / ❌ pendente |
| Commit em main | SHA do merge (se merged) |

## Opt-out: sem merge

Se o usuário pediu **"sem merge"** ou PR é excepcionalmente sensível:
- Pare após Passo 7a (aprovar)
- **Não** execute `gh pr merge`

## Resumo do fluxo

```
commit/push → PR → watch CI → verde? → approve → merge → confirmar
                    ↓ falhou
               fix + push → watch CI (loop)
```
