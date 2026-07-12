## Contexto

Follow-up pós-épico **Chat interno** (#478).

O épico definiu **fora de escopo v1**: anexos, reações, edição/exclusão de mensagem. A UI do composer (`ChatInternoComposerBar`) já expõe botões de anexo e áudio no estilo WhatsApp Web, mas exibe toast *«será disponibilizado em breve»* até existir API.

Hoje `mensagem_interna` só tem `corpo` (texto). Não há storage nem endpoints de mídia para chat interno.

## Proposta

### Backend

- Estender modelo de mensagem com tipo de conteúdo, por exemplo:
  - `tipo`: `texto` | `imagem` | `video` | `audio` | `documento`
  - Campos de mídia: `mimetype`, `nome_arquivo`, `tamanho_bytes`, `storage_key` (ou equivalente)
  - `corpo` opcional como legenda/caption (como WhatsApp)
- Migration Alembic + índices
- Diretório de storage dedicado (ex.: `data/chat_interno_anexos/`), limites de tamanho e tipos MIME permitidos (alinhar a tickets/WhatsApp onde fizer sentido)
- Endpoints em `/v1/chat-interno`:
  - `POST /conversas/{id}/mensagens/midia` (multipart) — RBAC: participante da conversa
  - `GET /conversas/{id}/mensagens/{msg_id}/download` — mesmo escopo
- SSE `chat.interno.mensagem` incluir metadados de mídia no payload
- Testes: upload, download 403 fora do escopo, tipos inválidos, tamanho excedido

### Frontend

- Conectar `ChatInternoComposerBar` ao upload real (reutilizar padrões de `WhatsappComposerBar` / `enviarMidia`)
- Pré-visualização no thread: imagem inline, documento com nome + download, player de áudio/vídeo
- Remover toasts «em breve» dos botões de anexo/áudio quando a API existir
- Gravação de áudio inline (opcional nesta issue; pode ser fase 2 se preferir escopo menor)

## Critérios de aceite

- [ ] Atendente participante envia imagem, documento, áudio e vídeo em conversa direta
- [ ] Membro do setor envia mídia no canal do setor (mesmas regras de publicação v1)
- [ ] Atendente fora da conversa recebe 403 no upload/download
- [ ] Thread renderiza mídia sem barra de rolagem horizontal indevida
- [ ] SSE atualiza inbox/thread para mensagens de mídia
- [ ] Testes backend passando; build frontend ok

## Dependências

- Requer épico #478 mergeado (IC-F1–F3: #479–#483)

## Fora de escopo (esta issue)

- Reações, edição/exclusão de mensagem
- Figurinhas/stickers
- E-mail push de notificação de anexo

## Origem

Fora de escopo v1 do épico #478 — identificado na entrega da UI estilo WhatsApp Web (composer com anexos desabilitados).

---

**Rascunho:** `.github/planning-issue-bodies/followups/IC-chat-interno-anexos-midia.md`
**Épico pai:** #478
