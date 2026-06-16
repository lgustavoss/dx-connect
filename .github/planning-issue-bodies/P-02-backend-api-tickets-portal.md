# Portal do cliente — API tickets listagem, detalhe e abertura (backend)

## Contexto

Épico: **Portal do cliente**. Expor tickets no escopo do funcionário autenticado.

Parte de: **P-F2**

## Proposta

### Endpoints

- `GET /v1/portal/tickets` — paginado, filtros: status, protocolo, data
- `GET /v1/portal/tickets/{id}` — detalhe se ticket pertence ao escopo
- `POST /v1/portal/tickets` — abertura com:
  - `empresa_id` (obrigatório se colaborador; validar escopo)
  - `setor_id` ou roteamento default
  - `assunto`, `descricao`, classificação opcional
  - `aberto_por_id` = funcionário logado (automático)

### Regras

- Funcionário **não** vê mensagens `interno`
- **Não** altera status/atendente (somente leitura operacional + nova mensagem pública se permitido)
- Empresa fora do escopo → 404 (não revelar existência)

## Critérios de aceite

- [ ] Listagem filtrada por escopo rede/empresa
- [ ] Abertura preenche `aberto_por_id` e respeita RBAC
- [ ] Detalhe omite campos internos (notas internas, atendente interno opcional)
- [ ] Testes de autorização cross-empresa

## Dependências

- Requer: P-01
- Bloqueia: P-06, P-07, P-08

## Labels

`backend`, `fase-portal`, `portal-cliente`, `tickets`
