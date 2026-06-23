## Contexto

No WhatsApp, o atendimento é **síncrono**: o operador resolve um ou mais assuntos **dentro da conversa** e só abre ticket quando não é possível concluir na sessão.

Hoje registramos mensagens, estados do chat, vínculos chat↔ticket e métricas agregadas (TMA, espera, % com ticket). **Não há registro estruturado** de quantos e quais problemas foram tratados/resolvidos na sessão — apenas o transcript, difícil de agregar para gestão.

Decisão de produto (2026-06): complementar o chat com **mapeamento de demandas da sessão**, separado de SLA (#419) e de ticket assíncrono. Análise: `.github/planning-issue-bodies/analises/filas-tickets-vs-chats.md`.

## Objetivo

Permitir que o atendente registre **itens de demanda** por sessão de chat, para análise operacional e comercial:

- Muitas **dúvidas** → oportunidade de treinamento
- Muitos **erros** → revisar versão/atualização ou bug recorrente
- Muitas **solicitações** → demanda de serviço/configuração
- Alto volume de itens ou escalonamentos → revisar processo ou perfil do cliente

## Proposta (v1)

### Modelo de dados

Tabela `whatsapp_chat_demandas` (nome técnico a definir na implementação):

| Campo | Descrição |
|-------|-----------|
| `chat_id` | Sessão WhatsApp |
| `natureza_id` | Reutilizar `ticket_naturezas` (Erro, Dúvida, Solicitação) |
| `motivo_id` | Opcional — reutilizar `ticket_motivos` |
| `desfecho` | `resolvido_sessao` \| `escalado_ticket` |
| `ticket_id` | Preenchido quando escalado (vínculo existente) |
| `descricao_curta` | Opcional, texto livre curto |
| `atendente_id`, `created_at` | Auditoria |

Um chat pode ter **N demandas** (ex.: 3 dúvidas + 1 erro resolvido na mesma sessão).

### UX (chat)

- Ação **«+ Registrar demanda»** durante `em_atendimento` (2 cliques: natureza + motivo opcional)
- Ao **abrir ticket** a partir do chat: criar item automaticamente com `desfecho=escalado_ticket` (evitar duplicar trabalho)
- Ao **encerrar**: exibir resumo dos itens da sessão; lembrete leve se zero itens *(não bloquear encerramento no v1)*

### API / relatório

- CRUD dos itens por `chat_id` (RBAC setor/responsável como demais endpoints de chat)
- Endpoint agregado ou extensão do dashboard de chats: contagem por natureza/motivo por **empresa/rede/funcionário** e período
- Export CSV alinhado aos relatórios existentes (#286 / dashboard chats)

### Fora de escopo v1

- Inferência automática por NLP/IA no transcript (v2 — sugestão para confirmar)
- SLA formal de chat (#419)
- Unificação de filas ticket+chat

## Critérios de aceite

- [ ] Atendente registra demanda resolvida na sessão com natureza (+ motivo opcional)
- [ ] Abrir ticket a partir do chat gera item escalado vinculado ao ticket
- [ ] Lista/resumo visível no detalhe do chat (itens da sessão)
- [ ] Relatório ou dashboard: totais por natureza/motivo filtráveis por rede/empresa e período
- [ ] RBAC: mesmas regras de visibilidade do chat; admin vê agregados globais
- [ ] Testes backend (CRUD + agregação); smoke UI no fluxo de registro

## Dependências

- Catálogo natureza/motivo (#036 / config existente)
- Vínculo chat↔ticket (`WhatsappChatTicket`, `POST .../abrir-ticket`)
- Dashboard chats (#284 / `dashboard_chats.py`) — extensão natural para v1

## Relacionado

- #419 — SLA WhatsApp (tempo de fila/resposta; ortogonal a este item)
- #416 — SLA tickets no dashboard geral
- #403 — restrição admin/comentário interno no chat

## Origem

Discussão de produto pós-épico SLA (#259) — necessidade de inteligência operacional sobre **conteúdo** do atendimento WhatsApp, não apenas tempo de resposta.
