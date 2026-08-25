# Arquitetura de deploy — um cliente, um PostgreSQL

**Decisão de produto (2026-05):** em produção, cada cliente pagante do DX Connect terá **isolamento por instância de dados**, não por `tenant_id` num banco compartilhado.

## Alvo

| Aspecto | Direção |
|---------|---------|
| Infra | Mesma **VPS** (ou cluster) para vários clientes |
| URL | **Subdomínio** por cliente (ex.: `duplexsoft.deskrudder.com.br`, `cliente02.deskrudder.com.br`) |
| Dados | **Um PostgreSQL por cliente** (`DATABASE_URL` distinta por deploy) |
| API | **Um container Docker por cliente** (modelo adotado — ver abaixo) |
| Código | Tratar cada deploy como **single-tenant**: sem filtrar “outro cliente” na mesma base |

## Estado atual do repositório (transitório)

| Aspecto | Hoje |
|---------|------|
| Banco | Uma `DATABASE_URL` por processo |
| Isolamento entre clientes | Coluna `tenant_id` + subdomínio numérico `{id}.connect...` |
| E-mail inbound | `tenant_inbound_addresses` na mesma base |
| Auth | JWT com `tid` + login filtrado por `tenant_id` |

Isto serve **desenvolvimento/staging** com vários “tenants” num Postgres local; **não** é o modelo de venda em produção.

## O que muda na implementação futura

1. **Deploy:** Nginx → subdomínio → backend com `.env` / secret da BD daquele cliente.
2. **Código:** Remover ou fixar `tenant_id` como legado interno (`1`); eliminar `tenant_scope` entre clientes.
3. **E-mail:** Endereços inbound e webhooks Resend **por instância** (config no `.env` ou tabela sem partilha entre clientes).
4. **Migrações Alembic:** `upgrade head` **em cada** base do cliente no deploy.
5. **Reset de senha (#105/#106):** escopo por e-mail na BD da instância; link com o **mesmo subdomínio** — sem `tenant_id` como eixo de isolamento.

## Modelo de deploy adotado (produção)

**Opção B — um container Docker por cliente** na mesma VPS:

1. Nginx (ou Caddy) encaminha `server_name` do subdomínio → porta do container daquele cliente.
2. Cada stack tem seu `docker-compose` (ou override) com `DATABASE_URL` apontando para o Postgres **dedicado** do cliente.
3. Frontend estático pode ser um build por cliente (`VITE_API_URL` do subdomínio) ou um artefacto com API no mesmo host.
4. No deploy: `alembic upgrade head` na BD do cliente antes ou durante o restart do container.

Não será usada, por agora, uma única API com roteamento dinâmico entre várias bases (opção A).

### Fase 1 — templates e runbook (implementado)

- [`deploy/clients/README.md`](../deploy/clients/README.md) — stack por cliente (Postgres + API + porta dedicada)
- `deploy/scripts/provision-client.sh` — gera `deploy/clients/<slug>/`
- `deploy/scripts/stack-client.sh` — migrate, up, seed, health

### Fase 2 — modo single-tenant no código (implementado)

Variáveis principais:

| Variável | Onde | Padrão | Uso |
|----------|------|--------|-----|
| `DX_CONNECT_MULTI_TENANT` | backend | `false` | `true` só em dev legado (mesmo Postgres, subdomínio numérico) |
| `CLIENT_APP_HOST` | backend | vazio | Host público do painel (`GET /v1/tenant/atual` → `app_host`) |
| `DEFAULT_TENANT_ID` | backend | `1` | ID fixo da linha `tenants` na BD da instância |
| `VITE_MULTI_TENANT` | frontend | `false` | Se `true`, envia `X-Dx-Tenant-Id` e resolve subdomínio numérico |
| `VITE_CLIENT_APP_HOST` | frontend | vazio | URL sugerida na tela de configuração |

Comportamento em **single-tenant** (`DX_CONNECT_MULTI_TENANT=false`, padrão):

- Middleware e login usam sempre `DEFAULT_TENANT_ID` (ignoram subdomínio numérico e cabeçalho `X-Dx-Tenant-Id`).
- Login por e-mail **sem** exigir `tenant_id` do host; refresh e rotas autenticadas não bloqueiam por divergência de subdomínio.
- Em `ENVIRONMENT=production`, `DX_CONNECT_MULTI_TENANT=true` é **rejeitado** na validação de settings.
- `GET /health` expõe `capabilities.multi_tenant_mode`.

Legado multi-tenant: definir `DX_CONNECT_MULTI_TENANT=true` (e no front `VITE_MULTI_TENANT=true`) apenas em desenvolvimento/staging com Postgres partilhado.

## Relacionado

- Épico deploy: **#170**
- Épico refatoração de código: **#191**
- Épico operacional legado: **#16**
- Control-plane vs cliente DuplexSoft: **#875** — stack em [`deploy/admin-center/`](../deploy/admin-center/README.md)
- Checklist de servidor: [`PRE_DEPLOY_CHECKLIST.md`](PRE_DEPLOY_CHECKLIST.md)
