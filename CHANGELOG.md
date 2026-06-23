# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Versão CalVer (`YY.MM.NNN`) é atribuída automaticamente no deploy de `staging`.

## [Unreleased]

### Correções

- Som de ticket novo na fila sem responsável tocava múltiplas vezes por emissões SSE duplicadas e hook de alerta montado em mais de um componente (#406)

### Melhorias

- SLA (#277): políticas por setor e prioridade, calendário comercial compartilhado e snapshot de metas na criação de tickets
- SLA (#278): cálculo com horário comercial, estados dentro/em risco/violado, worker periódico e endpoint de detalhe do SLA por ticket
- SLA (#279): alertas de SLA em risco e violado por e-mail e SSE, com preferências opt-in/out e debounce por ticket/meta
- SLA (#280): painel admin em Configurações → Atendimento → SLA para CRUD de políticas por setor/prioridade
- SLA (#281): badges e filtros na listagem de tickets e card de SLA no detalhe com countdown
- Motor de roteamento automático: regras configuráveis por admin (setor, prioridade, natureza, motivo, atendente) com avaliação em e-mail inbound e criação manual de tickets
- Audit log e histórico do ticket quando uma regra de roteamento é aplicada em runtime
- `aplicar_roteamento` restrito a administradores para sobrescrever setor explícito
- UI em Configurações → Atendimento → Roteamento com simulador de teste seco
- Histórico completo de atualizações no painel Sobre (versões anteriores permanecem visíveis)
- CHANGELOG obrigatório em PRs com mudança de produto (validação automática no CI)

### Interno / Infra

- Persistência do manifest de releases após cada deploy em staging

<!-- Adicione bullets aqui a cada PR para main. Texto para o usuário final, não mensagem de commit. -->

## [26.06.002] - 2026-06-22

### Melhorias

- Histórico completo de atualizações no painel Sobre (versões anteriores permanecem visíveis)
- CHANGELOG obrigatório em PRs com mudança de produto (validação automática no CI)
- Persistência do manifest de releases após cada deploy em staging

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
