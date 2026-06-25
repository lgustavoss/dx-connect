# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Versão CalVer (`YY.MM.NNN`) é atribuída automaticamente no deploy de `staging`.

## [Unreleased]

### Correções

- Som de ticket novo na fila sem responsável tocava múltiplas vezes por emissões SSE duplicadas e hook de alerta montado em mais de um componente (#406)

### Melhorias

- Base de conhecimento (#293–#295, #299): categorias em tela própria com subcategorias (um nível); artigos separados; hub **Ajuda** no menu (consulta, categorias e artigos para admin); consulta em ticket e chat WhatsApp; artigos **somente internos** (`interno_only`); upload de imagens inline; histórico de versões; reordenação de categorias por arrastar; cache offline dos últimos manuais consultados; referência na mensagem com URL; rate limit na API pública
- Auditoria (#290–#292): trail expandido com payload, IP, request-id e user-agent; registro de atribuição, transferência, fechamento e reabertura de tickets, ações em chats WhatsApp, envio de e-mail ao cliente, visualização de credencial PDV e exportação de relatórios
- Auditoria: filtros por ação, período e atendente; exportação CSV; painel com detalhes do payload e request-id
- Página Sobre: badges de categoria (Melhorias, Correções, etc.) com texto centralizado e alinhamento uniforme na lista (#426)
- Chat WhatsApp (#403): administradores acompanham chats alheios apenas com comentário interno; envio ao cliente restrito ao operador responsável
- Chat WhatsApp (#423): registro de demandas por sessão (natureza/motivo), auto-registro ao abrir ticket e agregação no dashboard de chats
- SLA (#418): pausa automática da contagem quando o ticket está em status configurado (flag `pausa_sla`; «Aguardando cliente» ativado por padrão)
- SLA: políticas opcionais por natureza do ticket; filtro «em risco» e dashboard usam o motor completo (calendário + pausa); prazo efetivo no card SLA
- SLA (#277): políticas por setor e prioridade, calendário comercial compartilhado e snapshot de metas na criação de tickets
- SLA (#278): cálculo com horário comercial, estados dentro/em risco/violado, worker periódico e endpoint de detalhe do SLA por ticket
- SLA (#279): alertas de SLA em risco e violado por e-mail e SSE, com preferências opt-in/out e debounce por ticket/meta
- SLA (#280): painel admin em Configurações → Atendimento → SLA para CRUD de políticas por setor/prioridade
- SLA (#281): badges e filtros na listagem de tickets e card de SLA no detalhe com countdown
- Dashboard geral: card com quantidade de tickets abertos em violação de SLA, com atalho para a listagem filtrada (#416)
- Dashboard geral: card com tickets abertos em risco de SLA, com atalho para a listagem filtrada
- SLA (#417): CRUD de calendários comerciais em Configurações → Atendimento → SLA → Calendários (horário semanal e feriados nacionais)
- Configurações WhatsApp: editor de horário semanal reutilizado (mesmo componente dos calendários SLA)
- Motor de roteamento automático: regras configuráveis por admin (setor, prioridade, natureza, motivo, atendente) com avaliação em e-mail inbound e criação manual de tickets
- Audit log e histórico do ticket quando uma regra de roteamento é aplicada em runtime
- `aplicar_roteamento` restrito a administradores para sobrescrever setor explícito
- UI em Configurações → Atendimento → Roteamento com simulador de teste seco
- Histórico completo de atualizações no painel Sobre (versões anteriores permanecem visíveis)
- CHANGELOG obrigatório em PRs com mudança de produto (validação automática no CI)

### Interno / Infra

- Persistência do manifest de releases após cada deploy em staging

<!-- Adicione bullets aqui a cada PR para main. Texto para o usuário final, não mensagem de commit. -->

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
