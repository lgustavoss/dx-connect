# Alembic: padrão de revisions (evitar quebra em deploy)

## Regra de ouro

- O encadeamento das migrations é definido pelos IDs **internos** `revision` e `down_revision`.
- O `down_revision` deve apontar para um **`revision` que existe** (em algum arquivo dentro de `backend/alembic/versions/`).
- **Nome do arquivo não é referência**. Se o arquivo chama `004_atendente_must_change_password.py`, isso **não** significa que o `revision` seja `"004_atendente_must_change_password"`.

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

