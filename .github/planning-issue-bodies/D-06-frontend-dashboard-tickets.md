# Dashboard tickets — gráficos e filtros (frontend)

## Contexto

Épico: **Dashboards e relatórios**.

Parte de: **D-F2**

## Proposta

Rota `/dashboard/tickets`:

- Seletor período (7/30/90/custom)
- Filtros rede, setor, prioridade
- Gráficos: linha volume, barras motivo/status, card MTTR e CSAT
- Biblioteca: Recharts ou similar (avaliar bundle)

## Critérios de aceite

- [ ] Consome D-02
- [ ] Empty state período sem dados
- [ ] Link «Exportar CSV» → D-08

## Dependências

- Requer: D-02

## Labels

`frontend`, `dashboard`, `fase-interna`, `tickets`
