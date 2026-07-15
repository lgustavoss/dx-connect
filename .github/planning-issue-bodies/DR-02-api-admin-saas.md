# DR-02 — API admin SaaS (backend)

## Contexto

Parte de: DR-01 (modelo).

## Objetivo

API REST admin para CRUD de clientes SaaS / licenças e ações stub de provisionar/suspender.

## Escopo

### Dentro

- `GET/POST /v1/saas/clientes` (ou prefixo acordado)
- `GET/PATCH /v1/saas/clientes/{id}`
- Ação suspender / reativar
- Ação «registrar instância provisionada» (URL/host) sem orquestrar Docker ainda
- Stub ou flag para «solicitar provisionamento» (implementação real em DR-04)
- OpenAPI + testes (happy path + 403)

### Fora

- Orquestração shell/Docker (DR-04)
- UI (DR-03)
- Trial público (DR-07)

## RBAC

- `exigir_admin` (ou papel comercial dedicado na instância DeskRudder)
- Não expor rotas em instâncias de clientes que não sejam a comercial (feature flag / config `SAAS_CONTROL_PLANE=true` ou similar)

## Critérios de aceite

- [ ] CRUD funciona com testes
- [ ] 403 para atendente sem permissão
- [ ] Feature isolada à instância control-plane (não vazar para instâncias de clientes)

## Dependências

- Requer: DR-01

## Labels

`enhancement`, `backend`, `python`
