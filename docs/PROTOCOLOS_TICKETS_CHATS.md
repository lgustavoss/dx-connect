# Protocolos de tickets (#T…) e chats (#C…)

## Formato

- **Ticket:** `#T` + `AAAA-MM` + `-` + sequencial de **4 dígitos** (ex.: `#T2026-05-0001`).
- **Chat (WhatsApp):** `#C` + `AAAA-MM` + `-` + sequencial de **4 dígitos** (ex.: `#C2026-05-0001`).

O caractere `#` faz parte do valor persistido na coluna `protocolo`, para coincidir com a exibição e com a busca.

## Mês de referência e fuso

O par `AAAA-MM` é calculado no fuso **`America/Sao_Paulo`** no instante da criação do registro (ticket ou chat). Ao cruzar a meia-noite local, o mês muda e o **sequencial reinicia** para aquele tipo (`T` ou `C`).

## Concorrência e sequência

A sequência por (`kind`, `AAAA-MM`) está na tabela `protocol_sequences`, atualizada na mesma transação da criação do ticket/chat, com incremento sob lock (`SELECT … FOR UPDATE` onde suportado), e *savepoint* + retentativa em caso de colisão na primeira inserção.

## Dados legados

Registros antigos podem manter:

- Tickets: protocolo numérico (`10001`, …) sem prefixo `#T`.
- Chats: prefixo `WCH-…`.

Listagens e buscas (`ILIKE`) continuam a funcionar. A UI trata os dois formatos (ver `exibirProtocolo` no frontend).
