## Contexto

Épico: [#545](https://github.com/lgustavoss/dx-connect/issues/545) Presença de atendentes online (admin).

Parte de: **PR-F2** · Issue: [#547](https://github.com/lgustavoss/dx-connect/issues/547)

Depende de: [#546](https://github.com/lgustavoss/dx-connect/issues/546) (API presença).

## Objetivo

Tela no painel, **somente admin**, listando quem está online e desde quando — para coordenar atendimento de chats e tickets.

## Proposta de UX

### Navegação

- Item no menu (ex.: **Equipe online** ou sob Relatórios/Dashboard) visível só para `role === admin`.
- Rota sugerida: `/equipe/online` ou `/presenca`.

### Conteúdo

- Tabela ou lista:
  - Nome
  - Setores (chips/texto)
  - Online desde (relativo «há 12 min» + tooltip com horário absoluto)
  - Role (admin / atendente) — opcional, discreto
- Estado vazio: «Nenhum atendente online no momento»
- Contador no topo: «N online»
- Refresh: polling leve (ex. 15–30 s) e/ou evento SSE `presenca.atualizada` se a F1 emitir
- Indicador de última atualização

### Fora desta tela (v1)

- Ações na linha (atribuir ticket, ping)
- Filtro por setor (nice-to-have se barato)
- Histórico

## Mapa técnico

| Ação | Caminho provável |
|------|------------------|
| API client | `frontend/src/api/client.ts` |
| Página | `frontend/src/pages/PresencaOnline.tsx` (ou pasta `equipe/`) |
| Rota | `App.tsx` — guard admin |
| Menu | `Sidebar.tsx` — só admin |

Reutilizar padrões visuais de listagens admin existentes (Auditoria, dashboards) — sem inventar design system novo.

## Critérios de aceite

- [ ] Admin acessa a tela e vê online + desde quando
- [ ] Atendente não vê o item no menu nem acessa a rota (redirect/403)
- [ ] Lista atualiza periodicamente (ou via SSE)
- [ ] Estado vazio legível
- [ ] Mobile: lista legível
- [ ] `npm run build` passa

## Dependências

- Requer: PR-F1 (API presença)

## Labels

`frontend`, `ux`, `enhancement`
