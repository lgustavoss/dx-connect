# DR-01 — Modelo Licença / ClienteSaaS (backend)

## Contexto

Épico: DeskRudder SaaS — licenças e instâncias.

A **instância comercial** DeskRudder precisa persistir os clientes pagantes (e trials): slug, status, datas de renovação, plano — ortogonal a `Rede`/`Empresa` do helpdesk na instância do cliente.

## Objetivo

Modelo de dados na BD da instância DeskRudder para registro SaaS.

## Escopo

### Dentro

- Entidade(s) ex.: `ClienteSaaS` / `LicencaDeskRudder` com: nome, slug único, status (`trial` | `ativo` | `suspenso` | `churn`), `data_inicio`, `data_renovacao`, plano (texto/enum inicial), URL/host da instância, notas
- Migration Alembic (head único)
- Sem provisionamento automático nesta issue (DR-04)

### Fora

- UI (DR-03), API completa além do necessário para testes de modelo (API em DR-02)
- Cobrança / gateway
- Dados nas BD dos clientes provisionados

## RBAC

- Admin (e perfil comercial, se existir) na instância DeskRudder — detalhar em DR-02

## Critérios de aceite

- [ ] Migration aplica em ambiente limpo; `alembic heads` único
- [ ] Constraints: slug único; status validado
- [ ] Testes de modelo/repositório básicos

## Dependências

- Nenhuma de produto; #170 para URL/host real da instância

## Labels

`enhancement`, `backend`, `python`
