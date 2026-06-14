# Portal do cliente — autenticação e escopo (backend)

## Contexto

Épico: **Portal do cliente** (fase futura). Primeira entrega backend: autenticação de **funcionário da rede** com JWT e escopo de dados.

Parte de: **P-F1**

## Problema atual

- Apenas atendentes internos (`Atendente`) autenticam no sistema
- `FuncionarioRede` existe no cadastro mas não tem fluxo de login

## Proposta

1. **Login portal:** e-mail + senha (ou magic link em fase posterior) vinculado a `FuncionarioRede` ativo
2. **JWT distinto** ou claim `aud=portal` para separar rotas internas vs portal
3. **Escopo automático:**
   - Colaborador → uma `empresa_id`
   - Supervisor → `empresa_ids` vinculadas
   - Sócio → todas empresas da `rede_id`
4. Endpoints `GET /v1/portal/me` com perfil e empresas visíveis
5. Primeiro acesso / reset de senha (reutilizar padrão #105 adaptado)

## Critérios de aceite

- [ ] Funcionário ativo consegue login; inativo recebe 403
- [ ] Token portal não acessa rotas admin internas
- [ ] Escopo de empresas respeita tipo (sócio/supervisor/colaborador)
- [ ] Testes pytest cobrindo os três perfis de funcionário
- [ ] Migração: campos `password_hash`, `must_change_password` em `funcionarios_rede` (ou tabela auth dedicada)

## Escopo técnico

- `backend/app/api/portal_auth.py` (novo router prefix `/portal`)
- `backend/app/core/portal_scope.py`
- Schemas Pydantic `PortalLogin`, `PortalMe`
- Alembic migration

## Dependências

- Bloqueia: P-02, P-03, P-04
- Paralelo possível com: P-05 (mock API)

## Labels

`backend`, `fase-portal`, `portal-cliente`
