---
name: design-feature
description: Planeja features do DX Connect — camadas, RBAC, SSE, migrations e ordem de implementação. Use ao planejar épicos, quebrar issues, ou antes de codar features novas (ex. chat interno, SLA, portal).
---

# Design Feature — DX Connect

Playbook para **planejar** antes de implementar. Não escreva código nesta fase — produza um plano revisável.

## Quando usar

- Épico ou issue nova em `.github/planning-issue-bodies/`
- Feature que cruza backend + frontend + tempo real
- Dúvida sobre onde colocar lógica ou como aplicar RBAC

## Fase 1 — Ler e delimitar

1. Ler body completo da issue/épico
2. Extrair:
   - **Objetivo** (1 frase)
   - **Dentro do escopo** / **Fora do escopo**
   - **Dependências** (issues bloqueantes)
   - **Critérios de aceite**
3. Identificar bounded context: tickets, chats, notificações, cadastro, WhatsApp, etc.

Se faltar escopo, pergunte uma vez com opções — não assuma.

## Fase 2 — Mapa técnico

Preencha mentalmente (e no output) esta tabela:

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
| RBAC | `docs/BACKEND_RBAC.md`, `setor_scope` | Admin-only ou escopo por setor? |
| SSE | `docs/REALTIME_SSE.md` | Quem recebe o evento? Payload? |
| Deploy | `docs/DEPLOYMENT_ARCHITECTURE.md` | Afeta multi-cliente / migration? |
| Tenant | `project-core` rule | Não modelar em cima de `tenant_id` legado |

### Checklist RBAC

- [ ] Rotas de cadastro usam `exigir_admin`
- [ ] Operação usa `obter_atendente_atual` + `setor_scope`
- [ ] Homônimos considerados (não filtrar só no frontend)
- [ ] Testes 403 documentados

### Checklist tempo real

- [ ] Tipo de evento definido (`chat.mensagem`, `ticket.fila`, etc.)
- [ ] Publicação **após commit** DB
- [ ] Destinatários filtrados por RBAC
- [ ] Frontend consome via `EventStreamContext` (sem SSE duplicado)

## Fase 4 — Ordem de implementação

Ordem padrão para features full-stack:

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

Quebrar em **issues/sub-PRs** quando possível (ex.: IC-01 → IC-02 → IC-03).

## Fase 5 — Output do plano

Entregar neste formato:

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
- Atendente: ...
- Casos 403: ...

## SSE (se houver)
- Tipo: ...
- Payload: ...
- Quem recebe: ...

## Ordem de implementação
1. ...
2. ...

## Testes
- [ ] ...
- [ ] ...

## Riscos / dúvidas
- ...

## Próximo passo
→ `/implementar-issue @<arquivo-da-issue.md>`
```

## Referências

- `docs/BACKEND_RBAC.md`
- `docs/REALTIME_SSE.md`
- `docs/ALEMBIC_MIGRATIONS.md`
- `.github/planning-issue-bodies/`
