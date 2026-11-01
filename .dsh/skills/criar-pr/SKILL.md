---
name: criar-pr
description: "Finaliza a feature, abre Pull Request para main, acompanha o CI, aprova e faz merge automático em main. Nunca usa staging como base."
whenToUse: "Quando o usuário pedir /criar-pr, abrir o PR, fechar a feature ou mergear em main."
---

# /criar-pr — PR para `main` + CI + merge automático

Este skill é o comando `/criar-pr` do DX Connect. O playbook completo é
`.cursor/commands/criar-pr.md` — **leia-o antes de começar** e siga os passos; se
ele divergir deste resumo, o playbook vence.

## Regras que não se negociam

- `main` é branch de **testes**: merge automático após CI verde é o padrão.
- A base do PR é **sempre `main`**. **Nunca** `staging` — staging é produção e só
  o humano mergeia (`/release-staging`).
- Nunca commitar `.env`, credenciais ou arquivos fora do escopo.
- Se a branch atual for `main` ou `staging`, pare e oriente `/iniciar-feature`.
- Se o CI falhar, corrija **só o escopo do PR**. Não altere workflows de CI para
  "passar no gato".
- Não abandonar enquanto houver check `pending`/`in_progress`.

## Passos

1. **Diagnóstico**: `git status`, `git diff`, `git diff --staged`,
   `git branch --show-current`, `git log origin/main..HEAD --oneline`. Use
   `origin/main` como base (não a `main` local).
2. **Commit** (se houver working tree): mensagem no estilo
   `tipo(escopo): descrição`, em pt-BR, com HEREDOC. Não incluir `.env`.
3. **Push**: `git push -u origin HEAD`.
4. **PR**: reutilize se já existir (`gh pr view --json number,url,state`). Se não,
   monte o corpo em arquivo temporário seguindo
   `.github/pull_request_template.md` (Summary, CHANGELOG, Test plan,
   Follow-ups) e rode
   `gh pr create --base main --title "..." --body-file <temp>`; apague o temp.
5. **CI**: `gh pr checks <n> --watch --interval 20` até tudo `pass`/`SUCCESS`.
   Jobs que aparecem "omitidos" em segundos são sucesso, não falha.
6. **Se falhou**: `gh run view <run> --log-failed`, identifique a causa, corrija,
   commit + push e volte ao passo 5.
7. **Verde**: `gh pr review <n> --approve` (best-effort) e
   `gh pr merge <n> --merge --delete-branch`.
8. **Confirmar**: `gh pr view <n> --json state,mergedAt,mergeCommit,url` →
   esperado `MERGED`. Atualize o local:
   `git fetch origin && git checkout main && git pull origin main`.

## Notas deste ambiente (Windows + DSH, já verificadas)

- `gh` já está autenticado (`lgustavoss`).
- **Self-approve é bloqueado** pelo GitHub:
  `Review Can not approve your own pull request` — siga para o merge; este repo
  permite merge sem aprovação de terceiro.
- Logo após o push, `gh pr checks --watch` pode sair com
  `no checks reported on the '...' branch` (corrida do run aparecer). Espere
  ~25s e repita.
- **Não existe Python no host** (`python` é atalho da Microsoft Store; `py` não
  existe). Scripts de `scripts/` que precisam de git+python não rodam localmente;
  a validação fica no CI.
- Testes rápidos antes do push:
  - backend: `docker compose run --rm --no-deps backend pytest -q`
  - frontend: `VITE_API_URL=https://ci.invalid.example npm run build`
  - mobile: `cd mobile && npm run typecheck`
- Imagem Docker velha sem `pytest-xdist` → `docker compose build backend` antes
  do pytest (o compose passa `INSTALL_DEV=1`).
- Corpo do PR via `--body-file` (evita quoting no PowerShell/bash); arquivo
  temporário removido depois.

## Entrega

Reporte a tabela: URL do PR, branch → base, CI (verde/falhou), aprovação,
merge (SHA do merge), commit em `main`.
