# Chat interno — modelo de conversas e mensagens (backend)

## Contexto

Épico: **Chat interno entre atendentes e comunicados por setor**.

Parte de: **IC-F1**

## Proposta

### Entidades (sugestão)

| Tabela | Propósito |
|--------|-----------|
| `conversa_interna` | `tipo`: `direta` \| `setor`; `setor_id` (obrigatório se setor); `tenant_id` |
| `conversa_interna_participante` | N:N atendente↔conversa (direta: 2 linhas; setor: espelha `atendente_setor` ou lazy) |
| `mensagem_interna` | `conversa_id`, `atendente_id`, `corpo`, `created_at` |
| `conversa_interna_leitura` | `conversa_id`, `atendente_id`, `last_seen_at` |

### Regras

- **Canal setor:** no máximo **uma conversa** `tipo=setor` por `setor_id` (criada sob demanda).
- **Direta:** par único de atendentes reutiliza a mesma conversa (dedup por par ordenado).
- Mensagens só em conversas onde o atendente é participante ou membro do setor.
- Migrations Alembic versionadas.

## Critérios de aceite

- [ ] Migrations aplicam em Postgres limpo e em upgrade a partir de `head`
- [ ] Modelos SQLAlchemy exportados em `app/models/__init__.py`
- [ ] Índices em `conversa_id`, `atendente_id`, `setor_id`, `created_at`
- [ ] Testes unitários de factory/helpers (criar conversa direta, obter canal setor)

## Dependências

- Bloqueia: IC-02, IC-03

## Labels

`backend`, `chat-interno`, `fase-interna`
