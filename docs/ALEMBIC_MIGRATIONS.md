# Alembic: padrão de revisions (evitar quebra em deploy)

## Regra de ouro

- O encadeamento das migrations é definido pelos IDs **internos** `revision` e `down_revision`.
- O `down_revision` deve apontar para um **`revision` que existe** (em algum arquivo dentro de `backend/alembic/versions/`).
- **Nome do arquivo não é referência**. Se o arquivo chama `004_atendente_must_change_password.py`, isso **não** significa que o `revision` seja `"004_atendente_must_change_password"`.
- O valor de `revision` deve ter no máximo **32** caracteres (`alembic_version.version_num` é `varchar(32)`).

Quando esse encadeamento fica inconsistente, o comando `alembic upgrade head` falha antes mesmo de consultar o banco, com erros do tipo `KeyError`/`Revision ... is not present`.

## Boas práticas para evitar o problema

- **Ao criar uma migration nova**, sempre confira:
  - o `revision` gerado
  - o `down_revision` que ela referencia
  - se o `down_revision` bate com o `revision` real da migration anterior
- **Evite trocar o valor de `revision`** de uma migration que já pode ter sido aplicada em algum ambiente. Se precisar padronizar IDs antigos, prefira planejar isso como uma ação controlada (ex.: com `alembic stamp`) e documentar para todos os ambientes.

## Checagem rápida (local/CI)

No container/ambiente do backend:

```bash
alembic heads
alembic history
```

Se `history`/`heads` já falhar, há inconsistência de `revision`/`down_revision`.

Se `alembic heads` listar **mais de uma** revision, `alembic upgrade head` falha no deploy. Crie uma migration de **merge** (sem DDL) com `down_revision` em tupla apontando para cada head — ver `029_merge_ticket_parent_and_outbox_heads.py`.

## Hotfix manual (DDL antes do deploy)

Em produção, às vezes é necessário aplicar SQL manual **antes** do release (ex.: coluna faltando que quebra login). Regras:

1. **Preferir** `ALTER TABLE … ADD COLUMN IF NOT EXISTS` (Postgres) — alinhado ao que a migration idempotente faria no próximo deploy.
2. **Não** alterar `alembic_version` à mão, salvo `alembic stamp` planejado com o time.
3. Migrations idempotentes do repo (`has_table`, `_ensure_columns`, `_ensure_indexes`) **não** recriam colunas obrigatórias ausentes — só completam colunas opcionais e índices quando a tabela já existe.

### Exemplo: `134_ponto_dia_convocado_985` (#985)

Se `ponto_dias_convocados` foi criada manualmente:

| Situação | O que a migration faz |
|----------|------------------------|
| Tabela não existe | `CREATE TABLE` + índices |
| Tabela existe, faltam colunas opcionais (`tolerancia_minutos`, `estado`, `criado_por_id`, `created_at`, `cancelado_*`) | `ADD COLUMN` só das ausentes |
| Tabela existe, faltam índices | `CREATE INDEX` dos ausentes |
| Tabela existe **sem** colunas obrigatórias (`tenant_id`, `atendente_id`, `data_ref`, `inicio`, `fim`, `motivo`) | **Não corrige** — o DDL manual deve incluir o núcleo; ajuste o SQL na VPS ou recrie a tabela |

SQL mínimo aceitável para hotfix manual (Postgres):

```sql
CREATE TABLE IF NOT EXISTS ponto_dias_convocados (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    atendente_id INTEGER NOT NULL REFERENCES atendentes(id) ON DELETE CASCADE,
    data_ref DATE NOT NULL,
    inicio VARCHAR(5) NOT NULL,
    fim VARCHAR(5) NOT NULL,
    motivo VARCHAR(1000) NOT NULL
);
-- Colunas opcionais e índices: o deploy (migration 134) completa se faltarem.
```

Teste automatizado: `backend/tests/test_alembic_134_idempotent.py`.

