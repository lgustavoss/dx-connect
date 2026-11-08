---
name: release-staging
description: "Abre o PR main → staging para o humano mergear (nunca mergeia staging) e, após o deploy, alinha o CHANGELOG na main. staging = produção."
whenToUse: "Quando o usuário pedir /release-staging, release para produção, promover main para staging ou sincronizar o CHANGELOG pós-deploy."
---

# /release-staging — release para produção (humano mergeia)

Este skill é o comando `/release-staging` do DX Connect. O playbook completo está
em `.cursor/commands/release-staging.md` — **leia antes de começar**; se divergir
deste resumo, o playbook vence.

## Regra de ferro

`staging` = **produção**.

- **Só abrir o PR quando o usuário executar `/release-staging` explicitamente.**
  Nunca proativamente — nem com “prepare o release”, “release hoje à noite” ou
  “deixa pronto”. Se abrir por engano, **fechar sem merge** e avisar.
- Antes de abrir, checar: (a) o time validou a `main` (smoke, não só suíte);
  (b) `gh pr list --state open` e `git branch -r --no-merged origin/main` —
  outra entrega pode entrar no mesmo lote; se houver, avisar e aguardar.
- **NUNCA** `gh pr merge` com base `staging` — nem com CI verde, nem "para
  facilitar".
- **NUNCA** push direto para `staging`.
- O agente abre o PR `main → staging` e **para**, entregando a URL.
- Exceção permitida: o PR de **sync `staging → main`** (Passo 5) pode ser
  mergeado automaticamente após CI verde, como em `/criar-pr`.

## Passos

1. **Diagnóstico**: `git fetch origin`,
   `git log origin/staging..origin/main --oneline`,
   `gh pr list --base staging --head main --state open`. Se já houver PR aberto,
   reutilize.
2. **O merge esvazia o `[Unreleased]`?** O CI simula o merge-tree da head na
   `staging`. Rode `python scripts/check_changelog.py --base origin/staging --head origin/main`:
   - `OK` → PR direto `main → staging` (3a).
   - Erro de merge → branch `merge/main-into-staging-YYYYMMDD` a partir de
     `origin/staging`, `git merge origin/main`, rode o script com
     `--write-changelog`, commite o CHANGELOG e abra o PR a partir dela (3b).
3. **PR**: `gh pr create --base staging --head <branch> --title "release: main → staging" --body-file <temp>`
   com Summary do lote + test plan. Corpo sóbrio, sem avisos sobre quem mergeia.
4. **Entrega (pré-merge)**: URL do PR. **Pare aqui.**
5. **Pós-merge (só quando o usuário confirmar merge e o Deploy em `staging`
   estiver verde)**: branch `chore/sync-changelog-YYYYMMDD` a partir da `main`,
   `git merge origin/staging`, rodar `python scripts/sync_changelog_from_staging.py`,
   commitar e abrir PR → `main` (esse pode ser mergeado automaticamente após CI
   verde). Entrega: versão publicada, URL do PR de sync e `[Unreleased]` limpo.

## Notas deste ambiente (Windows + DSH, já verificadas)

- **Não existe Python no host** (`python` = atalho da Store; `py` não existe) e a
  imagem do backend não tem `git`, então `scripts/check_changelog.py` e
  `scripts/sync_changelog_from_staging.py` **não rodam localmente**. Deixe o job
  `changelog` do CI validar o PR; se ele falhar, corrija o `CHANGELOG.md` e
  re-push.
- `gh` autenticado (`lgustavoss`). Self-approve de PR próprio falha — para o PR
  de release isso é irrelevante (merge é humano).
- Use `--body-file` com arquivo temporário e apague depois.
- Antes de abrir o release, confirme que a `main` já passou pelo `/criar-pr` e
  que o CHANGELOG descreve o lote.
