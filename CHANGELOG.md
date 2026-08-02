# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Versão CalVer (`YY.MM.NNN`) é atribuída automaticamente no deploy de `staging`.

## [Unreleased]

### Corrigido

- WhatsApp: Enter na legenda do anexo deixava de enviar a imagem **duas vezes** (o evento subia ao painel e disparava o envio de novo)
- WhatsApp (#628): ao atender com vários setores, o modal «Escolher setor» voltava vazio (pedido com `limit` acima do máximo da API); a lista passa a carregar com paginação válida
- Frontend: alinhamento de `react` e `react-dom` em **19.2.8** (o Dependabot tinha subido só o `react`, o que gerava tela preta com React error #527 em produção)

### Melhorias

- WhatsApp: na visualização ampliada de imagens, dá para fazer zoom (+/−, scroll e duplo clique), rodar e arrastar; repor volta à vista normal (também no chat interno)
- WhatsApp (#628): no WhatsApp do cliente, mensagens do atendente saem com prefixo **setor do atendimento + nome** e o texto na linha de baixo (ex.: `[ Suporte - Ana ]:`); ao assumir, 1 setor é gravado automaticamente e vários setores pedem escolha no painel
- WhatsApp (#629): no lightbox de imagens da conversa, dá para navegar entre as fotos (botões e setas ←/→) com contador e legenda atualizada; Esc continua a fechar só a visualização
- WhatsApp (#630): foto de perfil do contacto no header e nas listas Atendendo/Aguardando (com cache e fallback para a inicial do nome)
- WhatsApp (#630): reações no chat com o cliente — ver emoji do cliente no balão e o atendente responsável pode reagir (👍 ❤️ 😂 😮 😢 🙏); clique de novo remove
- WhatsApp (#630): editar (até 15 min) e apagar para todos (até 48 h) mensagens de texto enviadas pelo responsável; também sincroniza quando o cliente edita ou apaga
- WhatsApp: no header da conversa, o chip da empresa abre a página de detalhe da empresa (Voltar regressa ao chat); alterar empresa multi-empresa continua no menu ⋮
- Chat (#626): ícone de som junto a **Aguardando** para silenciar/reativar o alerta contínuo da fila (WhatsApp + portal); preferência guardada no browser — não afeta alertas de ticket nem do chat interno
- Portal do cliente (#263 / #300–#308): funcionários da rede fazem login em **/portal**, abrem e acompanham chamados da sua empresa, respondem no fio público, anexam ficheiros, consultam a base de ajuda e recebem e-mail quando a equipe responde; o admin define a senha do portal no cadastro do funcionário
- Portal (#600, #601): cadastro de funcionário pelo modal da Rede permite definir senha do portal na criação; sócio cadastra sem escolher empresas (escopo automático em toda a rede)
- Portal (#604): RBAC por papel — colaborador vê só os próprios chamados; supervisor vê todos das empresas vinculadas; sócio vê toda a rede
- Portal (#603): listagem e detalhe de atendimentos WhatsApp no `/portal` (somente leitura), com o mesmo escopo por papel e sem comentários internos da equipe
- Portal (#602): sócio gere a equipa no `/portal` — cadastro e edição de colaboradores e supervisores (empresas, senha do portal); outros sócios listados com edição limitada; colaborador/supervisor recebem 403
- Portal (#605): branding white-label no `/portal` — logo e cores da instância (mesmas configurações de Configurações → Base de conhecimento); login e shell aplicam a identidade do contratante, não a marca DeskRudder
- Portal: shell alinhado ao painel DeskRudder (menu lateral com usuário/Sair, navbar com expandir/recolher); cor do menu lateral configurável (padrão = navbar); chat ao vivo no `/portal` (mesmo canal da `/kb`, isolado por instância); login com logo em destaque, ícone de olho na senha e fundo minimalista; título do portal independente da central `/kb`
- WhatsApp (#593): ao **cadastrar** contacto no chat, o sistema sugere funcionários com nome semelhante para vincular (evita duplicados); o atendente pode ignorar e criar novo
- WhatsApp (#591): no detalhe da **Empresa**, nova aba **Chats** com atendimentos filtrados por aquela empresa (busca, paginação, abrir conversa / retomar)
- WhatsApp (#592): com funcionário em **mais de uma empresa**, o atendimento pode começar sem empresa; o atendente pergunta ao cliente e vincula (ou altera) a qualquer momento antes de encerrar — 1 empresa continua automática
- WhatsApp (#590): na listagem **Atendimentos**, cada card mostra a **empresa** do contacto (ou «Sem empresa» quando não houver vínculo)
- WhatsApp (#577): encerramento por inatividade conta desde a **última mensagem** (cliente ou atendente); botão **Pausar/Retomar** com countdown (até o aviso e, após o aviso, até encerrar); enviar mensagem sai da pausa automaticamente
- WhatsApp (#575): ✓✓ azul no WhatsApp do cliente só quando o **atendente responsável** abre o chat no painel
- PDVs: código editável na edição (ex.: 001 ↔ 002 ao trocar equipamento); listagem mostra só o código, sem prefixo «PDV»; colunas separadas de acesso remoto, ID e senha (copiar ID/senha; revelar senha com o olho)
- Chat interno: alerta sonoro ao receber nova mensagem; em grupos, opção de **Silenciar** / **Ativar som** (preferência por pessoa)
- Chat interno: ao passar o mouse em mensagens próximas, as opções (Responder/Editar/Apagar) e reações não “saltam” mais para a mensagem de cima
- Equipe online: lista funciona com vários workers do servidor (presença gravada no banco); admin pode **Forçar saída** de um atendente conectado
- Chat interno: balões mais próximos — opções/reações só no hover; em grupos, avatar e cor por pessoa para distinguir quem fala
- Equipe online (#545–#547): administradores veem quem está com o painel aberto e desde quando (menu **Equipe online**), para coordenar atendimento de chats e tickets
- Chat interno: no grupo, clique no nome na barra superior para ver participantes e administradores; admins promovidos também podem gerenciar membros
- WhatsApp: na busca «Vincular existente», cada resultado mostra **rede** e **empresa(s)** para distinguir homónimos
- WhatsApp (#534): identificar/cadastrar contato do cliente também em atendimento **encerrado** (Histórico); o número do WhatsApp passa a ser gravado no telefone do cadastro para retomar pela aba Contatos
- WhatsApp (#531): aba **Contatos** no hub de chat — lista funcionários com empresa e telefone; iniciar conversa (ou número avulso / retomar no Histórico); chat já fica em atendimento com o iniciador; telefone no cadastro do funcionário da rede
- Chat (#607): na aba **Atendendo**, secções **Comigo** e **Outros atendentes** quando o admin acompanha colegas; badge «Você» e destaque visual nos seus; nome do responsável legível nos de outros
- WhatsApp (#606): conversa mais utilizável no **mobile** — composer com campo largo e botão de manuais só ícone; menu **⋮** com Transferir/Tickets; metadados em linha separada; painel de demandas colapsável; `safe-area` no composer

### Correções

- Chat (#625): ao **Ver** um chat da fila Aguardando, a lista com **Atender** permanece na lateral; na conversa há CTA **Atender** (WhatsApp e portal) para assumir sem voltar à lista
- WhatsApp (#627): com anexo pendente, **Enter** na legenda (ou no painel, em áudio) envia o anexo — equivalente a «Enviar anexo»
- WhatsApp (#608): duas mensagens inbound seguidas do mesmo contacto deixam de abrir dois chats/protocolos — lock por `wa_id` no webhook e uma única sequência de auto-mensagens por sessão
- WhatsApp (#598): após encerrar com avaliação, janela de ~30 min (configurável) para a nota; se o cliente mandar outro texto, abre atendimento novo com essa mensagem; sem resposta, finaliza sozinho
- WhatsApp: após encerramento por inatividade, o chat fica em **A classificar demanda** (somente leitura) até registar, manter demandas existentes ou confirmar sem demanda; nova mensagem do mesmo cliente abre chat novo na fila
- WhatsApp (#575): ticks de entrega/leitura no painel passam a atualizar (✓✓ / ✓✓ azul) — o webhook da Evolution com `keyId` + `DELIVERY_ACK`/`READ` era ignorado; mark-as-read no WhatsApp do cliente também quando chega mensagem nova com o responsável no chat
- WhatsApp (#568): ao anexar imagem, só o campo de legenda fica visível (sem o composer por baixo)
- WhatsApp (#569/#572/#574): legenda de mídia com a mesma fonte do texto; PDF/vídeo mostram legenda; sem placeholder «[Imagem enviada]» quando não há legenda
- WhatsApp (#571): Esc no zoom da imagem fecha só a visualização, sem sair do chat
- WhatsApp (#576): cancelar gravação de áudio já não envia o ficheiro
- WhatsApp (#573): ao reabrir o chat, o scroll volta à última posição vista (não salta para o início)
- WhatsApp (#570): contacto já vinculado é reconhecido em chats novos do mesmo número
- Modo escuro: texto digitado nos campos de pesquisa (listagens e chat interno) volta a ficar legível
- Equipe online: «0 online» mesmo com painel aberto (lista lia só a memória do worker errado)
- Chat interno: espaço excessivo entre mensagens após colocar ações/reações fora do balão
- WhatsApp: o feed deixa de puxar sozinho para o fim enquanto você lê mensagens acima; ao reabrir a conversa, retoma a posição em que parou
- Chat interno: ações (Responder/Editar/Apagar) e reações ficam fora do balão da mensagem
- Chat interno: clique na imagem abre visualização em tela cheia (antes só tinha o cursor de zoom, sem ação)
- Anexos de ticket: ficheiros deixam de desaparecer após atualização do sistema; se o arquivo já tiver sido perdido, o aviso deixa isso claro
- WhatsApp: removido botão duplicado «Identificar contato» no header — fica só o do banner enquanto o contacto não está vinculado; após vincular o CTA some
- WhatsApp: encerramento por inatividade só conta a partir da última mensagem do cliente quando o chat já está em atendimento e o atendente já enviou mensagem humana (auto_assumido/BOT não disparam o timer)
- WhatsApp: Ctrl+V no composer cola imagem/ficheiro do clipboard (pré-visualização antes de enviar), como no chat interno
- Chat: removida a borda branca de foco no campo de mensagem e nos demais inputs/textareas (outline nativo + alinhamento ao design system)
- Chat interno: contraste no hover de Responder/Editar/Apagar; duplo clique na mensagem (ou ao lado do balão) inicia resposta e foca o composer — também no WhatsApp
- WhatsApp / modais: ao digitar na descrição da demanda no **Encerrar atendimento**, o campo perdia o foco a cada atualização da conversa — diálogo já não refoca o painel; formulário não é limpo pelo poll
- Sons de alerta: toque de **abertura de ticket** e de **novo chat** (fila WhatsApp/Portal) estavam trocados — ticket usa `notification.mp3` e chat na fila usa `alerta.mp3`
- WhatsApp: conversa em atendimento disparava loop de pedidos a `/demandas` (e esgotava recursos do browser com `ERR_INSUFFICIENT_RESOURCES`) — o painel de demandas já não notifica o pai no carregamento inicial
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
- Chat interno (IC-F3): inbox unificada, conversas diretas e canais de setor no menu Chat interno; comunicados com visual distinto; link no detalhe do setor; layout com lista lateral fixa para alternar conversas e ver não lidas
- Chat interno (#495): anexos e mídia — upload, download, pré-visualização no painel e colar imagem (Ctrl+V) no composer
- Chat operacional: hub unificado em `/chat` com abas Atendendo, Aguardando e Interno; tela **Atendimentos** no menu para consulta de chats abertos e encerrados (#485)
- WhatsApp (#484): aba **Aguardando** no hub; no mobile, atalho na conversa abre a fila para assumir chats sem voltar à lista
- Chat interno e WhatsApp: indicadores de envio, entrega e leitura nas mensagens (✓ / ✓✓)
- Notificações: pendência do chat interno abre direto em `/chat/interno/{id}`
- Chat interno (#503): editar e apagar mensagens de texto — autor ou admin; exclusão lógica com «Mensagem apagada»
- Chat interno (#502): reações rápidas (👍 ❤️ 😂 😮 😢 🙏) em conversas diretas e canais de setor
- Chat interno: editar e apagar para todos só nos primeiros 5 minutos; depois «apagar para mim»; opção de limpar conversa só para você
- Chat interno: ao ler o histórico o scroll não volta sozinho para o fim; ao reabrir a conversa retoma na última mensagem visualizada
- Chat interno (#505): paginação infinita — carrega mensagens recentes e busca histórico ao rolar para cima (50 por vez)
- Chat interno (#506): editar legenda de mensagens com mídia (mesma janela de 5 minutos)
- Chat interno (#507): grupos personalizados com até 50 atendentes; criador e admins promovidos gerenciam membros
- WhatsApp (#470): áudio gravado na barra de composição é enviado automaticamente ao terminar a gravação (estilo WhatsApp Web)
- Identidade visual (#434): marca DeskRudder no login e em todo o painel
- WhatsApp (#485): menu «Atendimentos» unifica chats abertos e encerrados com filtro por status
- Base de conhecimento (#296): admin vincula manuais a natureza/motivo; até 5 sugestões na classificação de tickets e demandas WhatsApp
- Base de conhecimento (#465/#466): portal público `/kb` com logo e nome da empresa (Configurações → Empresa); listagem, busca e leitura de artigos sem login
- Base de conhecimento (#467): personalização do portal em Configurações → Sistema → Base de conhecimento (cores da navbar, textos, links); menu lateral de categorias/subcategorias expansível no /kb; navbar com título centralizado, logo sem fundo branco e menu hamburger
- Base de conhecimento (#469): visitantes do portal `/kb` avaliam manuais como úteis ou não; admin vê totais no artigo e pode ligar/desligar a avaliação nas configurações do portal
- Base de conhecimento (#468): chat ao vivo no portal `/kb` — widget para visitantes; atendimento na mesma inbox WhatsApp (abas Aguardando/Atendendo) com badge Portal; protocolo unificado `#C`; mensagens automáticas, avaliação ao encerrar, anexos e áudio como no WhatsApp; transferência, demandas e encerramento com revisão
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
- Deploy: volume Docker `backend_data` → `/app/data` (anexos, mídia WhatsApp/chat interno, KB e logos) no compose de produção e no template por cliente

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
