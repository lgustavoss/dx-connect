# Portal do cliente — layout, rotas e login (frontend)

## Contexto

Épico: **Portal do cliente**. Shell da aplicação externa (subdomínio ou `/portal`).

Parte de: **P-F1**

## Proposta

- Rotas: `/portal/login`, `/portal/tickets`, `/portal/tickets/novo`, `/portal/tickets/:id`
- Layout distinto do painel interno (marca empresa sistema + rede)
- Auth context separado (`PortalAuthProvider`) ou app Vite separado (decisão implementação)
- Guard: redireciona não autenticado para login
- Tema claro/escuro opcional (reutilizar ThemeContext se mesmo bundle)

## Critérios de aceite

- [ ] Login consome P-01 e persiste token
- [ ] Logout limpa sessão
- [ ] Mobile-first (funcionários de posto)
- [ ] Sem links para áreas admin internas

## Dependências

- Requer: P-01 (ou mock)
- Bloqueia: P-06, P-07, P-08

## Labels

`frontend`, `fase-portal`, `portal-cliente`
