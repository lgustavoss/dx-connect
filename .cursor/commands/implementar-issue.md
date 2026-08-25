# Implementar issue

Implemente a issue ou épico indicado pelo usuário seguindo o padrão do DX Connect.

## Entrada

Se o usuário não passou issue, peça:
- número/link da issue GitHub **ou**
- descrição do lote (ex.: «lote A do #322»)

Ler o body com `gh issue view` (e issues filhas do lote). **Não** depender de ficheiros locais em `.github/planning-issue-bodies/` para o corpo da issue.

Leia o body completo antes de codar. Respeite **fora de escopo** e **critérios de aceite**.

## Fase 0 — Git (obrigatório)

Antes de editar código:

1. Verifique a branch atual (`git branch --show-current`)
2. Se estiver em `main` ou `staging`, **pare** e oriente `/iniciar-feature`
3. Se não houver branch de feature, crie uma seguindo `git-workflow` rule

**Nunca** implementar direto em `main`.

## Fase 1 — Entendimento (não pule)

1. Resuma em 3–5 bullets: objetivo, escopo, fora de escopo
2. Identifique camadas afetadas: `models`, `schemas`, `services`, `api`, `tests`, `frontend`
3. Verifique dependências: RBAC (`docs/BACKEND_RBAC.md`), SSE (`docs/REALTIME_SSE.md`), migrations
4. Se algo estiver ambíguo, pergunte **uma** vez com opções claras

## Fase 2 — Backend (se aplicável)

- [ ] Model + migration Alembic (checar `down_revision` e heads únicos)
- [ ] Schema Pydantic
- [ ] Service com lógica de negócio
- [ ] Rota fina em `api/` com RBAC correto
- [ ] Teste em `backend/tests/`
- [ ] Evento SSE pós-commit, se feature for tempo real

Rodar pytest **só se o lote tocou backend/scripts/CI** (mesma regra do `/revisar-e-testar`):

```bash
docker compose run --rm --no-deps backend pytest -q
```

## Fase 3 — Frontend (se aplicável)

- [ ] Tipos/funções em `api/client.ts`
- [ ] Página ou componente em `pages/` / `components/`
- [ ] `AdminRoute` se for área admin
- [ ] Integrar SSE via `EventStreamContext` se aplicável
- [ ] Mensagens de erro em português do Brasil

Rodar: `cd frontend && npm run build`

## Fase 4 — Fechamento

Entregue resumo com:
- Branch atual
- Arquivos alterados (agrupados por camada)
- Como testar manualmente (passos concretos)
- O que **não** foi feito (fora de escopo)
- Pendências ou riscos

Sugira próximos passos:

```
/revisar-e-testar
/criar-pr
```

**Não** commitar, push ou abrir PR a menos que o usuário peça ou use `/criar-pr`.
