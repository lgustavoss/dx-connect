# Dashboard chats — endpoints de métricas WhatsApp (backend)

## Contexto

Épico: **Dashboards e relatórios**. Visão analítica do canal WhatsApp.

Parte de: **D-F3**

## Proposta

`GET /v1/dashboard/chats?de=&ate=`:

| Métrica | Descrição |
|---------|-----------|
| Chats por dia | Abertos, encerrados |
| Tempo médio de espera | `aguardando_atendente` → assume |
| Tempo médio de atendimento | assume → encerra |
| Avaliações | Média 1–5, distribuição |
| Encerramentos por inatividade vs manual |
| Chats com ticket vinculado | % |
| Por atendente | Volume assumido (admin) |

## Critérios de aceite

- [ ] Usa timestamps existentes (`atendimento_inicio_at`, `encerramento_at`)
- [ ] Atendente vê métricas dos próprios chats + fila setor (definir política)
- [ ] Admin vê global

## Dependências

- Paralelo: D-07

## Labels

`backend`, `dashboard`, `fase-interna`, `whatsapp`
