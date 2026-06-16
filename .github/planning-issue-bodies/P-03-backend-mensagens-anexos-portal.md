# Portal do cliente — mensagens públicas e anexos (backend)

## Contexto

Épico: **Portal do cliente**. Permitir que o solicitante acompanhe e responda no fio público.

Parte de: **P-F3**

## Proposta

- `GET /v1/portal/tickets/{id}/mensagens` — apenas `tipo=publico`
- `POST /v1/portal/tickets/{id}/mensagens` — texto + anexos (limites de tamanho/count)
- Upload anexo reutilizando storage de tickets com prefixo/quota portal
- Disparar notificação interna (#109) ao atendente responsável ou setor

## Critérios de aceite

- [ ] Mensagens internas nunca expostas
- [ ] Anexos respeitam limites configuráveis
- [ ] Nova mensagem do cliente notifica atendente (in-app; e-mail se P-04 pronto)
- [ ] Ticket encerrado: mensagem pode reabrir ou criar novo (definir regra — sugerido: mensagem pública em encerrado abre triagem / novo ticket, alinhado e-mail)

## Dependências

- Requer: P-02
- Bloqueia: P-08

## Labels

`backend`, `fase-portal`, `portal-cliente`, `tickets`
