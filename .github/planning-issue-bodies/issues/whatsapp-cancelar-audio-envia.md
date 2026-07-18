## Problema
Ao começar a gravar um áudio no composer e **cancelar**, o áudio é enviado mesmo assim (incluindo “no mudo” / clip vazio ou residual). Cancelar deve descartar a gravação sem enviar.

Provável origem: `WhatsappGravadorAudioInline` / `MediaRecorder` — `cancelar` pode ainda disparar `onstop` com blob que o fluxo trata como envio.

## Critérios de aceite
- [ ] Cancelar gravação não envia mensagem de áudio
- [ ] Não cria mensagem vazia/muda no chat nem no WhatsApp do cliente
- [ ] Após cancelar, o composer volta ao estado normal (microfone disponível)
- [ ] Enviar (parar e confirmar) continua a enviar o áudio normalmente

## Origem
Testes em produção — lote WhatsApp UX (#567).
