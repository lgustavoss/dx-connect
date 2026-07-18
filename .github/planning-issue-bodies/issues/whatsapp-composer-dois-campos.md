## Problema
QA em produção (WhatsApp): composer com anexo de imagem deixa o campo principal «Escreva uma mensagem…» visível junto com «Legenda opcional», gerando dois campos de texto ao mesmo tempo.

## Critérios de aceite
- [ ] Com pré-visualização de anexo aberta, só o campo de legenda (ou um único composer) fica editável
- [ ] O composer principal não permanece ativo/visível por baixo do overlay de anexo
- [ ] Cancelar ou enviar o anexo restaura o composer normal

## Origem
Testes em produção — lote WhatsApp UX.
