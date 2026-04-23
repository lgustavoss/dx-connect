## Contexto

Deploy em produção/staging falhou ao executar `alembic upgrade head` com erro:

- `KeyError: '004_atendente_must_change_password'`

Isso ocorreu porque a migration `005_rede_login_retaguarda` referenciava um `down_revision` que **não existe** como `revision` no repositório.

## O que foi feito

- Ajuste da cadeia Alembic: `005_rede_login_retaguarda` agora referencia o `revision` correto (`004_must_pwd`).
- Documentação: adiciona `docs/ALEMBIC_MIGRATIONS.md` e reforça o checklist em `docs/PRE_DEPLOY_CHECKLIST.md`.

## Por que assim (e não “renomear” o revision antigo)

Alterar o `revision` de uma migration existente pode quebrar ambientes que já tenham essa revisão aplicada (valor registrado em `alembic_version`). O ajuste no `down_revision` resolve o problema sem exigir re-stamp do banco.

## Test plan

- Em ambiente do backend: `alembic history` / `alembic heads` (deve funcionar sem warnings/KeyError)
- No VPS antes do `up --build`: `docker compose -f docker-compose.prod.yml run --rm backend alembic upgrade head`

