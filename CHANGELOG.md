# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Versão CalVer (`YY.MM.NNN`) é atribuída automaticamente no deploy de `staging`.

## [Unreleased]

### Correções

- WhatsApp (#473): modal de encerramento deixava de carregar demandas — polling da conversa refazia o fetch e mantinha «A carregar demandas…» em loop; demanda passa a ser opcional quando o chat encerra por inatividade
- WhatsApp (#472): banner «contato não identificado» persistia após vincular/cadastrar — polling/SSE com snapshot antigo sobrescrevia o vínculo; sidebar e header atualizam na hora
- WhatsApp (#471): cache de mídia por mensagem reduz refetch de blobs e mitiga `ERR_INSUFFICIENT_RESOURCES` no carregamento de anexos
- WhatsApp: aviso de inatividade duplicado quando vários workers processavam o mesmo chat em paralelo (Gunicorn)
- WhatsApp (#443/#454): painel de emoji e envio de figurinhas no composer; Histórico e Avaliações preservam posição de scroll ao voltar da conversa
- WhatsApp (#449): corrigido link do Histórico/Avaliações para conversa — query `?from=` separada do `pathname` (React Router v7)
- Notificações (#452): pendências de mensagem não lida abrem o ticket ou chat concreto (`/tickets/{id}`, `/whatsapp/c/{id}`) — removido fallback genérico para listagens
- WhatsApp (#447): terminologia «contato do cliente» no chat e tickets — distingue colaborador da rede de atendente interno
- WhatsApp (#453): ícones por tipo de ficheiro (PDF, Word, Excel, etc.) nas mensagens de documento
- WhatsApp (#446): marco «Demanda registada» na timeline via evento interno + SSE em tempo real; removido ao excluir demanda
- WhatsApp (#455): Histórico lista chats em atendimento — colegas do setor consultam e comentam internamente; ordenação e filtros de data corrigidos
- WhatsApp (#443): barra de composição estilo WhatsApp Web (+ anexos, emoji e figurinhas, microfone à direita)
- WhatsApp (#445): modal de encerramento substitui `confirm()` nativo — registo/edição de demandas, aviso quando houve conversa após última demanda, marco na timeline e `ConfirmDialog` reutilizável
- WhatsApp (#449): botão Voltar na conversa regressa à lista de origem (Atendimento, Histórico ou Avaliações), com filtros na URL e atalho Escape
- WhatsApp (#448): abas Histórico e Avaliações — filtros coerentes (finalizados incluem aguardando avaliação; avaliações só com nota respondida)
- WhatsApp (#444): cadastro de funcionário no chat com e-mail opcional; erros de validação visíveis dentro do modal (não atrás do overlay); toasts acima de modais
- WhatsApp (#442): mensagens inbound passam a aparecer sem reload — polling de segurança na conversa e na fila, complementando SSE em deploy multi-worker
- WhatsApp (#441): áudio gravado pelo atendente enviado como nota de voz via `sendWhatsAppAudio` (encoding Evolution); falha explícita se a API não confirmar entrega
- WhatsApp (#431): mídia recebida (imagem, áudio, vídeo, documento, figurinha) gravada corretamente no webhook; fallback e retry na Evolution API; UI deixa de ficar presa em «Carregando mídia…» quando o ficheiro não está disponível
- WhatsApp (#432): barra de anexos com ações visíveis (imagem, vídeo, áudio, documento, gravar áudio), pré-visualização antes do envio e legenda opcional
- WhatsApp (#433): banner e badge «Sem vínculo» para contactos não cadastrados; botão vincular visível em mobile
- WhatsApp: mensagens de contacto e localização recebidas passam a aparecer como texto legível no chat
- Som de ticket novo na fila sem responsável tocava múltiplas vezes por emissões SSE duplicadas e hook de alerta montado em mais de um componente (#406)

### Melhorias

- Chat interno (IC-F1): API backend para conversas diretas entre atendentes e canal de comunicados por setor — inbox, mensagens, leitura (`/v1/chat-interno`); conversas diretas privadas (admin não vê conversas de terceiros)
- Chat interno (IC-F2): mensagens internas no sino de notificações e evento SSE `chat.interno.mensagem`; contador `chat_interno_nao_lidas_count` no badge do navbar
- WhatsApp (#470): áudio gravado na barra de composição é enviado automaticamente ao terminar a gravação (estilo WhatsApp Web)
- Identidade visual (#434): painel lateral do login e assets legados DX/Duplexsoft removidos — marca DeskRudder em todo o painel
- Base de conhecimento (#296): admin vincula manuais a natureza/motivo; até 5 sugestões na classificação de tickets e demandas WhatsApp
- Base de conhecimento (#465/#466): portal público `/kb` com logo e nome da empresa (Configurações → Empresa); listagem, busca e leitura de artigos sem login
- Base de conhecimento (#467): personalização do portal em Configurações → Sistema → Base de conhecimento (cores da navbar, textos, links); menu lateral de categorias/subcategorias expansível no /kb; navbar com título centralizado, logo sem fundo branco e menu hamburger
- Base de conhecimento (#293–#299): menu **Ajuda** para consultar manuais durante o atendimento; gestão de categorias e artigos (admin); consulta integrada em tickets e WhatsApp; manuais «só para a equipe»; imagens no texto; histórico de versões; reordenar categorias arrastando; manuais consultados ficam disponíveis offline neste computador
- Auditoria (#290–#292): trail expandido com payload, IP, request-id e user-agent; registro de atribuição, transferência, fechamento e reabertura de tickets, ações em chats WhatsApp, envio de e-mail ao cliente, visualização de credencial PDV e exportação de relatórios
- Auditoria: filtros por ação, período e atendente; exportação CSV; painel com detalhes do payload e request-id
- Página Sobre: badges de categoria (Melhorias, Correções, etc.) com texto centralizado e alinhamento uniforme na lista (#426)
- Chat WhatsApp (#403): administradores acompanham chats alheios apenas com comentário interno; envio ao cliente restrito ao operador responsável
- Chat WhatsApp (#423): registro de demandas por sessão (natureza/motivo), auto-registro ao abrir ticket e agregação no dashboard de chats; edição via `PATCH`, marco na timeline e fluxo completo no modal de encerramento (#445)
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
