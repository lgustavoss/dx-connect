# Integração WhatsApp — Evolution API (v1)

Este documento descreve como o **DX Connect** integra com a [Evolution API](https://doc.evolution-api.com/) na v1 do módulo de chats.

## Decisão

- **Provedor:** Evolution API (instância própria ou gerida pelo time).
- **Fluxo:** Evolution recebe/envia mensagens ao WhatsApp; o DX Connect recebe **webhooks** HTTP e chama a **REST** da Evolution para enviar texto.

## Variáveis e configuração no painel

Campos persistidos em `whatsapp_settings` (via **Configurações → WhatsApp**, admin):

| Campo | Descrição |
|--------|-----------|
| URL base | Origem da API Evolution, sem barra final (ex.: `https://evolution.exemplo.com`). |
| Nome da instância | Instância criada na Evolution (path em vários endpoints). |
| API key | Cabeçalho `apikey` nas chamadas à Evolution. **Nunca** é devolvida em GET; apenas `has_api_key`. |
| Segredo do webhook | Valor esperado no header `X-Dx-Webhook-Secret` (ou `apikey`) nas chamadas **de entrada** à rota de webhook do DX Connect. Recomendado em produção. |

## Webhook (Evolution → DX Connect)

1. Na Evolution, configure o webhook apontando para:

   `POST https://<sua-api>/v1/webhooks/evolution`

2. Eventos tratados na v1 (extensível depois):

   - `messages.upsert` — mensagens recebidas/enviadas; o backend **persiste apenas mensagens recebidas do cliente** (`fromMe === false`), texto simples (`conversation` ou `extendedTextMessage.text`).

3. **Idempotência:** uso do identificador da mensagem na origem (`key.id` no payload Baileys-like) na coluna `wa_message_id` (único).

4. **Segurança:** se `webhook_secret` estiver preenchido nas settings, o pedido deve enviar o mesmo valor em `X-Dx-Webhook-Secret` ou `apikey` (útil se a Evolution só permitir o header `apikey`). Se o segredo estiver vazio (ex.: dev), o webhook aceita sem validação — **não usar assim em produção**.

## Envio (DX Connect → Evolution)

- Endpoint típico Evolution v2: `POST {base}/message/sendText/{instance}` com JSON `{ "number": "<DDI+DDD+número>", "text": "..." }` e header `apikey`.
- O número do cliente é normalizado a dígitos (ex.: `5511999999999`).

## Ciclo de vida do chat

1. Primeira mensagem inbound de um `wa_id` → cria **chat** em `aguardando_atendente` com protocolo `WCH-*` (numerador distinto dos tickets).
2. Atendente **assume** → `em_atendimento`, `atendimento_inicio_at`.
3. **Encerrar** → `encerrado`, `encerramento_at`.
4. Nova mensagem do mesmo cliente **após encerramento** → **novo** chat e novo protocolo.

## Riscos e limitações

- Comportamento e payloads podem variar entre **versões** da Evolution; ajustar o parser em `app/api/whatsapp_webhook.py` se necessário.
- Políticas e limitações do **WhatsApp** aplicam-se ao número conectado na Evolution.
- Mídia, localização e templates não fazem parte da v1 descrita aqui.

## Referências úteis

- Documentação oficial: https://doc.evolution-api.com/
- Issues de produto: #70–#76 (GitHub).
