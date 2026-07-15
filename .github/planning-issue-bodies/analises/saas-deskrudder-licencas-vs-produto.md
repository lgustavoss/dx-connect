# Análise — SaaS DeskRudder vs produto por instância

**Data:** 2026-07-14  
**Status:** decisão de vocabulário e roadmap (documentação)  
**Não substitui** issues no GitHub — ver épico DR e índice em `ISSUES_CRIADAS.md`.

---

## Contexto

O DeskRudder é um produto SaaS para **empresas que dão suporte a outros sistemas**. Havia confusão entre:

1. Camada para **vender e operar** o DeskRudder (LP, licenças, instâncias)
2. Módulos **dentro** de cada instância do cliente (helpdesk, KB, CRM, etc.)
3. O papel do portal `/kb`

Esta análise fixa o vocabulário e a relação com épicos existentes.

---

## Duas camadas

| Camada | Quem usa | O que é |
|--------|----------|---------|
| **SaaS DeskRudder** | Equipe DeskRudder + prospects | Landing `deskrudder.com.br`, painel de licenças/instâncias, contato comercial B2B, trial/renovações |
| **Produto (por instância)** | Atendentes do cliente; funcionários da rede (#263); cliente final no `/kb` | Helpdesk, KB white-label, CM/FN, portal autenticado do funcionário |

**CM/FN (#321–#375)** = módulos do **produto** que o cliente DeskRudder usa no negócio dele (custos, CRM, contratos, NFe, boletos). **Não** é o painel de licenças SaaS.

---

## Personas

| Persona | Onde age | Objetivo |
|---------|----------|----------|
| **Prospect** | Landing `deskrudder.com.br` | Conhecer o produto e falar com o comercial DeskRudder |
| **Operador DeskRudder** | Instância comercial / painel SaaS | Gerir licenças, renovações, provisionar instâncias, atender leads |
| **Cliente DeskRudder** (empresa de suporte) | Instância dela (`cliente01.deskrudder.com.br`) | Atender as redes/empresas que ela suporte; publicar manuais no `/kb` |
| **Cliente final** | `/kb` (e futuramente portal #263) da **instância do cliente DeskRudder** | Consultar manuais / abrir ticket com o suporte que o atende |

---

## Papel do KB

O portal `/kb` é **módulo do produto**, não canal SaaS:

- Cada cliente DeskRudder cria **seu próprio** portal de manuais (marca, artigos, chat opcional) para o **cliente final dele**.
- `cliente01` e `cliente02` têm KBs **diferentes** por isolamento de instância (Postgres + stack dedicados — #170).
- Chat do `/kb` = cliente final ↔ atendentes **daquele** cliente DeskRudder.
- **Não** reutilizar esse chat na landing comercial DeskRudder (público e objetivo distintos).

Épico de produto [#464](https://github.com/lgustavoss/dx-connect/issues/464) (portal KB white-label) está **entregue** e deve ser fechado; não é trabalho da camada SaaS.

---

## URL de instância

Decisão vigente (#170, `docs/DEPLOYMENT_ARCHITECTURE.md`):

- **Subdomínio** por cliente: `cliente01.deskrudder.com.br`
- **PostgreSQL dedicado** por cliente
- O discurso `www.deskrudder.com.br/cliente01` = **slug** no painel SaaS (redirect/alias possível), **não** path compartilhando a mesma BD

---

## Relação com épicos existentes

| Épico / faixa | Camada | Notas |
|---------------|--------|-------|
| #515, #516 | SaaS | LP + contato comercial (LP-02 revisada — sem chat `/kb`) |
| Épico DR (novo) | SaaS | Licenças, provisionamento, trial, renovações |
| #170 | Infra SaaS | Scripts/runbook; DR-04 orquestra via produto |
| #321–#375 (CM/FN) | Produto | Roadmap Fase 2 |
| #263 / #300–#308 | Produto | Portal funcionário — Fase 3 |
| #464 / KB | Produto | Entregue — fechar |
| #419, #120–#124 | Produto | Entram no roadmap (Fases 3–4); não “futuro eterno” |

---

## Roadmap resumido

| Fase | Foco |
|------|------|
| 0 | Higiene, vocabulário, abrir issues DR |
| 1 | Go-to-market SaaS: LP, contato comercial, painel licenças (manual + #170) |
| 2 | CM/FN (#321 → #328) |
| 3 | Portal funcionário (#263) |
| 4 | Provision automático, trial, renovações; RBAC; SLA WhatsApp |

Hotfixes de produção furam a fila.

---

## Conclusão

Documentar e desenvolver a camada SaaS **em paralelo** ao aprofundamento do produto, sem misturar personas nem reutilizar o chat `/kb` para funil comercial. Tudo o que está no backlog aberto permanece no plano de entrega — a ordenação é por fase, não por descarte.
