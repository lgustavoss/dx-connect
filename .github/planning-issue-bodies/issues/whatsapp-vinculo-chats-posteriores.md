## Problema
Após identificar/vincular um contacto novo a uma rede e empresa, quando o mesmo número envia outra mensagem (novo chat ou retomada), o banner «Contacto não identificado» / «Identificar contato» volta a aparecer como se o vínculo não tivesse sido gravado.

Relacionado em parte a #472 (banner no mesmo chat), mas aqui o sintoma é em **chats posteriores** do mesmo contacto.

## Critérios de aceite
- [ ] Após vincular/cadastrar, chats novos do mesmo `wa_id`/telefone já nascem vinculados (sem pedir identificação de novo)
- [ ] Telefone/`wa_id` no funcionário da rede permite match em inbound futuro
- [ ] Banner some e não reaparece após poll/SSE com snapshot antigo
- [ ] Teste de regressão: vincular → simular novo inbound do mesmo número → chat com vínculo

## Origem
Testes em produção — lote WhatsApp UX.
