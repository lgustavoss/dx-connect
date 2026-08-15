---
name: design-feature
description: Planeja features do DX Connect — camadas, RBAC, SSE, migrations e ordem de implementação. Use ao planejar épicos, quebrar issues, ou antes de codar features novas (ex. chat interno, SLA, portal).
---

# Design Feature — DX Connect

Playbook para **planear** antes de implementar. Não escreva código nesta fase — produza um plano revisável **no chat**.

## Quando usar

- Épico ou issue no **GitHub** (`gh issue view`)
- Feature que cruza backend + frontend + tempo real
- Dúvida sobre onde colocar lógica ou como aplicar RBAC

**Não** criar ficheiros em `.github/planning-issue-bodies/` para o plano — ver rule `planning-github-source`.

## Fase 1 — Ler e delimitar

1. Ler body completo da issue/épico no GitHub
2. Extrair:
   - **Objetivo** (1 frase)
   - **Dentro do escopo** / **Fora do escopo**
   - **Dependências** (issues bloqueantes)
   - **Critérios de aceite**
3. Identificar bounded context: tickets, chats, notificações, cadastro, WhatsApp, comercial, etc.

Se faltar escopo, pergunte uma vez com opções — não assuma.

## Fase 2 — Mapa técnico

Preencha mentalmente (e no output do chat) esta tabela:

| Camada | Arquivos prováveis | Necessário? |
|--------|-------------------|-------------|
| Model | `backend/app/models/` | sim/não |
| Migration | `backend/alembic/versions/` | sim/não |
| Schema | `backend/app/schemas/` | sim/não |
| Service | `backend/app/services/` | sim/não |
| API | `backend/app/api/` + `main.py` | sim/não |
| Testes | `backend/tests/test_*.py` | sim |
| SSE | `realtime.py` + evento novo | sim/não |
| Frontend API | `frontend/src/api/client.ts` | sim/não |
| UI | `pages/` + `components/` | sim/não |

## Fase 3 — Decisões de arquitetura

Consultar e aplicar:

| Tema | Onde decidir | Pergunta-chave |
|------|--------------|----------------|
| RBAC | `docs/BACKEND_RBAC.md`, `setor_scope` | Admin-only, comercial, ou escopo por setor? |
| SSE | `docs/REALTIME_SSE.md` | Quem recebe o evento? Payload? |
| Deploy | `docs/DEPLOYMENT_ARCHITECTURE.md` | Afeta multi-cliente / migration? |
| Tenant | `project-core` rule | Não modelar em cima de `tenant_id` legado |

### Checklist RBAC

- [ ] Rotas de cadastro usam `exigir_admin` (ou papel adequado)
- [ ] Operação usa `obter_atendente_atual` + `setor_scope` quando aplicável
- [ ] Homônimos considerados (não filtrar só no frontend)
- [ ] Testes 403 documentados

### Checklist tempo real

- [ ] Tipo de evento definido
- [ ] Publicação **após commit** DB
- [ ] Destinatários filtrados por RBAC
- [ ] Frontend via `EventStreamContext` (sem SSE duplicado)

## Fase 4 — Ordem de implementação

```
1. Model + migration (alembic heads único)
2. Schemas Pydantic
3. Service (regras de negócio + RBAC)
4. Rotas API + OpenAPI
5. Testes backend (happy path + 403)
6. Eventos SSE (se aplicável)
7. client.ts (tipos + funções)
8. UI (pages/components)
9. Integração SSE no frontend
10. Build frontend
```

Agrupar em **lotes/PRs** conforme `main-pr-batch-delivery` (não micro-PR por issue).

## Fase 5 — Output do plano

Entregar **no chat**. Após confirmação do utilizador → `gh issue comment` na issue/épico.

```markdown
## Resumo
[1–2 frases]

## Escopo
- Dentro: ...
- Fora: ...

## Mapa de arquivos
| Ação | Caminho |
|------|---------|
| criar | ... |
| alterar | ... |

## RBAC
- Admin: ...
- Atendente / comercial: ...
- Casos 403: ...

## SSE (se houver)
- ...

## Ordem de implementação
1. ...

## Testes
- [ ] ...

## Riscos / dúvidas
- ...

## Próximo passo
→ `/iniciar-feature` + `/implementar-issue #<issue-ou-lote>`
```

## Referências

- `docs/BACKEND_RBAC.md`
- `docs/REALTIME_SSE.md`
- `docs/ALEMBIC_MIGRATIONS.md`
- Issues no GitHub (não cópias locais de bodies)
