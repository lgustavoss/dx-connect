# [Épico] Chat interno entre atendentes e comunicados por setor

## Contexto

Hoje a comunicação entre a equipe no DX Connect passa por **comentários em tickets** ou **WhatsApp com o cliente**. Falta um canal **interno** para:

1. **Chat direto** — conversa 1:1 entre atendentes (dúvidas rápidas, handoff informal).
2. **Canal do setor** — avisos e comunicados broadcast para todos os **atendentes vinculados** ao setor (`atendente_setor`), com notificação in-app e leitura individual.

> **Não confundir** com chat WhatsApp (#76) nem com mensagens públicas do ticket. Alinha-se ao princípio de atendimento humano (#122): ferramenta para **operadores**, não bot para o cliente.

## Objetivo

| Tipo | Quem vê | Quem publica (v1) | Notificação |
|------|---------|-------------------|-------------|
| **Direta** | Os 2 atendentes da conversa | Qualquer participante | In-app + SSE |
| **Canal setor** | Atendentes vinculados ao setor | Admin ou membro do setor | In-app + SSE para todos os membros |

Reutilizar infraestrutura existente:

- Auth/RBAC e escopo por setor (`docs/BACKEND_RBAC.md`, `setor_scope`)
- Contadores e sino em `/notificacoes` (#109)
- SSE por atendente (`GET /v1/events/stream`, #264–#269)

## Fases

| Fase | Issues | Entrega |
|------|--------|---------|
| **IC-F1** | IC-01, IC-02 | Modelo + API (direta e canal) |
| **IC-F2** | IC-03 | Notificações, leitura e SSE |
| **IC-F3** | IC-04, IC-05 | UI inbox, thread e canal do setor |

## Fora de escopo (v1)

- Grupos customizados além do vínculo setor↔atendente
- Anexos, reações, edição/exclusão de mensagem
- E-mail push de mensagem interna (pode seguir preferências #109 em v2)
- Chat com **funcionários da rede** (portal cliente — épico P)

## Labels

`epic`, `chat-interno`, `fase-interna`
