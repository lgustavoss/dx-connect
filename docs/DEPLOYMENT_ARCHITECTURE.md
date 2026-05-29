# Arquitetura de deploy — um cliente, um PostgreSQL

**Decisão de produto (2026-05):** em produção, cada cliente pagante do DX Connect terá **isolamento por instância de dados**, não por `tenant_id` num banco compartilhado.

## Alvo

| Aspecto | Direção |
|---------|---------|
| Infra | Mesma **VPS** (ou cluster) para vários clientes |
| URL | **Subdomínio** por cliente (ex.: `duplexsoft.connect.duplexsoft.com.br`, `clienteb.connect.duplexsoft.com.br`) |
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

## Relacionado

- Épico deploy: **#170**
- Épico refatoração de código: **#191**
- Épico operacional legado: **#16**
- Checklist de servidor: [`PRE_DEPLOY_CHECKLIST.md`](PRE_DEPLOY_CHECKLIST.md)
