# KB — API admin CRUD artigos (backend)

## Contexto

Épico: **Base de conhecimento**.

Parte de: **KB-F2**

## Proposta

Admin/atendente autorizado:

- `GET/POST/PUT /v1/kb/articles`
- `POST /v1/kb/articles/{id}/publish`
- `POST /v1/kb/articles/{id}/archive`
- Upload imagens inline (storage ticket-like)

Permissão: admin ou flag `pode_editar_kb` no atendente (v1: admin-only).

## Critérios de aceite

- [ ] Rascunho não visível API pública
- [ ] Audit log publish/update
- [ ] Testes CRUD + publish

## Dependências

- Requer: KB-01
- Bloqueia: KB-05

## Labels

`backend`, `base-conhecimento`, `fase-interna`
