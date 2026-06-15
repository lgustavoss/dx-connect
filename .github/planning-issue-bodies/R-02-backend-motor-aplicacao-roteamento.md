# Roteamento — avaliação de regras (backend)

## Contexto

Épico: **Roteamento automático**.

Parte de: **R-F2**

## Proposta

Serviço `evaluate_routing(context) -> RoutingResult`:

1. Carrega regras ativas ordenadas
2. Primeira match ganha
3. Integração:
   - `email_inbound_dispatch.py` — após parse MIME
   - `POST /v1/tickets` — se setor não informado ou flag `aplicar_roteamento=true`
4. Log qual regra aplicou (debug + audit)

Fallback: comportamento atual (default setor env).

## Critérios de aceite

- [ ] E-mail financeiro roteado conforme regra teste
- [ ] Ticket manual sem setor recebe setor da regra
- [ ] Setor explícito manual **não** sobrescrito (a menos que admin force)
- [ ] Testes unitários operadores contains/regex

## Dependências

- Requer: R-01

## Labels

`backend`, `roteamento`, `fase-interna`, `tickets`, `email`
