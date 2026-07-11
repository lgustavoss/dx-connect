# Chat interno — API REST direta e canal do setor (backend)

## Contexto

Épico: **Chat interno entre atendentes e comunicados por setor**.

Parte de: **IC-F1**

Depende de: **IC-01**

## Proposta

### Endpoints (prefixo sugerido `/v1/chat-interno`)

**Inbox**

- `GET /conversas` — lista conversas do atendente (diretas + canais dos seus setores); campos: última mensagem, `nao_lidas_count`, tipo, título (nome do outro atendente ou nome do setor).

**Chat direto**

- `POST /conversas/direta` — `{ "atendente_id": N }` → cria ou retorna conversa existente.
- `GET /conversas/{id}/mensagens` — paginação cursor/offset.
- `POST /conversas/{id}/mensagens` — `{ "corpo": "..." }`.

**Canal do setor (comunicados)**

- `GET /setores/{setor_id}/canal` — obtém/cria canal do setor; 403 se atendente não vinculado ao setor.
- `POST /setores/{setor_id}/canal/mensagens` — publica comunicado (v1: admin **ou** atendente vinculado ao setor).
- Listagem de mensagens via `GET /conversas/{id}/mensagens` (mesmo contrato).

**Leitura**

- `POST /conversas/{id}/visto` — atualiza `last_seen_at` (zera não lidas para aquele atendente).

### Segurança

- Só atendentes autenticados; respeitar `tenant_id` e visibilidade de setor.
- Atendente A não lista conversa direta de B↔C.

## Critérios de aceite

- [ ] OpenAPI documentado
- [ ] Testes: criar direta, enviar mensagem, publicar no canal, 403 fora do setor
- [ ] Validação de corpo não vazio; limite razoável de tamanho (ex. 8k chars)

## Dependências

- Depende de: IC-01
- Bloqueia: IC-03, IC-04, IC-05

## Labels

`backend`, `chat-interno`, `fase-interna`
