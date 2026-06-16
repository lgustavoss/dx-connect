# Tempo real — conversa WhatsApp (frontend)

## Contexto

Épico: **Tempo real (SSE)**.

Parte de: **RT-F2**

## Proposta

Em `WhatsappConversa.tsx`:

- Subscrever `chat.mensagem` para `chatId` atual
- Append mensagem na timeline
- Reduzir intervalo polling (ou remover quando SSE ok)
- Manter scroll behavior existente

Lista `WhatsappAtendendo`: refresh fila on `chat.fila`.

## Critérios de aceite

- [ ] Mensagem inbound aparece <2s (rede local)
- [ ] Sem duplicata (dedupe por wa_message_id)
- [ ] Funciona com SSE off (polling legacy)

## Dependências

- Requer: RT-04, RT-02

## Labels

`frontend`, `tempo-real`, `fase-interna`, `whatsapp`
