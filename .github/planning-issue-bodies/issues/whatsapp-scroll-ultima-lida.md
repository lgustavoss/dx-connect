## Problema
Ao reabrir um chat em andamento, o scroll cai em posição aleatória em vez da última mensagem vista pelo atendente. Comportamento desejado (estilo WhatsApp): restaurar a última posição lida; se o atendente já viu tudo, ir para o fim.

## Critérios de aceite
- [ ] Reabrir o mesmo chat restaura a última posição de scroll vista pelo atendente
- [ ] Se já estava no fim (todas vistas), reabre no fim da conversa
- [ ] Polling/SSE de novas mensagens não “pula” a posição enquanto o atendente lê histórico acima
- [ ] Comportamento alinhado ao já feito no Histórico/chat interno (memória de scroll por conversa)

## Origem
Testes em produção — lote WhatsApp UX.
