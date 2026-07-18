## Problema
Quando o atendente envia imagem/mídia **sem** legenda, o balão mostra texto placeholder do tipo `[ Luan ]: [Imagem enviada]` (ou similar). Sem legenda, deve aparecer **só** a mídia — sem rótulo de texto.

Hoje o filtro de rótulos técnicos (`ROTULO_SEM_LEGENDA`) cobre padrões como `[Imagem]`, mas não variantes como `[Imagem enviada]`, e o prefixo `[ Nome ]:` pode estar a ser concatenado no corpo.

## Critérios de aceite
- [ ] Imagem/vídeo/documento/áudio enviados sem legenda: balão sem texto de placeholder
- [ ] Com legenda real: legenda continua a aparecer
- [ ] Não exibir `[Imagem]`, `[Imagem enviada]` nem equivalentes como corpo da mensagem

## Origem
Testes em produção — lote WhatsApp UX (#567).
