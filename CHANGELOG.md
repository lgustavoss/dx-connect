# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Versão CalVer (`YY.MM.NNN`) é atribuída automaticamente no deploy de `staging`.

## [Unreleased]

### Melhorias

- PDVs: código editável na edição (ex.: 001 ↔ 002 ao trocar equipamento); listagem mostra só o código, sem prefixo «PDV»; colunas separadas de acesso remoto, ID e senha (copiar ID/senha; revelar senha com o olho)

### Correções

- Modo escuro: texto digitado nos campos de pesquisa (listagens e chat interno) volta a ficar legível


## [26.06.001] - 2026-06-22

### Melhorias

- Versão e notas de atualização no painel (página Sobre) (#404)
- Distribuição automática de tickets na fila — modos manual, após timeout e imediato; estratégias round-robin e menor carga (#399)
- Exibição do solicitante no detalhe do ticket e reconciliação inbound pós-cadastro (#392)
- Relatórios de tickets e chats WhatsApp com exportação CSV (#390)

### Correções

- E-mail de resposta ao cliente no Postgres (worker de outbox com timezone) (#397)
- Notificações: paridade entre badge e itens do dropdown (#395)
- Health check e capabilities com FastAPI 0.137+ (#394)
