# DR-03 — UI painel de licenças (frontend)

## Contexto

Parte de: DR-02.

## Objetivo

Painel interno na instância DeskRudder para listar, criar e editar clientes SaaS / licenças; link para a URL da instância do cliente (onde vive o `/kb` daquele cliente).

## Escopo

### Dentro

- Rota admin (ex. `/saas/licencas` ou sob Configurações)
- Listagem com status e data de renovação
- Formulário criar/editar
- Link externo para host da instância
- Mensagens de erro em português

### Fora

- Wizard de provisionamento Docker (DR-04)
- Landing pública (DR-05 / #515)
- Billing

## RBAC

- Visível só para admin (e comercial, se aplicável); menu oculto se control-plane desligado

## Critérios de aceite

- [ ] Admin vê listagem e detalhe
- [ ] Atendente comum não acessa (UI + API)
- [ ] Link da instância abre URL correta
- [ ] `npm run build` passa

## Dependências

- Requer: DR-02

## Labels

`enhancement`, `frontend`, `ux`
