# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Versão CalVer (`YY.MM.NNN`) é atribuída automaticamente no deploy de `staging`.

## [Unreleased]

### SaaS Control Plane

#### Melhorias

- Fila de sugestões no Cursor (MCP): o ops liga-se à API comercial (`api.deskrudder.com.br`); o token fica só na VPS e no Cursor de cada pessoa, não no git

### DeskRudder

#### Melhorias

- UI (#866): botão **Cancelar** padronizado em vermelho (`variant=cancel`, bordo forte), distinto de Excluir; ConfirmDialog e formulários/modais alinhados
- UI (#867): controlo **Voltar** com estilo de botão (fundo/padding) em cadastros, detalhes, portal, WhatsApp e ecrãs de erro de carregamento
- Sugestões: cada pedido ganha um **protocolo único** (`#S202608-0001`) no painel DeskRudder, visível depois em Minhas solicitações, para amarrar a issue no GitHub
- Sugestões: no painel SaaS dá para **ligar pedidos iguais** de vários clientes (peso da demanda). O cliente não vê este grupo; na issue GitHub entram todos os protocolos
- Sugestões (#855): pedidos abertos nas Release Notes continuam na instância (**Minhas solicitações**); a cópia para o produto DeskRudder vai para o painel SaaS, não para o GitHub na instância
- Sugestões (#856): o **status e as respostas de produto** passam a ser definidos no painel SaaS DeskRudder; na instância o admin só acompanha. O cliente vê o andamento e os comentários públicos em **Minhas solicitações** (notas internas não saem do SaaS)
- Sobre / Release Notes: o rodapé da barra leva sempre a esta tela (em local a versão vem das notas publicadas, mesmo sem o ficheiro `VERSION` no Docker). **Minhas solicitações** fica nesta página, não no menu Ajuda.
- Ponto (#841): ao bater **saída** com pausa aberta, a pausa é encerrada automaticamente (origem sistema) e o dia fecha — sem exigir duas correções; toast na UI
- Ponto (#842): calendário mensal em **Meu ponto** e **Ponto da equipe** (por atendente), com cores por meta de jornada (vermelho / verde / azul HE / laranja feriado); setting **jornada diária (minutos)** (padrão 480)
- Ponto (UX): **Meu ponto** redesenhado — relógio ao vivo, botão principal contextual (entrada / retomar / saída), cards de métricas, períodos de hoje e calendário mais legível (inspirado no DX Ponto)
- Ponto (#844): **geofence** — admin cadastra locais (lat/lon + raio), política de geo (opcional / recomendada / obrigatória); batidas fora da área ficam marcadas; link para mapa (OSM) no histórico admin
- Ponto: batida com **geolocalização** (lat/lon/precisão) — web e APK via `@capacitor/geolocation`; política da instância controla obrigatoriedade
- Ponto: **offline + sync** — batidas guardadas localmente quando sem rede e enviadas ao voltar online
- Ponto: **Ponto da equipe** alinhado visualmente a Meu ponto (digest em cards); relatório **PDF** e **Excel** mensal no filtro do histórico
- Ponto (#846–#851): CSV admin com colunas geo; mapa embutido (OSM) no admin; editar/desactivar locais; histórico Meu ponto com GPS/fora da área; estado optimista offline; checklist APK geo ampliado
- Faturamento (#326 / #363 / #364): faturas internas mensais para o financeiro conferir e **aprovar** (ou rejeitar com motivo). Geração automática no início do mês, ou avulsa na tela Faturamento; o botão do mês também reabre rejeitadas. Vencimento no **dia 10 do mês seguinte**. Na empresa, a flag **Emite NFS-e** (ligada por defeito) fica registada na fatura; boleto e nota fiscal só no lote seguinte, e só se a fatura estiver aprovada. O seed cria o setor **Financeiro** se ainda não existir.
- Sugestões (#799 / #800–#807): a partir de **Sobre** (Release Notes), enviar sugestão ou problema; acompanhar em **Minhas solicitações**; admin faz triagem e responde (público/interno) na instância
- WhatsApp (#837): **Exportar PDF** da conversa (header / menu ⋮) — relatório com protocolo, contacto e mensagens; mídia como rótulo; comentários internos excluídos; mesma permissão de ver o chat
- Configurações (#833): hub com **pesquisa** e cartões por domínio; menu reorganizado (Equipa e tickets, Canais, Comercial/CRM, Empresa e catálogos, Administração); URLs antigas redireccionam
- WhatsApp (#831): clicar no **número** do contacto (lista Em atendimento, Aguardando, histórico e header) copia automaticamente, com «Copiado!» discreto
- Alertas (#823): com a app/aba em **segundo plano**, a fila continua a chamar via notificação do sistema (re-alerta periódico + vibração no push); silenciar na mesa alinha com «Avisar fila» nas preferências
- WhatsApp (#827): mensagens **encaminhadas** pelo cliente mostram o rótulo «Encaminhada» (ou «Encaminhada muitas vezes») no balão do chat, como no WhatsApp
- Implantação (#325 / #358–#361): ao marcar o contrato como assinado, abre um ticket no setor configurado (Implantação ou Suporte) com checklist (documentos, WebPosto, PDVs, treino). O modelo é editável em Cadastros; o ticket só fecha com os itens obrigatórios feitos; o admin tem atalho para cadastrar PDVs da empresa
- Empresas (#824): na listagem, o **nome** fica em cima e o **CNPJ/CPF** em baixo no telemóvel (menos truncagem); botão para **copiar** o documento (só dígitos) com toast
- Atendimentos (#825): no telemóvel, Estado/datas/Atendente ficam num acordeão **Filtros** (recolhido por defeito) para a lista aparecer logo; a busca continua visível; badge indica filtros activos
- Mobile: o APK passa a usar o **mesmo painel** do browser no telemóvel (menu e rotas completos conforme RBAC); mantém Conta/slug, HTTP nativo e push
- Mobile: ícone do APK Android alinhado ao da PWA/computador (mark DeskRudder no fundo Deck)
- Mobile: no APK, **Meu ponto** (`/ponto`) abre de facto — deixava de cair na mesa de chat por falta de rota nativa
- Menu: grupo **Atendimentos** no menu lateral com **Chat**, **Tickets** e **Histórico** (toda a operação de atendimento junta)
- Menu (#793): **Ponto** (Meu ponto / Equipe online / Ponto da equipe) e **Chat** (Chat / Atendimentos) passam a ser grupos expansíveis no menu lateral, no mesmo padrão de Configurações
- WhatsApp (#788): gravação de áudio deixa de ficar presa em «A preparar microfone…» (o compositor reiniciava o MediaRecorder a cada render) e rejeita blobs vazios/truncados antes do envio; MIME preferido ogg/webm opus
- Mobile (#739): runbook de publicação na Play Store (textos de listing, checklist AAB, versão Android) e página pública de **privacidade** em `/privacidade` (URL para a Console)
- Controle de ponto (#761–#765 / #770–#772): entrada e saída pelo próprio utilizador; histórico com totais; admin vê a equipe e a visão do dia; no cadastro do atendente há flag **Usa escala** e ciclo personalizável (horas trabalhadas × horas de folga, ex. 12×36) com data de início
- Ponto (#766–#768): pausas (almoço) sem fechar o dia; ajustes manuais do admin com motivo e auditoria; exportação CSV da equipe
- Ponto (#769 / #773 / #774): banner de lembretes (online sem ponto / jornada longa / dia de escala sem entrada); indicador «Online sem ponto» na visão do dia; justificativas do utilizador com aprovação do admin
- Ponto (#778–#782): horário previsto e tolerância de atraso; feriados (nacionais + extras da instância) sem contar falta; banco de horas simples; digest diário do admin; fecho automático overnight opcional (desligado por padrão)
- Mobile: documentação do APK Android (checklist de validação + gerar AAB) e o build ignora o `VITE_API_URL` placeholder da CI
- Mobile: correções no APK — Conta/login sem ficar na empresa errada após falha ou «Trocar»; toque no alerta abre a conversa uma só vez; teclado no Android e no composer de tickets; envio sem double-tap (figurinha, portal, interno); safe area e rotas desconhecidas no app nativo
- Contratos (#355): ao rescindir contrato assinado, o sistema mostra estimativa de multa (`mín(meses de fidelidade restantes, teto) × mensalidade`) com aviso de que é só ajuda operacional — não é cobrança; a estimativa aparece também no cartão do contrato assinado; contrato cancelado deixa de mostrar dias de fidelidade restantes; ao assinar, CNPJ já cadastrado noutra Rede vincula a Empresa existente (sem erro)
- Contratos (#775): nos modelos de contrato, catálogo de chaves copiáveis (`{{contratada.*}}`, `{{contratante.*}}`, `{{contrato.*}}`) para o sistema preencher o HTML do cliente; multa e fidelidade passam a ser só dados (a cláusula fica no texto do modelo); preview com dados de exemplo
- Mobile chat (#747–#759): lista a 100% da largura; teclado sem vão/corte no campo; composer estilo WhatsApp; reagir pelo menu da seta; demanda e modais em folha inferior; header da app oculto na conversa; Encerrar/empresa/setor no telemóvel; empty states úteis; ícones PWA legíveis (fundo claro + contorno branco no desktop)
- Mobile (#737): no **app Android**, os alertas com a app fechada usam o mesmo canal da instância (sem Firebase); o clique abre a mesa certa
- Mobile (#735 / #736): app Android (instalação pelo APK) focado em **tickets e chat**; na primeira vez escolhes a **conta da empresa** (ex. duplexsoft) e nas seguintes o login já usa essa base
- Contratos comerciais (#324 / #349–#357): gerar PDF por CNPJ (fidelidade, setup, cláusulas, dados fiscais e nome da base WebPosto); reajuste padrão da instância ou override no contrato; anexar PDF assinado (ClickSign ou outro) com referência opcional; ao marcar assinado, cria ou vincula Rede e Empresa pelo CNPJ (sem PDVs), copia e-mail/telefone e cria contacto na rede para o chat; rascunho → enviado → assinado; lista com filtro por responsável; painel interno com custo, lucro e margem %; modelos em Cadastros. Na negociação, os dados fiscais ficam no gerar contrato; depois de assinado, a linha e o nome da Rede não se editam
- Proposta comercial (#323 / #345–#348): modelos HTML versionados, geração a partir da negociação (CNPJs à escolha), preview, PDF e marcar como enviada (com opção de avançar o funil) — sem custo/margem no documento do cliente
- CRM (#322 / #336–#344): perfil comercial, funil, leads e negociações multi-CNPJ (API + UI — lista/Kanban, detalhe com custos/margem e timeline); configuração dos estágios em Cadastros; simulação e leitura do catálogo de custos para comercial (CRUD do catálogo continua só admin)
- Sobre: as notas de atualização passam a mostrar só o que mudou no helpdesk nesta instância; melhorias do painel SaaS deixam de aparecer misturadas (#672 / #674)
- WhatsApp (#684): número do contacto visível no header da conversa (com copiar)
- WhatsApp (#681): clique na foto do contacto abre a imagem em tela cheia
- WhatsApp (#682): no telemóvel, dá para ocultar detalhes (protocolo, tags, demandas) e ver mais o chat
- WhatsApp (#680): vídeos da conversa abrem em overlay ampliado, com opção de tela cheia nativa
- WhatsApp (#679): documentos mostram e descarregam com o **nome original** do ficheiro (envio e recebimento)
- Chat (#654): a mesa de atendimento fica sempre no mesmo endereço (`/chat/atendendo`, `/chat/espera`, `/chat/interno`) — o número da conversa deixa de aparecer na barra do navegador e a conversa aberta continua no painel ao trocar de aba
- Tickets (#655): abrir um chamado mantém o endereço `/tickets`, sem o número do ticket na barra do navegador; ao voltar, a lista preserva filtros e página
- Notificações (#697): o sininho e o e-mail interno do painel já não põem o número do chamado ou da conversa no endereço; o clique abre o item certo na mesa ou em tickets
- Chat e tickets (#699): o Voltar do navegador fecha o painel da conversa ou do chamado e permanece na mesa (`/chat/…`, `/tickets`), sem o número na barra
- Portal (#700): chamados e atendimentos WhatsApp ficam em `/portal/tickets` e `/portal/chats`, sem o número na barra; links antigos com id continuam a abrir o item certo
- Mobile (#690 / #691): o painel no endereço do cliente pode ser **adicionado à tela inicial** (PWA); o brief mobile descreve PWA primeiro, depois lojas
- Mobile (#692): no telemóvel, WhatsApp e tickets dão para operar por completo — assumir, responder (texto/mídia), transferir, encerrar, abrir ticket; fila e detalhe do chamado com botões grandes e teclado que não cobre o campo de mensagem
- WhatsApp (#723): quem abre um chat em atendimento (colega ou admin) também vê o cronômetro de inatividade; Pausar/Retomar continua só com o responsável
- Notificações (#693 / #694): no telemóvel podes receber alertas mesmo com a app fechada — fila de espera e mensagens nos chats/tickets já teus. Activa em Notificações; o silêncio da fila na mesa também vale com a app fechada
- Mobile (#695): no iPhone, o painel explica que os alertas com a app fechada só funcionam depois de adicionar o DeskRudder à tela inicial (Safari 16.4+)
- Menu (#716): a barra de rolagem da sidebar (painel e portal) fica fina e alinhada ao tema, sem o visual nativo do Windows
- WhatsApp (#728): no modal da empresa do atendimento dá para **pesquisar pelo nome do posto**, em vez de só rolar a lista
- WhatsApp (#729): arrastar um ficheiro para a conversa abre a pré-visualização (como colar com Ctrl+V)
- WhatsApp (#730): no compositor há um atalho para **respostas prontas** do setor (insere o texto; o envio continua a ser teu)
- CI: testes do backend deixam de repetir bcrypt lento em cada caso; PRs só de interface já não esperam o pytest, e o contrário também (job do lado inalterado conclui em segundos)

#### Interno

- Licença: o repositório deixa a MIT e passa a **copyright reservado** (Luis Gustavo da S. Sousa); copiar, modificar ou usar sem autorização por escrito é proibido — ver `LICENSE`
- Mobile: brief (`MOBILE_APP_BRIEF.md`) alinhado ao estado real do épico #689 / L6 Android (PWA + Capacitor + listing docs; iOS = #738)
- Deploy (#734): ligação SSH ao VPS em IPv4, diagnóstico do IP do runner e segunda tentativa noutro runner só em timeout de rede
- Mobile (#735): `CORS_ORIGINS` das instâncias passa a incluir `https://localhost` (origem do WebView Android)
- Mobile (#735): projecto Capacitor Android no `frontend/` (`npm run build:android`); `stack-client.sh` documentado como `<comando> <slug>`

#### Correções

- Sugestões (#855): os botões **Criar issue no GitHub** / **Sincronizar GitHub** deixam de aparecer na triagem da instância (isso é trabalho da equipa DeskRudder no painel SaaS)
- Sugestões (#856): o admin da instância deixa de alterar status ou enviar notas de produto — a fonte de verdade é o painel SaaS
- Atendimentos (#826): no mobile, cards do histórico deixam de cortar telefone e **Retomar contacto** (layout em coluna, sem overflow horizontal)
- Chat: ao encerrar o atendimento na mesa, o painel fecha (como Voltar), em vez de ficar aberto com a lista vazia; se ainda falta classificar a demanda, o painel permanece
- Chat: o estado «Aguardando avaliação» passa a âmbar; «Encerrado» usa vermelho mais legível no tema escuro
- WhatsApp (#712): após registar demanda no chat aberto, o encerramento por inatividade continua a contar e o worker fecha o atendimento quando o prazo esgota (marco de demanda já não “prende” o relógio em 00:00)
- Dark mode (#713): texto e caixa de confirmação ao concluir sem demanda ficam legíveis no tema escuro
- Sobre (#672): notas antigas que começam com «SaaS» deixam de aparecer em `/sobre` mesmo se o histórico foi publicado antes da separação por produto
- Login (#677): em subdomínio do cliente, **Voltar ao site** abre a landing DeskRudder (apex) em vez de voltar ao próprio login
- Funcionários da rede (#685): ao editar/criar, o formulário volta a mostrar o topo e a rolar até ao fim — sem espaço vazio abaixo dos botões nem conteúdo preso fora do ecrã
- Links antigos (#654 / #655 / #700): endereços com número (chat da fila, conversa do WhatsApp, detalhe de ticket no painel ou no portal) continuam a funcionar e abrem o item certo no novo formato
- Chat (#698): a mesa deixa de gravar a conversa aberta só por desenhar a lista — só o clique (ou o sininho) muda o painel
- WhatsApp (#683): envio de mensagem/áudio/anexo já não mostra toast verde que cobria o botão de enviar (erros continuam)

### SaaS Control Plane

#### Melhorias

- Fila de **sugestões/bugs** das instâncias (#855 / #808): quem usa o DeskRudder abre o pedido nas Release Notes; a cópia autenticada chega a `/saas/solicitacoes` (lista + detalhe). Token no provisionamento, não no browser do cliente. **Prints e anexos** da instância também chegam ao painel (não só o texto).
- Triagem da fila (#856): `saas_ops` altera status e responde (público/interno) em `/saas/solicitacoes/{id}`. O que é público (e o status) volta à instância — apply directo no control-plane local, ou pull autenticado `GET /v1/saas/ingest/solicitacoes/sync` nas instâncias. Notas internas e GitHub não aparecem ao cliente.
- Fila de sugestões (#857): o **Cursor** lista e actualiza a fila SaaS (status, comentários, link da issue GitHub) via MCP. O cliente não vê Cursor nem GitHub; no painel ops aparece a issue se estiver ligada.
- Painel SaaS: página **Sobre / Novidades** com o histórico só de entregas do control-plane (licenças, planos, provisionamento) (#672 / #675)
- Release notes: CHANGELOG e API separam DeskRudder e SaaS no mesmo deploy CalVer (#672 / #673 / #676)

#### Correções

- Landing (#668): modal «Quero ver uma demonstração» fica centrado na tela, com scroll se o formulário for alto (deixa de cortar Nome/E-mail)

<!-- Adicione bullets sob ### DeskRudder ou ### SaaS Control Plane. Ver docs/RELEASES.md. -->


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
