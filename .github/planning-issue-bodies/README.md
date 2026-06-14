# Rascunhos de issues — planejamento DX Connect

Corpos de issue prontos para colar no GitHub. Cada arquivo segue o template do projeto (contexto, proposta, critérios de aceite, escopo técnico, dependências).

**Como usar:** abra uma issue no repositório, copie o conteúdo do `.md` correspondente e vincule ao épico pai indicado no cabeçalho do arquivo.

**Convenção de labels sugeridas:** `backend` | `frontend` | `epic` | `fase-interna` | `fase-portal` | `dashboard` | `sla` | `auditoria` | `tempo-real` | `roteamento` | `base-conhecimento`

---

## Ordem sugerida de implementação (uso interno primeiro)

| Fase | Épico | Prioridade | Observação |
|------|--------|------------|------------|
| 1 | [Tempo real (SSE)](#épico-rt--tempo-real) | Alta | Melhora chat e notificações sem unificar filas |
| 2 | [Distribuição automática de tickets](#épico-t--distribuição-automática-de-tickets) | Alta | Complementa fila receptiva; chats permanecem manuais |
| 3 | [Roteamento automático](#épico-r--roteamento-automático) | Alta | E-mail e abertura manual |
| 4 | [SLA](#épico-s--sla) | Média-alta | Depende de métricas de tempo (parcialmente dashboard) |
| 5 | [Dashboards e relatórios](#épico-d--dashboards-e-relatórios) | Média-alta | Pode iniciar em paralelo com SLA |
| 6 | [Auditoria estruturada](#épico-a--auditoria) | Média | Independente |
| 7 | [Base de conhecimento](#épico-kb--base-de-conhecimento) | Média | Editor interno primeiro; portal público no épico Portal |
| 8 | [Portal do cliente](#épico-p--portal-do-cliente-fase-futura) | Após consolidação interna | Issues abertas para planejamento |

**Fora de escopo por agora (decisão do time):** inbox omnichannel unificada, templates WhatsApp proativos, API pública/webhooks externos.

**Análises de viabilidade:** [`analises/integracao-retaguarda.md`](analises/integracao-retaguarda.md) · [`analises/filas-tickets-vs-chats.md`](analises/filas-tickets-vs-chats.md)

---

## Épico P — Portal do cliente (fase futura)

Meta: permitir que **funcionários da rede** abram e acompanhem tickets após o produto interno estar consolidado. Reutiliza `aberto_por_id`, CSAT e classificação existentes.

| Arquivo | Título sugerido | Camada |
|---------|-----------------|--------|
| [`P-epic-portal-cliente.md`](P-epic-portal-cliente.md) | **[Épico] Portal do cliente — visão e fases** | epic |
| [`P-01-backend-auth-portal-funcionario.md`](P-01-backend-auth-portal-funcionario.md) | Portal: autenticação e escopo por funcionário/rede/empresa | backend |
| [`P-02-backend-api-tickets-portal.md`](P-02-backend-api-tickets-portal.md) | Portal: API de listagem, detalhe e abertura de tickets | backend |
| [`P-03-backend-mensagens-anexos-portal.md`](P-03-backend-mensagens-anexos-portal.md) | Portal: mensagens públicas e anexos do solicitante | backend |
| [`P-04-backend-notificacoes-portal.md`](P-04-backend-notificacoes-portal.md) | Portal: notificações ao funcionário (e-mail) | backend |
| [`P-05-frontend-shell-portal.md`](P-05-frontend-shell-portal.md) | Portal: layout, rotas e login (app separado ou subpath) | frontend |
| [`P-06-frontend-listagem-tickets-portal.md`](P-06-frontend-listagem-tickets-portal.md) | Portal: listagem e filtros de tickets do funcionário | frontend |
| [`P-07-frontend-abertura-ticket-portal.md`](P-07-frontend-abertura-ticket-portal.md) | Portal: formulário de abertura com empresa/PDV | frontend |
| [`P-08-frontend-detalhe-ticket-portal.md`](P-08-frontend-detalhe-ticket-portal.md) | Portal: detalhe, timeline e CSAT | frontend |

---

## Épico D — Dashboards e relatórios

| Arquivo | Título sugerido | Camada |
|---------|-----------------|--------|
| [`D-epic-dashboards-relatorios.md`](D-epic-dashboards-relatorios.md) | **[Épico] Dashboards e relatórios operacionais** | epic |
| [`D-01-backend-metricas-dashboard-geral.md`](D-01-backend-metricas-dashboard-geral.md) | Dashboard geral: endpoints de métricas consolidadas | backend |
| [`D-02-backend-metricas-dashboard-tickets.md`](D-02-backend-metricas-dashboard-tickets.md) | Dashboard tickets: volume, MTTR, fila, CSAT | backend |
| [`D-03-backend-metricas-dashboard-chats.md`](D-03-backend-metricas-dashboard-chats.md) | Dashboard chats: fila, TMA, avaliações, encerramentos | backend |
| [`D-04-backend-relatorios-export.md`](D-04-backend-relatorios-export.md) | Relatórios: consultas paginadas e export CSV | backend |
| [`D-05-frontend-dashboard-geral.md`](D-05-frontend-dashboard-geral.md) | Dashboard geral: visão executiva e atalhos | frontend |
| [`D-06-frontend-dashboard-tickets.md`](D-06-frontend-dashboard-tickets.md) | Dashboard tickets: gráficos e filtros por período | frontend |
| [`D-07-frontend-dashboard-chats.md`](D-07-frontend-dashboard-chats.md) | Dashboard chats: métricas WhatsApp | frontend |
| [`D-08-frontend-relatorios-ui.md`](D-08-frontend-relatorios-ui.md) | Relatórios: telas de consulta e download | frontend |

---

## Épico S — SLA

| Arquivo | Título sugerido | Camada |
|---------|-----------------|--------|
| [`S-epic-sla.md`](S-epic-sla.md) | **[Épico] SLA configurável por setor e prioridade** | epic |
| [`S-01-backend-modelo-config-sla.md`](S-01-backend-modelo-config-sla.md) | SLA: modelo de metas e calendário comercial | backend |
| [`S-02-backend-calculo-violacoes-sla.md`](S-02-backend-calculo-violacoes-sla.md) | SLA: cálculo de prazos, pausas e violações | backend |
| [`S-03-backend-notificacoes-sla.md`](S-03-backend-notificacoes-sla.md) | SLA: alertas in-app e e-mail ao estourar prazo | backend |
| [`S-04-frontend-config-sla-admin.md`](S-04-frontend-config-sla-admin.md) | SLA: painel admin de configuração por setor | frontend |
| [`S-05-frontend-indicadores-sla-tickets.md`](S-05-frontend-indicadores-sla-tickets.md) | SLA: badges e filtros na listagem/detalhe de tickets | frontend |

---

## Épico R — Roteamento automático

| Arquivo | Título sugerido | Camada |
|---------|-----------------|--------|
| [`R-epic-roteamento.md`](R-epic-roteamento.md) | **[Épico] Motor de roteamento automático** | epic |
| [`R-01-backend-modelo-regras-roteamento.md`](R-01-backend-modelo-regras-roteamento.md) | Roteamento: modelo e CRUD de regras | backend |
| [`R-02-backend-motor-aplicacao-roteamento.md`](R-02-backend-motor-aplicacao-roteamento.md) | Roteamento: avaliação de regras (e-mail e ticket manual) | backend |
| [`R-03-frontend-crud-regras-roteamento.md`](R-03-frontend-crud-regras-roteamento.md) | Roteamento: UI admin de regras | frontend |

---

## Épico RT — Tempo real

| Arquivo | Título sugerido | Camada |
|---------|-----------------|--------|
| [`RT-epic-tempo-real.md`](RT-epic-tempo-real.md) | **[Épico] Eventos em tempo real (SSE)** | epic |
| [`RT-01-backend-infra-sse.md`](RT-01-backend-infra-sse.md) | Tempo real: infraestrutura SSE e autenticação | backend |
| [`RT-02-backend-eventos-tickets-chats.md`](RT-02-backend-eventos-tickets-chats.md) | Tempo real: eventos de tickets e chats WhatsApp | backend |
| [`RT-03-backend-eventos-notificacoes.md`](RT-03-backend-eventos-notificacoes.md) | Tempo real: eventos do sino de notificações | backend |
| [`RT-04-frontend-cliente-sse.md`](RT-04-frontend-cliente-sse.md) | Tempo real: hook/cliente SSE com fallback polling | frontend |
| [`RT-05-frontend-integracao-chat-sse.md`](RT-05-frontend-integracao-chat-sse.md) | Tempo real: conversa WhatsApp sem polling agressivo | frontend |
| [`RT-06-frontend-integracao-tickets-notificacoes-sse.md`](RT-06-frontend-integracao-tickets-notificacoes-sse.md) | Tempo real: detalhe ticket e NavbarNotificacoes | frontend |

---

## Épico KB — Base de conhecimento

| Arquivo | Título sugerido | Camada |
|---------|-----------------|--------|
| [`KB-epic-base-conhecimento.md`](KB-epic-base-conhecimento.md) | **[Épico] Base de conhecimento (interno + público)** | epic |
| [`KB-01-backend-modelo-artigos-categorias.md`](KB-01-backend-modelo-artigos-categorias.md) | KB: categorias, artigos, versões e publicação | backend |
| [`KB-02-backend-api-admin-artigos.md`](KB-02-backend-api-admin-artigos.md) | KB: API admin (CRUD, rascunho, publicar) | backend |
| [`KB-03-backend-api-publica-artigos.md`](KB-03-backend-api-publica-artigos.md) | KB: API pública de leitura (portal / link) | backend |
| [`KB-04-backend-vinculo-motivo-artigos.md`](KB-04-backend-vinculo-motivo-artigos.md) | KB: sugestão de artigos por natureza/motivo | backend |
| [`KB-05-frontend-editor-artigos-admin.md`](KB-05-frontend-editor-artigos-admin.md) | KB: editor de manuais para atendentes/admin | frontend |
| [`KB-06-frontend-gestao-categorias-admin.md`](KB-06-frontend-gestao-categorias-admin.md) | KB: gestão de categorias e ordem | frontend |
| [`KB-07-frontend-leitura-artigos-interno.md`](KB-07-frontend-leitura-artigos-interno.md) | KB: consulta rápida no painel interno (sidebar/modal) | frontend |

*Publicação no portal do cliente: issue [`P-09-frontend-kb-portal-cliente.md`](P-09-frontend-kb-portal-cliente.md) (depende do épico Portal).*

---

## Épico T — Distribuição automática de tickets

| Arquivo | Título sugerido | Camada |
|---------|-----------------|--------|
| [`T-epic-distribuicao-tickets.md`](T-epic-distribuicao-tickets.md) | **[Épico] Distribuição automática de tickets na fila** | epic |
| [`T-01-backend-config-setor-distribuicao.md`](T-01-backend-config-setor-distribuicao.md) | Distribuição: config por setor (modo, timeout, estratégia) | backend |
| [`T-02-backend-worker-atribuicao-automatica.md`](T-02-backend-worker-atribuicao-automatica.md) | Distribuição: worker de atribuição após timeout | backend |
| [`T-03-frontend-config-distribuicao-setor.md`](T-03-frontend-config-distribuicao-setor.md) | Distribuição: UI em configurações do setor | frontend |
| [`T-04-frontend-indicadores-fila-tickets.md`](T-04-frontend-indicadores-fila-tickets.md) | Distribuição: indicadores de tempo na fila sem responsável | frontend |

---

## Épico A — Auditoria

| Arquivo | Título sugerido | Camada |
|---------|-----------------|--------|
| [`A-epic-auditoria.md`](A-epic-auditoria.md) | **[Épico] Auditoria estruturada e rastreável** | epic |
| [`A-01-backend-audit-trail-expandido.md`](A-01-backend-audit-trail-expandido.md) | Auditoria: trail expandido (payload, IP, tickets/chats) | backend |
| [`A-02-backend-consulta-export-auditoria.md`](A-02-backend-consulta-export-auditoria.md) | Auditoria: filtros avançados e export | backend |
| [`A-03-frontend-auditoria-ui.md`](A-03-frontend-auditoria-ui.md) | Auditoria: UI com filtros, detalhe e paginação | frontend |

---

## Relacionamento com épicos existentes

| Épico existente | Issues desta pasta |
|-----------------|-------------------|
| [#16](https://github.com/lgustavoss/dx-connect/issues/16) melhorias operacionais | D, S, R, T, RT, A |
| [#162](https://github.com/lgustavoss/dx-connect/issues/162) e-mail SaaS | R (roteamento inbound complementa) |
| Portal futuro | P, KB-03, KB-07, P-09 |
