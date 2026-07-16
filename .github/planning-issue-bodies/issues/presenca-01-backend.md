## Contexto

Épico: [#545](https://github.com/lgustavoss/dx-connect/issues/545) Presença de atendentes online (admin).

Parte de: **PR-F1** · Issue: [#546](https://github.com/lgustavoss/dx-connect/issues/546)

O `RealtimeHub` já mantém filas por canal `atendente:{id}` em `subscribe` / `unsubscribe`. Falta registrar **quem** está conectado e **desde quando**, e expor isso numa API só para admin.

## Proposta

### Tracking no hub

- Ao `subscribe` em `atendente:{id}`: se for a 1ª conexão desse canal, gravar `online_desde = now()` (UTC).
- Ao `unsubscribe`: se o canal ficar sem filas, marcar offline (remover do mapa).
- Multi-aba: contador de conexões; `online_desde` só muda quando o canal passa de 0 → 1 conexão.
- Opcional v1: evento SSE `presenca.atualizada` para admins (payload mínimo: `{ atendente_id, online, online_desde? }`) — facilita UI sem polling agressivo. Se não houver canal «broadcast admin», aceitar polling na F2.

### API

`GET /v1/presenca/online` (ou `/v1/atendentes/presenca`) — **somente admin**

Resposta sugerida (lista só online, ou todos com flag — preferir **só online** na v1):

```json
{
  "itens": [
    {
      "atendente_id": 12,
      "nome": "Maria",
      "email": "maria@…",
      "role": "atendente",
      "online_desde": "2026-07-16T12:00:00Z",
      "setores": [{ "id": 1, "nome": "Suporte" }]
    }
  ]
}
```

- Incluir admins online também (eles também usam o painel).
- Excluir contas `ativo=false` mesmo que ainda tenham SSE residual.
- Tenant scope: só atendentes do tenant atual.

### Testes

- Integração: simular subscribe/unsubscribe (ou cliente SSE de teste) e assert da API.
- RBAC: atendente recebe 403; admin 200.
- Multi-aba: 2 connects → 1 disconnect → ainda online; 2º disconnect → some da lista.

### Docs

- Nota curta em `docs/REALTIME_SSE.md`: presença deriva do hub; limite multi-worker.

## Critérios de aceite

- [ ] Admin lista atendentes online com `online_desde`
- [ ] Atendente recebe 403
- [ ] Abre/fecha SSE reflete na lista (após disconnect limpo)
- [ ] Multi-aba não zera presença até a última conexão
- [ ] Testes de integração cobrindo happy path + RBAC
- [ ] Nota multi-worker em `docs/REALTIME_SSE.md`

## Dependências

- Requer: SSE RT-F1 (#264) — já em produção

## Fora de escopo

- Persistência em banco / histórico
- Redis para multi-worker
- Status «ausente» manual

## Labels

`backend`, `enhancement`, `python`
