# Protocolos de tickets (#T…), chats (#C…) e sugestões (#S…)

## Formato

- **Ticket:** `#T` + `YYYYMM` + `-` + sequencial de **4 dígitos** (ex.: `#T202605-0001`).
- **Chat (WhatsApp):** `#C` + `YYYYMM` + `-` + sequencial de **4 dígitos** (ex.: `#C202605-0001`).
- **Sugestão / problema (Release Notes):** `#S` + `YYYYMM` + `-` + sequencial de **4 dígitos** (ex.: `#S202608-0001`). Emitido **só no control-plane** DeskRudder (instância comercial na VPS), por isso é único em todos os clientes. A instância do cliente recebe o número no sync. Use este identificador no título da issue no GitHub.

O caractere `#` faz parte do valor persistido na coluna `protocolo`, para coincidir com a exibição e com a busca. **Não há hífen entre ano e mês** (`202605` = maio de 2026); o único hífen separa o período do número sequencial.

## Mês de referência e fuso

O par `YYYYMM` é calculado no fuso **`America/Sao_Paulo`** no instante da criação. Ao cruzar a meia-noite local, o mês muda e o **sequencial reinicia** para aquele tipo. `#T`/`#C`/`#P` reiniciam **na instância do cliente**; `#S` reinicia **só no control-plane**.

## Concorrência e sequência

A sequência por (`kind`, `YYYYMM`) está na tabela `protocol_sequences`, atualizada na mesma transação da criação do ticket/chat/sugestão, com incremento sob lock (`SELECT … FOR UPDATE` onde suportado), e *savepoint* + retentativa em caso de colisão na primeira inserção.

A sequência `#S` vive **só no Postgres da instância comercial** (`SAAS_CONTROL_PLANE=true`). Tickets `#T` e chats `#C` continuam por instância de cliente. Pedidos antigos sem número global podem ter legado `#S0-NNNNN` até o remint no control-plane.

## Dados legados

Registros antigos podem manter:

- Tickets: protocolo numérico (`10001`, …) sem prefixo `#T`.
- Chats: prefixo `WCH-…`.
- Protocolos já gerados no formato antigo com hífen na data (`#T2026-05-0001`): permanecem como estão até novos registros usarem `YYYYMM`.

Listagens e buscas (`ILIKE`) continuam a funcionar. A UI trata os dois formatos (ver `exibirProtocolo` no frontend).
