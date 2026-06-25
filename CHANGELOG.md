# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Versão CalVer (`YY.MM.NNN`) é atribuída automaticamente no deploy de `staging`.

## [Unreleased]

### Correções

- Som de ticket novo na fila sem responsável tocava múltiplas vezes por emissões SSE duplicadas e hook de alerta montado em mais de um componente (#406)

### Melhorias

- Base de conhecimento (#293–#299): menu **Ajuda** para consultar manuais durante o atendimento; gestão de categorias e artigos (admin); consulta integrada em tickets e WhatsApp; manuais «só para a equipe»; imagens no texto; histórico de versões; reordenar categorias arrastando; manuais consultados ficam disponíveis offline neste computador
- Auditoria (#290–#292): registro detalhado de ações no sistema (atribuição e transferência de tickets, chats WhatsApp, e-mails ao cliente, credenciais PDV e exportações)
- Auditoria: filtros por ação, período e atendente; exportação CSV; painel com detalhes do registro
- Página Sobre: badges de categoria (Melhorias, Correções, etc.) com texto centralizado e alinhamento uniforme na lista (#426)
- Chat WhatsApp (#403): administradores acompanham chats alheios apenas com comentário interno; envio ao cliente restrito ao operador responsável
- Chat WhatsApp (#423): registro de demandas por sessão (natureza/motivo), auto-registro ao abrir ticket e agregação no dashboard de chats
- SLA (#418): pausa automática da contagem quando o ticket está em status «Aguardando cliente» (ativado por padrão)
- SLA: políticas opcionais por natureza do ticket; filtro «em risco» e dashboard usam calendário comercial e pausa; prazo efetivo no card SLA
- Dashboard geral: card com quantidade de tickets abertos em violação de SLA, com atalho para a listagem filtrada (#416)
- Dashboard geral: card com tickets abertos em risco de SLA, com atalho para a listagem filtrada
- SLA (#417): calendários comerciais em Configurações → Atendimento → SLA (horário semanal e feriados nacionais)
- Configurações WhatsApp: editor de horário semanal reutilizado (mesmo componente dos calendários SLA)

## [26.06.003] - 2026-06-23

### Melhorias

- SLA (#277): políticas por setor e prioridade, calendário comercial compartilhado e snapshot de metas na criação de tickets
- SLA (#278): cálculo com horário comercial, estados dentro/em risco/violado, worker periódico e detalhe do SLA por ticket
- SLA (#279): alertas de SLA em risco e violado por e-mail e SSE, com preferências opt-in/out
- SLA (#280): painel admin em Configurações → Atendimento → SLA para políticas por setor/prioridade
- SLA (#281): badges e filtros na listagem de tickets e card de SLA no detalhe com countdown
- Motor de roteamento automático: regras configuráveis por admin com simulador de teste
- Histórico completo de atualizações no painel Sobre (versões anteriores permanecem visíveis)
- CHANGELOG obrigatório em PRs com mudança de produto (validação automática no CI)
- Persistência do manifest de releases após cada deploy em staging

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
