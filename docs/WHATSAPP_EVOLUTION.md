# Integração WhatsApp — Evolution API e chats no DX Connect

Este documento junta **infraestrutura Evolution**, **webhook**, **API REST do backend** e um **guia para o frontend** consumir chats, texto, mídia e respostas citadas (reply).

**Não existe cadastro obrigatório** num site da Evolution: o projeto é [open source](https://github.com/EvolutionAPI/evolution-api) e a API corre no teu ambiente (ex.: Docker). Os links oficiais ([introdução v2](https://doc.evolution-api.com/v2/pt/get-started/introduction), [GitHub](https://github.com/EvolutionAPI/evolution-api)) servem para documentação e instalação, não para “ativar” uma conta.

## Índice

1. [Decisão de arquitetura](#decisão)
2. [Início rápido (Docker Compose)](#início-rápido-docker-compose-do-repositório)
3. [Variáveis e configuração no painel](#variáveis-e-configuração-no-painel)
4. [Webhook (Evolution para o DX Connect)](#webhook-evolution-para-o-dx-connect)
5. [Envio (DX Connect para a Evolution)](#envio-dx-connect-para-a-evolution)
6. [Ciclo de vida do chat](#ciclo-de-vida-do-chat)
7. [API REST do DX Connect (chats)](#api-rest-do-dx-connect-chats)
8. [API REST (configurações WhatsApp, admin)](#api-rest-configurações-whatsapp-admin)
9. [Guia para desenvolvimento frontend](#guia-para-desenvolvimento-frontend)
10. [Riscos e limitações](#riscos-e-limitações)
11. [Referências úteis](#referências-úteis)

---

## Decisão

- **Provedor:** Evolution API (instância própria ou gerida pelo time).
- **Fluxo:** Evolution recebe/envia mensagens ao WhatsApp; o DX Connect recebe **webhooks** HTTP e chama a **REST** da Evolution para enviar **texto** e **mídia** (com citação opcional).

---

## Início rápido (Docker Compose do repositório)

O `docker-compose.yml` na raiz já inclui **Evolution API** (`evolution-api`), **Redis** e **PostgreSQL** dedicados à Evolution, além do **backend** com variáveis para o modo embutido.

1. Na raiz do projeto: `docker compose up -d --build` (sobe `db`, `evolution-*`, `backend`).
2. A API Evolution fica em `http://localhost:8080` (útil para diagnóstico).
3. No DX Connect, como **admin**: **Configurações → WhatsApp (Evolution)**.
4. Em **Configurações → WhatsApp · Evolution API**, clique em **Preparar e mostrar QR Code**. O sistema cria a instância, regista o webhook em `http://backend:8000/v1/webhooks/evolution` (rede Docker) e mostra o QR.
5. No telemóvel: **WhatsApp → Aparelhos ligados → Ligar um aparelho** e leia o QR.
6. Mensagens de teste devem aparecer em **Chats WhatsApp**.

**Produção:** altere `AUTHENTICATION_API_KEY` da Evolution e as passwords do Postgres da Evolution; defina `DX_CONNECT_WEBHOOK_BASE_URL` com a URL **interna ou pública** que a Evolution consiga chamar (ex.: URL da API atrás do reverse proxy). O modo simples assume a mesma API key global na Evolution e no backend (`EVOLUTION_GLOBAL_API_KEY` no compose). O compose do repositório define `AUTHENTICATION_EXPOSE_IN_FETCH_INSTANCES=true` para o endpoint `fetchInstances` poder devolver a `apikey` por instância quando a resposta do `create` não incluir `hash`; se estiver `false`, o DX Connect usa a mesma API key global nas chamadas `connect` / envio, que a Evolution aceita quando a autenticação é por `apikey`.

---

## Variáveis e configuração no painel

Campos persistidos em `whatsapp_settings` (via **Configurações → WhatsApp**, admin):

| Campo | Descrição |
|--------|-----------|
| URL base | Origem da API Evolution, sem barra final (ex.: `https://evolution.exemplo.com`). |
| Nome da instância | Instância criada na Evolution (path em vários endpoints). |
| API key | Cabeçalho `apikey` nas chamadas à Evolution. **Nunca** é devolvida em GET; apenas `has_api_key`. |
| Segredo do webhook | Valor esperado no header `X-Dx-Webhook-Secret` (ou `apikey`) nas chamadas **de entrada** à rota de webhook do DX Connect. Recomendado em produção. |

---

## Webhook (Evolution para o DX Connect)

1. Na Evolution, configure o webhook apontando para:

   `POST https://<sua-api>/v1/webhooks/evolution`

2. Eventos tratados na v1 (extensível depois):

   - `messages.upsert` — mensagens recebidas/enviadas; o backend **persiste apenas mensagens recebidas do cliente** (`fromMe === false`). **Texto** (`conversation` / `extendedTextMessage`) e **mídia** (imagem, áudio, vídeo, documento, figurinha): o ficheiro é obtido via `POST /chat/getBase64FromMediaMessage/{instance}` na Evolution e guardado em disco (`WHATSAPP_MEDIA_DIR`); a UI do DX Connect pré-visualiza ou permite descarregar.
   - Mensagens de **resposta citada** (reply no WhatsApp): o payload pode trazer `contextInfo` / `quotedMessage`; o backend extrai o id da mensagem referida e grava em `quoted_wa_message_id` e um resumo em `quoted_corpo_preview` na tabela `whatsapp_mensagens`.

3. **Idempotência:** uso do identificador da mensagem na origem (`key.id` no payload Baileys-like) na coluna `wa_message_id` (único).

4. **Segurança:** se `webhook_secret` estiver preenchido nas settings, o pedido deve enviar o mesmo valor em `X-Dx-Webhook-Secret` ou `apikey` (útil se a Evolution só permitir o header `apikey`). Se o segredo estiver vazio (ex.: dev), o webhook aceita sem validação — **não usar assim em produção**.

---

## Envio (DX Connect para a Evolution)

- **Texto:** `POST {base}/message/sendText/{instance}` com JSON que inclui `number` e `text`; opcionalmente objeto de **citação** (`quoted`) quando o atendente responde a uma mensagem conhecida.
- **Mídia:** envio em base64 via endpoint de mídia da Evolution (implementado em `evolution_send_media`), com `mediatype`, `mimetype`, `caption`, ficheiro em base64 e **citação opcional** no mesmo formato que o texto.
- O número do cliente é normalizado a dígitos (ex.: `5511999999999`).

*(Os detalhes de payload seguem a documentação da versão da Evolution em uso; o backend encapsula isto em `app/services/evolution_api.py`.)*

---

## Ciclo de vida do chat

1. Primeira mensagem inbound de um `wa_id` → cria **chat** em `aguardando_atendente` com protocolo `WCH-*` (numerador distinto dos tickets).
2. Atendente **assume** → `em_atendimento`, `atendimento_inicio_at`.
3. **Encerrar** → `encerrado`, `encerramento_at`.
4. Nova mensagem do mesmo cliente **após encerramento** → **novo** chat e novo protocolo.

---

## API REST do DX Connect (chats)

Todas as rotas abaixo exigem **JWT de atendente autenticado** (`Authorization: Bearer <access_token>`), salvo indicação em contrário.

**Prefixo:** `/v1/whatsapp/chats`

| Método | Caminho | Descrição |
|--------|---------|-----------|
| `GET` | `/transfer/setores` | Lista setores ativos (transferência). |
| `GET` | `/fila` | Chats em `aguardando_atendente` (visível conforme setor). |
| `GET` | `/meus` | Chats em `em_atendimento` do atendente atual. |
| `GET` | `/encerrados` | Chats encerrados (paginação: `offset`, `limit`). |
| `GET` | `/por-ticket/{ticket_id}` | Chats vinculados a um ticket. |
| `GET` | `/{chat_id}` | Detalhe de um chat. |
| `GET` | `/{chat_id}/mensagens` | Lista de mensagens (ordenadas por data). |
| `GET` | `/{chat_id}/mensagens/{mensagem_id}/midia` | Binário da mídia (JWT obrigatório). |
| `POST` | `/{chat_id}/assumir` | Assume o chat (fila → em atendimento). |
| `POST` | `/{chat_id}/encerrar` | Encerra o chat. |
| `POST` | `/{chat_id}/mensagens` | Envia **texto** (JSON). |
| `POST` | `/{chat_id}/mensagens/midia` | Envia **ficheiro** (`multipart/form-data`). |
| `POST` | `/{chat_id}/comentarios-internos` | Comentário interno (não vai ao WhatsApp). |
| `POST` | `/{chat_id}/visto` | Marca conversa como vista (204). |
| `POST` | `/{chat_id}/vincular-ticket` | Vincula a um ticket existente. |
| `POST` | `/{chat_id}/abrir-ticket` | Abre ticket a partir do chat. |
| `POST` | `/{chat_id}/transferir` | Transfere setor/atendente. |

**Regras comuns de envio (texto e mídia):**

- Chat em estado **`em_atendimento`**.
- Utilizador **admin** ou **atendente responsável** (`chat.atendente_id` = id do token).
- **403** se o chat for de um setor que o atendente não vê (exceto fluxos onde só admin atua).

---

## API REST (configurações WhatsApp, admin)

**Prefixo:** `/v1/settings/whatsapp`

Rotas para ler/atualizar settings, testar ligação, preparar QR, etc. Aplicável a **admin** (ver `whatsapp_settings` router). O frontend de **Configurações → WhatsApp** consome estas rotas.

---

## Guia para desenvolvimento frontend

### 1. Base URL e autenticação

- Em **desenvolvimento**, o Vite costuma proxyar para `/api`; o cliente usa `BASE` + `API_VERSION_PREFIX` (`/v1`) — ver `frontend/src/api/client.ts`.
- Em **produção**, define-se `VITE_API_URL` (URL pública da API, sem barra final duplicada).
- Todas as chamadas autenticadas devem enviar **`Authorization: Bearer <token>`** (o helper `api()` no `client.ts` já faz isso). Para **`multipart/form-data`**, usar `fetch` manual com o mesmo header e **sem** definir `Content-Type` (o browser define `boundary`).

### 2. Fluxo obrigatório do atendente (enviar mensagem ou mídia)

1. Obter lista (**fila** ou **meus**) e abrir o detalhe `GET /whatsapp/chats/{id}` se necessário.
2. Se o chat estiver na **fila**, chamar **`POST .../assumir`** antes de enviar.
3. Carregar mensagens: **`GET .../{chat_id}/mensagens`**.
4. Só então **`POST .../mensagens`** (texto) ou **`POST .../mensagens/midia`** (ficheiro).

Sem assumir, o chat pode continuar `aguardando_atendente` e o envio devolve **400** (“Só é possível enviar mensagens em chats ativos”).

### 3. Modelo de mensagem na UI (`WhatsappChats.Mensagem`)

Campos relevantes para conversação:

| Campo | Uso na UI |
|--------|-----------|
| `direcao` | `inbound` (cliente) vs `outbound` (equipa). |
| `corpo` | Texto ou legenda composta (ex.: prefixo com nome do atendente em mídia). |
| `tipo_midia` | `texto`, `imagem`, `video`, `audio`, `documento`, etc. |
| `midia_disponivel` | Se `true`, existe ficheiro para ir buscar ao endpoint de mídia. |
| `wa_message_id` | Id estável no WhatsApp — **necessário** para “citar esta mensagem” no envio. |
| `quoted_wa_message_id` | Id da mensagem **referida** (reply). |
| `quoted_corpo_preview` | Texto curto para mostrar na faixa de citação. |
| `evento_sistema` | Mensagens automáticas do sistema (tratar visualmente à parte, se aplicável). |
| `atendente_nome` | Quem enviou (outbound humano). |

### 4. Enviar texto

- **Rota:** `POST /v1/whatsapp/chats/{chatId}/mensagens`
- **Corpo JSON:**

```json
{
  "texto": "Olá, em que podemos ajudar?",
  "quoted_wa_message_id": "ABC123OPTIONAL"
}
```

- Omitir `quoted_wa_message_id` se não for reply.
- No código: `whatsappChats.enviar(chatId, { texto, quoted_wa_message_id? })`.

### 5. Enviar mídia (multipart)

- **Rota:** `POST /v1/whatsapp/chats/{chatId}/mensagens/midia`
- **Content-Type:** `multipart/form-data`
- **Campos:**

| Campo | Obrigatório | Valores / notas |
|--------|-------------|-----------------|
| `file` | Sim | `File` / binário. |
| `mediatipo` | Sim | `imagem`, `video`, `audio`, `documento` (literais em português, como na API). |
| `caption` | Não | Legenda; pode ser string vazia. |
| `quoted_wa_message_id` | Não | Mesmo significado que no JSON de texto. |

- **Mapeamento sugerido** a partir de `File.type`: `image/*` → `imagem`, `video/*` → `video`, `audio/*` → `audio`, caso contrário → `documento`.
- **No código:** `uploadWhatsAppMidia(chatId, formData)` em `client.ts`.
- **413** se o ficheiro exceder `WHATSAPP_MEDIA_MAX_BYTES` (configuração do servidor).

### 6. Respostas citadas (“marcar” / reply)

- Conceito alinhado ao **WhatsApp reply**: envia-se o **`wa_message_id`** da mensagem a que se responde.
- **Pré-condição:** a mensagem citada deve existir na conversa e, na prática, ter **`wa_message_id` preenchido**. Mensagens outbound muito recentes podem ainda não ter id até sincronização — desativar “citar” quando `wa_message_id` for `null` evita erros confusos.
- **Texto:** incluir `quoted_wa_message_id` no JSON de `POST .../mensagens`.
- **Mídia:** acrescentar o mesmo campo no `FormData` do `POST .../mensagens/midia`.

### 7. Exibir mensagens com citação

- Se `quoted_wa_message_id` ou `quoted_corpo_preview` estiver presente, renderizar um **bloco de citação** acima do corpo/mídia (padrão tipo WhatsApp).
- **Opcional:** percorrer a lista já carregada e, se existir mensagem com `wa_message_id === quoted_wa_message_id`, ao clicar na citação fazer **scroll** até essa mensagem.

### 8. Exibir e descarregar mídia

- Não colocar o URL do GET de mídia diretamente em `<img src>` sem token; usar **`GET .../mensagens/{id}/midia`** com cabeçalho de autorização, obter `Blob` e **`URL.createObjectURL`** (ver `fetchWhatsAppMidiaBlob` e o componente de mensagem em `WhatsappConversa.tsx`).

### 9. “Marcar como visto” vs “citar mensagem”

- **`POST .../visto`:** estado de leitura do chat (não confundir com reply).
- **Citação:** campos `quoted_*` e `quoted_wa_message_id` no envio.

### 10. Referência de implementação no repositório

| Área | Ficheiro |
|------|----------|
| Cliente HTTP, tipos, upload | `frontend/src/api/client.ts` |
| Ecrã conversa (citar, enviar, mídia) | `frontend/src/pages/whatsapp/WhatsappConversa.tsx` |
| Fila / atendimento | `frontend/src/pages/whatsapp/WhatsappAtendendo.tsx` |
| Rotas backend | `backend/app/api/whatsapp_chats.py` |
| Parser inbound + citação | `backend/app/services/evolution_inbound.py`, `whatsapp_webhook.py` |

### 11. Checklist rápido para nova feature na UI

- [ ] Chat assumido e `estado === 'em_atendimento'` antes de enviar texto/mídia (ou tratar 400/403 com mensagem clara).
- [ ] Texto: JSON com `texto` e opcionalmente `quoted_wa_message_id`.
- [ ] Mídia: `FormData` com `file` + `mediatipo` + opcionais `caption`, `quoted_wa_message_id`.
- [ ] Listagem: mostrar `quoted_corpo_preview` / ligação a `wa_message_id`.
- [ ] Mídia inbound/outbound: `fetchWhatsAppMidiaBlob` + object URL, com revogação ao desmontar componente.

---

## Riscos e limitações

- Comportamento e payloads podem variar entre **versões** da Evolution; ajustar o parser em `app/services/evolution_inbound.py` ou as chamadas em `evolution_api.py` se necessário.
- Políticas e limitações do **WhatsApp** aplicam-se ao número conectado na Evolution.
- **Localização** e **templates** não são tratados nesta versão.
- Ficheiros muito grandes respeitam `WHATSAPP_MEDIA_MAX_BYTES` (por defeito 25 MB); mensagens de contacto / localização não são mapeadas.
- **Reply:** depende de `wa_message_id` consistente na conversa; edge cases de mensagens ainda sem id devem ser tratados na UX.

---

## Referências úteis

- Documentação oficial Evolution: https://doc.evolution-api.com/
- Issues de produto (GitHub): #70–#76, citação/mídia/reply: **#78**.
