# Integração WhatsApp — Evolution API (v1)

Este documento descreve como o **DX Connect** integra com a [Evolution API](https://doc.evolution-api.com/) na v1 do módulo de chats.

**Não existe cadastro obrigatório** num site da Evolution: o projeto é [open source](https://github.com/EvolutionAPI/evolution-api) e a API corre no teu ambiente (ex.: Docker). Os links oficiais ([introdução v2](https://doc.evolution-api.com/v2/pt/get-started/introduction), [GitHub](https://github.com/EvolutionAPI/evolution-api)) servem para documentação e instalação, não para “ativar” uma conta.

## Início rápido (Docker Compose do repositório)

O `docker-compose.yml` na raiz já inclui **Evolution API** (`evolution-api`), **Redis** e **PostgreSQL** dedicados à Evolution, além do **backend** com variáveis para o modo embutido.

1. Na raiz do projeto: `docker compose up -d --build` (sobe `db`, `evolution-*`, `backend`).
2. A API Evolution fica em `http://localhost:8080` (útil para diagnóstico).
3. No DX Connect, como **admin**: **Configurações → WhatsApp (Evolution)**.
4. Em **Configurações → WhatsApp · Evolution API**, clique em **Preparar e mostrar QR Code**. O sistema cria a instância, regista o webhook em `http://backend:8000/v1/webhooks/evolution` (rede Docker) e mostra o QR.
5. No telemóvel: **WhatsApp → Aparelhos ligados → Ligar um aparelho** e leia o QR.
6. Mensagens de teste devem aparecer em **Chats WhatsApp**.

**Produção:** altere `AUTHENTICATION_API_KEY` da Evolution e as passwords do Postgres da Evolution; defina `DX_CONNECT_WEBHOOK_BASE_URL` com a URL **interna ou pública** que a Evolution consiga chamar (ex.: URL da API atrás do reverse proxy). O modo simples assume a mesma API key global na Evolution e no backend (`EVOLUTION_GLOBAL_API_KEY` no compose). O compose do repositório define `AUTHENTICATION_EXPOSE_IN_FETCH_INSTANCES=true` para o endpoint `fetchInstances` poder devolver a `apikey` por instância quando a resposta do `create` não incluir `hash`; se estiver `false`, o DX Connect usa a mesma API key global nas chamadas `connect` / envio, que a Evolution aceita quando a autenticação é por `apikey`.

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

   - `messages.upsert` — mensagens recebidas/enviadas; o backend **persiste apenas mensagens recebidas do cliente** (`fromMe === false`). **Texto** (`conversation` / `extendedTextMessage`) e **mídia** (imagem, áudio, vídeo, documento, figurinha): o ficheiro é obtido via `POST /chat/getBase64FromMediaMessage/{instance}` na Evolution e guardado em disco (`WHATSAPP_MEDIA_DIR`); a UI do DX Connect pré-visualiza ou permite descarregar.

3. **Idempotência:** uso do identificador da mensagem na origem (`key.id` no payload Baileys-like) na coluna `wa_message_id` (único).

4. **Segurança:** se `webhook_secret` estiver preenchido nas settings, o pedido deve enviar o mesmo valor em `X-Dx-Webhook-Secret` ou `apikey` (útil se a Evolution só permitir o header `apikey`). Se o segredo estiver vazio (ex.: dev), o webhook aceita sem validação — **não usar assim em produção**.

5. **Mídia inbound (Evolution):** o download via `getBase64FromMediaMessage` exige que a Evolution **persista mensagens** na base de dados. Defina pelo menos:

   ```env
   DATABASE_ENABLED=true
   DATABASE_SAVE_DATA_INSTANCE=true
   DATABASE_SAVE_DATA_NEW_MESSAGE=true
   ```

   Sem isto, o webhook recebe o evento mas a Evolution responde «Message not found» ao pedir o base64. Garanta também volume/gravação em `WHATSAPP_MEDIA_DIR` no backend e que URL/API key da instância estão corretos no painel.

## Envio (DX Connect → Evolution)

- Endpoint típico Evolution v2: `POST {base}/message/sendText/{instance}` com JSON `{ "number": "<DDI+DDD+número>", "text": "..." }` e header `apikey`.
- **Áudio outbound (#441):** notas de voz usam `POST {base}/message/sendWhatsAppAudio/{instance}` com `{ "number", "audio": "<base64>", "encoding": true }` — a Evolution converte para Ogg Opus compatível com WhatsApp (não usar `sendMedia` com `audio/webm` do browser).
- **Figurinha outbound (#443):** `POST {base}/message/sendSticker/{instance}` com `{ "number", "sticker": "<base64>" }` (WebP/PNG).
- O número do cliente é normalizado a dígitos (ex.: `5511999999999`).

## Ciclo de vida do chat

1. Primeira mensagem inbound de um `wa_id` → cria **chat** em `aguardando_atendente` com protocolo `#CYYYYMM-NNNN` (mensal, distinto dos tickets `#T…`; chats antigos podem manter `WCH-*`).
2. Atendente **assume** → `em_atendimento`, `atendimento_inicio_at`.
3. **Encerrar** → `encerrado`, `encerramento_at`.
4. Nova mensagem do mesmo cliente **após encerramento** → **novo** chat e novo protocolo.

## Reações, editar e apagar (#630)

| Ação | Endpoint Evolution (v2 típico) | Limite no DX Connect |
|------|-------------------------------|----------------------|
| Reagir | `POST /message/sendReaction/{instance}` | Whitelist 👍❤️😂😮😢🙏; só responsável do chat |
| Editar texto | `POST /chat/updateMessage/{instance}` | Só outbound texto; **15 minutos** após envio |
| Apagar para todos | `DELETE /chat/deleteMessageForEveryone/{instance}` | Só outbound; **48 horas** após envio |

- Webhook inbound: `reactionMessage`, `protocolMessage` tipo `REVOKE`, e `editedMessage` atualizam a mensagem e emitem SSE `chat.mensagem`.
- Editar legenda de mídia fica fora do escopo v1.
- O prefixo de assinatura `[ Setor - Nome ]:` é reaplicado ao editar (ver #628).

## Riscos e limitações

- Comportamento e payloads podem variar entre **versões** da Evolution; ajustar o parser em `app/services/evolution_inbound.py` ou a chamada a `getBase64FromMediaMessage` se necessário.
- Políticas e limitações do **WhatsApp** aplicam-se ao número conectado na Evolution (janelas de edição/apagamento podem ser mais restritas que as do DX Connect).
- **Localização** e **templates** não são tratados nesta versão.
- Ficheiros muito grandes respeitam `WHATSAPP_MEDIA_MAX_BYTES` (por defeito 25 MB).
- **Contacto** e **localização** inbound aparecem como texto legível (`[Contacto]`, `[Localização]` + link Google Maps).
- Grupos (`@g.us`) continuam ignorados.

## Referências úteis

- Documentação oficial: https://doc.evolution-api.com/
- Issues de produto: #70–#76 (GitHub).
