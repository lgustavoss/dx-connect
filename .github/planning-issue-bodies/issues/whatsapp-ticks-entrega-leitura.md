## Problema
Mensagens do atendente ficam com um único ✓ no DeskRudder, e no WhatsApp do **cliente** a mensagem não passa a «visualizada» (✓✓ azul) mesmo depois de o cliente ter respondido.

Hoje o ✓✓ azul só aparece se alguém abrir a mesma conversa no **WhatsApp do suporte** (número/instância que recebe o inbound). Isso foge do fluxo do painel.

## Regra de negócio (leitura / ✓✓ azul)
A mensagem do **cliente** só deve ser marcada como visualizada (e o cliente só deve ver ✓✓ azul nas mensagens **dele** / o estado de leitura correspondente) quando for visualizada pelo **atendente responsável** pelo chat.

- [ ] Visualizada pelo **responsável** do chat → pode marcar como lida / refletir ✓✓ azul no WhatsApp do cliente (conforme API Evolution)
- [ ] Visualizada por **outro atendente** (ex.: consulta no Histórico, colega do setor) → **não** marcar como lida para o cliente
- [ ] Visualizada **antes** de alguém assumir o atendimento (fila / sem responsável) → **não** marcar como lida para o cliente

## Sintoma adicional (ticks no painel)
No DeskRudder, mensagens do atendente ficam com um só ✓ mesmo quando no WhatsApp do cliente já estão entregues/lidas — o painel precisa espelhar entrega (✓✓) e leitura (✓✓ azul) com base nos eventos reais da API, sem depender de abrir o app WhatsApp do suporte.

## Critérios de aceite
- [ ] ✓ = enviada / aceite pela API
- [ ] ✓✓ cinza = entregue no dispositivo do cliente
- [ ] ✓✓ azul = lida, **somente** quando a regra de negócio acima for satisfeita (responsável visualizou)
- [ ] Abrir o chat no painel como não-responsável ou sem responsável **não** dispara read receipt para o cliente
- [ ] Abrir o chat como responsável dispara (ou confirma) a leitura conforme a Evolution API
- [ ] Atualização via webhook/SSE/poll no painel sem precisar do WhatsApp mobile do suporte
- [ ] Testes cobrindo: responsável vs outro atendente vs sem responsável

## Origem
Testes em produção — lote WhatsApp UX (#567). Clarificação: read receipt só pelo atendente responsável.
