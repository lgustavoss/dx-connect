## Problema
O encerramento automático por inatividade conta desde a **última mensagem do cliente** e **não reinicia** quando o atendente fala. Isso causa:

1. Cliente na fila por vários minutos → ao assumir, o aviso/encerramento dispara cedo demais.
2. Atendente pede «aguarde, estou analisando» → o chat fecha mesmo com o cliente à espera, se a análise passar do prazo.

## Regra de negócio

### Timer
- Contar desde a **última mensagem relevante** (cliente **ou** atendente humano).
- Qualquer mensagem nova (cliente ou atendente) **reinicia** a contagem.
- Só age em chat `em_atendimento` **depois** da 1ª resposta humana (não dispara na fila / só com `auto_assumido`/BOT).
- Manter settings: `inativ_aviso_minutos` + `inativ_encerramento_apos_aviso_minutos`.

### Pausa no chat
- Botão **Pausar** / **Retomar** no header, com **countdown** ao lado.
- **Pausar:** para o worker e **reseta** o prazo para o valor configurado (ex. 10:00) — não congela o restante.
- **Retomar:** inicia a regressiva **de novo** a partir do prazo cheio.
- Enquanto pausado: não envia aviso nem encerra.
- Ao receber mensagem do cliente: sair da pausa automaticamente (além do retomar manual).

## Critérios de aceite
- [ ] Após fila longa, o prazo completo conta a partir da última mensagem (ex.: resposta do atendente reinicia)
- [ ] Mensagem do cliente ou do atendente reinicia a contagem
- [ ] Countdown visível no chat em atendimento (feature ligada)
- [ ] Pausar: para o worker e mostra prazo resetado; não encerra
- [ ] Retomar: inicia regressiva do prazo cheio de novo
- [ ] `auto_assumido` / fila sem resposta humana: não dispara
- [ ] Ciclo aviso → encerramento após aviso preservado
- [ ] Testes backend + texto de ajuda na Config WhatsApp + CHANGELOG

## Origem
QA produção — análise de regra de negócio. Parte do épico #567 (lote WhatsApp).

## Referência técnica
- `backend/app/services/whatsapp_inactivity_worker.py` (`_referencia_inatividade_cliente`)
- Plano: regra inatividade WhatsApp (última msg + pausa com countdown)
