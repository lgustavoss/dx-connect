# [Épico] DeskRudder SaaS — licenças, instâncias e go-to-market

## Contexto

O DeskRudder é vendido para empresas que dão suporte a outros sistemas. Cada cliente pagante recebe uma **instância isolada** (subdomínio + PostgreSQL — #170) com o produto completo, incluindo o portal `/kb` white-label para o **cliente final dele**.

Falta a **camada SaaS** na instância comercial (`deskrudder.com.br`): landing, contato comercial B2B, registro de licenças/renovações e orquestração de provisionamento.

Análise: `.github/planning-issue-bodies/analises/saas-deskrudder-licencas-vs-produto.md`

## Objetivo

Entregar go-to-market + operação mínima de licenças:

1. Landing pública e canal de contato comercial (prospect → DeskRudder)
2. Modelo e painel de clientes SaaS / licenças (slug, status, renovação)
3. Provisionamento de instâncias (manual → automático)
4. Trial e alertas de renovação

## Não confundir

| Isto | Não é |
|------|-------|
| Painel de licenças DeskRudder | CM/FN (#321–#375) — módulos do produto na instância do cliente |
| Contato comercial na LP | Chat do `/kb` (cliente final ↔ cliente DeskRudder) |
| Portal #263 | Login do funcionário da rede na instância do cliente |

## Fases

| Fase | Issues | Entrega |
|------|--------|---------|
| **DR-F0** | DR-00 | Vocabulário / higiene (#464 fechar) |
| **DR-F1** | DR-05, DR-06 | Landing + contato comercial |
| **DR-F2** | DR-01, DR-02, DR-03 | Modelo + API + UI licenças (registro manual de instância já provisionada) |
| **DR-F3** | DR-04, DR-07, DR-08 | Provision automático, trial, renovações |

## Issues filhas

| ID | Título | GitHub |
|----|--------|--------|
| DR-00 | Análise e vocabulário SaaS vs produto | [#520](https://github.com/lgustavoss/dx-connect/issues/520) fechada |
| DR-01 | Modelo Licença / ClienteSaaS (backend) | [#521](https://github.com/lgustavoss/dx-connect/issues/521) |
| DR-02 | API admin SaaS (backend) | [#522](https://github.com/lgustavoss/dx-connect/issues/522) |
| DR-03 | UI painel de licenças (frontend) | [#523](https://github.com/lgustavoss/dx-connect/issues/523) |
| DR-04 | Provisionamento de instâncias | [#524](https://github.com/lgustavoss/dx-connect/issues/524) |
| DR-05 | Landing LP-01 — vínculo | [#525](https://github.com/lgustavoss/dx-connect/issues/525) / [#515](https://github.com/lgustavoss/dx-connect/issues/515) |
| DR-06 | Contato comercial na landing | [#526](https://github.com/lgustavoss/dx-connect/issues/526) / [#516](https://github.com/lgustavoss/dx-connect/issues/516) |
| DR-07 | Trial / pré-cadastro | [#527](https://github.com/lgustavoss/dx-connect/issues/527) |
| DR-08 | Renovações e alertas | [#528](https://github.com/lgustavoss/dx-connect/issues/528) |

Épico: [#519](https://github.com/lgustavoss/dx-connect/issues/519)

## Relacionado

- Deploy: #170
- Portal KB entregue: #464
- Portal funcionário: #263
- Produto CM/FN: #321–#328
- Meta: #16

## Fora do v1

- Billing automático via gateway de pagamento do *produto DeskRudder*
- Login do cliente final no control-plane SaaS
- Path `www.deskrudder.com.br/cliente01` como isolamento (usa-se subdomínio)

## Labels

`epic`, `enhancement`, `fase-interna`

## Roadmap

Ver fases 0–4 em `ISSUES_CRIADAS.md` (seção SaaS / roadmap).
