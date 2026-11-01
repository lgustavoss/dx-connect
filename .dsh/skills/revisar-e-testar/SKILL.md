---
name: revisar-e-testar
description: "Revisa o diff atual (working tree ou PR) com o checklist de arquitetura/RBAC/SSE, roda só os testes que o diff exige e entrega o relatório pré-merge em pt-BR."
whenToUse: "Quando o usuário pedir /revisar-e-testar, revisão pré-merge, revisar a branch ou verificar antes do PR."
---

# /revisar-e-testar — revisão pré-merge

Este skill é o comando `/revisar-e-testar` do DX Connect. O playbook completo
está em `.cursor/commands/revisar-e-testar.md` — **leia antes de começar**; se
divergir deste resumo, o playbook vence.

## Regras que não se negociam

- Confirme que a branch **não** é `main`/`staging`; se for, avise para usar
  `/iniciar-feature` e pare.
- Revise o diff real (`git diff` + commits), não a memória do que foi feito.
- **Só rode os testes que o diff exige** (mesma regra do CI). Se não toca
  backend, não rode pytest; se não toca frontend, não rode build; se não toca
  `mobile/`, não rode tsc.
- Se um teste **executado** falhar, corrija antes de concluir.
- Mudança mínima: não aprove refatoração não solicitada.

## Checklist (resumo)

- **Geral**: critérios de aceite da issue, strings de UI/erro em pt-BR, diff
  mínimo.
- **Backend**: lógica em `services/`, rotas finas; RBAC (`exigir_admin` /
  `obter_atendente_atual`) e escopo por setor no servidor; testes com caminho
  feliz e 403/404; migration com `revision`/`down_revision` coerentes e head
  único.
- **Frontend**: HTTP só via `frontend/src/api/client.ts`, erros via
  `errorMessage.ts`; rotas admin com `AdminRoute`; sem filtrar setores no cliente.
- **SSE/realtime**: publicar após commit; sem conexão duplicada por tela.

## Notas deste ambiente (Windows + DSH, já verificadas)

- **Não existe Python no host** (`python` = atalho da Store; `py` não existe),
  então `python scripts/ci_detect_changes.py` **não roda localmente**. Reproduza
  a regra lendo `scripts/ci_detect_changes.py` e o job `changes` de
  `.github/workflows/ci.yml`, ou decida pelas pastas do diff:
  - `backend/`, `scripts/`, `.github/workflows/ci.yml` → backend
  - `frontend/`, `.github/workflows/ci.yml` → frontend
  - `mobile/`, `.github/workflows/ci.yml` → mobile
- Comandos:
  - backend: `docker compose run --rm --no-deps backend pytest -q`
    (se a imagem estiver velha: `docker compose build backend`).
  - frontend: `VITE_API_URL=https://ci.invalid.example npm run build`
    (sem a env o build falha por design; o CI define em `ci.yml`).
  - mobile: `cd mobile && npm run typecheck` (não há ESLint configurado; o gate
    é o tsc).
- Diff contra `origin/main`, incluindo working tree:
  `git fetch origin && git diff --name-only origin/main...HEAD` e
  `git status --short`.
- Em diffs grandes de backend, vale delegar um subagente só para o backend e
   cruzar as conclusões.

## Relatório

Formato do playbook:

```markdown
## Resumo
[1–2 frases]

## 🔴 Crítico (bloqueia merge)
- arquivo:linha — problema + por quê

## 🟡 Sugestão
- ...

## 🟢 OK / observações
- ...

## Testes
- comando → resultado
- omitido e por quê
```
