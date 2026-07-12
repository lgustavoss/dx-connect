# Chat interno — canal do setor e comunicados (frontend)

## Contexto

Épico: **Chat interno entre atendentes e comunicados por setor**.

Parte de: **IC-F3**

Depende de: **IC-02**, **IC-03**

## Proposta

### UX

- A partir da inbox ou do detalhe do **Setor** (configurações): link «Canal / Comunicados».
- Visualização em **feed cronológico** (comunicados do setor), distinto visualmente de chat direto (ex. card com título «Comunicado», autor, data).
- **Publicar:** formulário «Novo comunicado» visível para quem a API permitir (admin ou membro do setor v1).
- Badge de não lido no canal; ao abrir, marcar visto.
- Notificação no sino global com link direto para o canal.

### Integração

- Reutilizar componentes de thread onde fizer sentido (lista de mensagens, composer).
- Nome do setor e lista de membros (opcional v1: só contagem «N atendentes»).

## Critérios de aceite

- [ ] Atendente do setor vê comunicados e recebe notificação
- [ ] Atendente de outro setor não acessa o canal (403 tratado na UI)
- [ ] Admin pode publicar em qualquer canal de setor que visualize
- [ ] Comunicado aparece na inbox unificada

## Dependências

- Depende de: IC-02, IC-04 (inbox compartilhada)

## Labels

`frontend`, `ux`, `chat-interno`, `fase-interna`
