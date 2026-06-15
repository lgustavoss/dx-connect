# Análise: filas separadas (tickets vs chats) vs inbox unificada

## Decisão do time (registrar)

O DX Connect **mantém filas separadas**:

- **Chats WhatsApp** — prioridade operacional; alerta contínuo até um atendente assumir; atendimento síncrono.
- **Tickets** — demanda assíncrona; o atendente resolve quando não está em chat.

**Não implementar** inbox omnichannel unificada no curto/médio prazo.

## Por que a sugestão de unificação apareceu

Em helpdesks genéricos (Zendesk, Intercom), uma única fila reduz troca de contexto. No DX Connect, o WhatsApp já tem UX e SLA operacional distintos (som, fila `aguardando_atendente`, assume/encerra). Unificar poderia:

- Diluir a prioridade do chat
- Misturar métricas incompatíveis (TMA de chat vs MTTR de ticket)
- Complicar RBAC (setor de ticket vs fila global de chat)

## Alternativa recomendada (sem unificar)

Melhorar a **coordenação entre filas**, não fundi-las:

| Melhoria | Issue relacionada |
|----------|-------------------|
| Tempo real no chat e notificações | RT-* |
| Badge global no header (já existe parcialmente) | RT-06 |
| Atalho «Abrir ticket a partir do chat» (já existe #98) | — |
| Dashboard separado por canal | D-* |
| Distribuição automática **só tickets** | T-* |

## Quando reavaliar unificação

- Se atendentes reportarem perda sistemática de chats por excesso de navegação entre telas
- Se surgir canal adicional (ex.: chat web no portal) com mesma semântica de chat WhatsApp

Até lá: **duas filas, uma prioridade clara (chat > ticket quando em plantão)**.
