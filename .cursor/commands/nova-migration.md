# Nova migration

Crie ou revise uma migration Alembic seguindo o padrão do DX Connect.

## Pré-requisitos

- Alteração de model em `backend/app/models/` já definida (ou descreva o DDL necessário)
- Branch de feature ativa (não `main`) — use `/iniciar-feature` se necessário

## Passo 1 — Estado atual

```bash
docker compose run --rm --no-deps backend alembic heads
docker compose run --rm --no-deps backend alembic history -r -3:
```

Confirme:
- [ ] **Um único head** — se houver 2+, pare e crie migration de **merge** (sem DDL)
- [ ] Anote `revision` do head atual (ID interno, não nome do arquivo)

## Passo 2 — Gerar migration

```bash
docker compose run --rm --no-deps backend alembic revision -m "descricao_curta"
```

Ou com autogenerate (revisar diff manualmente):

```bash
docker compose run --rm --no-deps backend alembic revision --autogenerate -m "descricao_curta"
```

## Passo 3 — Validar arquivo gerado

- [ ] `down_revision` = `revision` real do head anterior
- [ ] `revision` único e coerente
- [ ] `upgrade()`/`downgrade()` corretos; sem DDL desnecessário
- [ ] Nome do arquivo **não** importa — só os IDs internos

Modelo de merge (se 2 heads):

```python
revision = "XXX_merge_descricao"
down_revision = ("head_a", "head_b")

def upgrade() -> None:
    pass
```

Referência: `029_merge_ticket_parent_and_outbox_heads.py`

## Passo 4 — Testar localmente

```bash
docker compose run --rm --no-deps backend alembic upgrade head
docker compose run --rm --no-deps backend pytest -q
```

## Passo 5 — Entrega

Informe:
- Arquivo criado
- `revision` / `down_revision`
- Resultado de `alembic heads` (deve ser 1)
- Testes passando

Lembrete: deploy roda `upgrade head` **em cada** Postgres de cliente.
