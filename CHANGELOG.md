# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Versão CalVer (`YY.MM.NNN`) é atribuída automaticamente no deploy de `staging`.

## [Unreleased]

### DeskRudder

#### Correções

- Listagens (tema escuro): hover das linhas de tabela deixa de «lavar» o texto — contraste alinhado ao padrão das telas SaaS (#921 / #S202608-0001)

## [26.08.018] - 2026-08-28

### SaaS Control Plane

#### Melhorias

- Provisionamento: URL de ingest gravada no `client.env` usa **loopback** (`127.0.0.1:8001`) por padrão — evita falha de sync quando instância e admin-center estão na mesma VPS

### DeskRudder

#### Melhorias

- **Minhas solicitações** e bloco no **Sobre**: lista em tabela com badges; no Sobre só as **5 mais recentes** com atalho **Ver todas**; filtros por tipo, fase, status e busca; detalhe com timeline e mensagem de status por fase
- **Nova solicitação**: seletor visual de tipo (chips), textos em pt-BR, anexos removíveis antes do envio e imagens coladas listadas com opção de remover
- **Acompanhamento**: linha do tempo vertical no detalhe do pedido; skeleton da tabela no Sobre enquanto carrega
- Ponto (#985): dia convocado — admin agenda trabalho fora da grade com janela própria; calendário, faltas e banco de horas respeitam a exceção
- Ponto (#S202608-0011): histórico da equipe paginado (20 batidas por página, com total e navegação)

#### Correções

- Deploy: migration do dia convocado (#985) idempotente — instâncias com tabela criada manualmente não travam no `alembic upgrade`
- Atendimentos (#S202608-0010): contador de mensagens não lidas no chat alinhado entre sino, lista e conversa; badge some ao responder; divisor «Mensagens não lidas» também no chat do portal

## [26.08.017] - 2026-08-27

### DeskRudder

#### Melhorias

- Ponto (#968 / #972 / #971): lembrete in-app de entrada/saída na janela de tolerância; resumo semanal em Meu ponto (previsto × feito, atrasos, HE, banco); motivo obrigatório reforçado e histórico/export de ajustes admin (também no PDF/Excel mensal)
- Ponto (#966): admin **concede hora extra** com antecedência (resto do dia, até horário ou duração em minutos); teto opcional por colaborador no cadastro; liberações respeitam o teto
- Ponto (#976 / #977 / #973): férias e folga programada (pedido do colaborador ou agendamento admin); justificativa com anexo (imagem/PDF); alerta de pausa abaixo do mínimo configurável
- Ponto (#969 / #974 / #982): colaborador **solicita hora extra** com janela desejada; teto mensal (global ou por pessoa) bloqueia novas liberações; digest e Meu ponto mostram consumo; avisos em tempo real (`ponto.he_atualizada`)
- Ponto (#981 / #980 / #978 / #979): checklist de configuração pós-deploy; ajuda **Como funciona o ponto**; **fechamento de competência** mensal (reabrir com motivo; ajustes pós-fechamento marcados); **ciência** do colaborador no espelho após o fechamento
- Ponto (#975 / #970): **export contábil/folha RH** (CSV e Excel) com matrícula, previsto/realizado, atrasos, faltas, HE, banco e ajustes; **cobertura de plantão** (A pede → B aceita → admin homologa, ou admin agenda direto) refletida no calendário e nas faltas

#### Correções

- Atendimentos (#996 / #S202608-0007): na tela de chats, a barra superior (menu, notificações) volta a aparecer no computador; no celular continua oculta com a conversa aberta
- Atendimentos (#998 / #S202608-0009): quem só acompanha o chat deixa de ver **Encerrar** e **Registrar demanda** — esses botões ficam só com o responsável

## [26.08.016] - 2026-08-26

### SaaS Control Plane

#### Melhorias

- Infra: no deploy, pedidos citados no CHANGELOG passam a **concluída** no painel admin (versão do release); o script usa o mesmo stack Docker do admin-center
- Sobre: notas **Interno / Infra** (deploy, LICENSE, briefs) deixam de aparecer no DeskRudder — ficam só no painel admin
- Release notes: versão **26.08.015** sem bullets duplicados de releases anteriores (lista gigante no Sobre)

### DeskRudder

#### Correções

- Sobre: deixa de listar itens **Interno / Infra** (deploy, LICENSE, docs internos) — só Melhorias e Correções de produto
- Sobre: versão **26.08.015** sem repetir notas já publicadas em releases anteriores

## [26.08.015] - 2026-08-26

### SaaS Control Plane

#### Melhorias

- Sugestões (#953 / #954): máquina de estados rígida na triagem (só avanços permitidos); **Implementar** cria ou liga issue no GitHub e só então marca em desenvolvimento — o cliente continua sem ver o GitHub
- Sugestões (#955–#957): quando o pedido é **concluído** no deploy, Minhas solicitações mostra **Disponível a partir da versão X (ou superior)** — a versão vem do release real (CalVer), não há previsão manual em planejada/desenvolvimento; rule Cursor para só codar com protocolo + issue ligada
- Docs (#879): MCP aponta a `api.deskrudder.com.br`; runbook para desativar cliente sem derrubar o painel SaaS; arquitetura pós-cutover (admin-center vs compose legado)
- Painel admin: cabeçalho com **Painel admin SaaS** + usuário logado (nome e cargos); **Equipe** com Usuários / Setores / Minha conta; removido o atalho «Painel atendimento»
- Equipe SaaS: cadastro de **setores/cargos** (Admin, Desenvolvimento, Comercial, …) sem campo ordem; um usuário pode ter **vários** cargos; o cabeçalho mostra os nomes em vez de só «Ops SaaS»
- Minha conta: além do token Cursor, o ops edita **nome**, **e-mail** e **senha**
- Licenças: coluna **Valor/mês** com valor negociado (ou estimativa do catálogo); campo opcional na ficha para negociação diferente do plano
- Catálogo comercial: **preço por módulo**; plano = soma dos módulos habilitados; licença pode misturar (ex. Essencial + 1 módulo Enterprise); **3 usuários inclusos** + R$ 10/usuário extra (editável no plano)
- Catálogo comercial: módulos do produto pré-cadastrados; planos Trial / Essencial / Profissional / Enterprise (sem teto de postos nem tickets)
- Sugestões: na fila, chips de **tipo** (Sugestão / Erro) e **fase** (Aguardando, Em desenvolvimento, Finalizadas), com contadores; badges coloridos na lista e no detalhe
- Fila de **sugestões/bugs** das instâncias (#855 / #808): quem usa o DeskRudder abre o pedido nas Release Notes; a cópia autenticada chega a `/saas/solicitacoes` (lista + detalhe). Token no provisionamento, não no browser do cliente. **Prints e anexos** da instância também chegam ao painel (não só o texto).
- Triagem da fila (#856): `saas_ops` altera status e responde (público/interno) em `/saas/solicitacoes/{id}`. O que é público (e o status) volta à instância — apply directo no control-plane local, ou pull autenticado `GET /v1/saas/ingest/solicitacoes/sync` nas instâncias. Notas internas e GitHub não aparecem ao cliente.
- Fila de sugestões (#857): o **Cursor** lista e actualiza a fila SaaS (status, comentários, link da issue GitHub) via MCP. O cliente não vê Cursor nem GitHub; no painel ops aparece a issue se estiver ligada.

#### Interno / Infra

- Licença: o repositório deixa a MIT e passa a **copyright reservado** (Luis Gustavo da S. Sousa); copiar, modificar ou usar sem autorização por escrito é proibido — ver `LICENSE`

### DeskRudder

#### Melhorias

- Ponto (#968 / #972 / #971): lembrete in-app de entrada/saída na janela de tolerância; resumo semanal em Meu ponto (previsto × feito, atrasos, HE, banco); motivo obrigatório reforçado e histórico/export de ajustes admin (também no PDF/Excel mensal)
- Ponto (#966): admin **concede hora extra** com antecedência (resto do dia, até horário ou duração em minutos); teto opcional por colaborador no cadastro; liberações respeitam o teto
- Ponto (#965): após o fim da jornada, **pegar** chat WhatsApp novo fica bloqueado até um admin liberar **hora extra** (resto do dia ou até um horário); pedidos aparecem em Ponto da equipe e no sino de pendências
- Ponto (#984): locais de trabalho no **cadastro do atendente** (empresa + extras no mapa OSM); pin da empresa em Configurações → Empresa; raio e ativar/desativar por local; removido o card global de Locais em Ponto da equipe
- Chat interno (#941 / #S202608-0008): no canal de **setor**, clicar no nome abre modal com membros vinculados e quem está **online**
- WhatsApp / Portal (#943 / #S202608-0002): no modal de **encerrar** atendimento, **Concluir/Encerrar** fica azul (ação principal) e **Cancelar** vermelho — deixa de confundir dois botões iguais
- WhatsApp / Portal (#951 / #S202608-0004): contador de **mensagens não lidas** na lista Atendendo e divisor «Mensagens não lidas» ao abrir a conversa (continua de onde parou)
- Ponto (#959 / #960–#964 / #961–#963): jornada **semanal** (grade Dia/Aberto/Início/Fim como no chat) ou **ciclo** X×Y, ou **nenhum**; entrada só a partir de início−tolerância; atraso só após início+tolerância; fecho por esquecimento (N horas **ou** saída prevista+margem); alertas in-app de falta/atraso para colaborador e admin
- Chat interno (#916): cada setor activo passa a ter canal próprio (criação ao cadastrar/activar + backfill); canais vazios aparecem em Interno → Setores; o vínculo do atendente ao setor basta para ver o canal; admin vê todos

#### Correções

- WhatsApp (#945 / #S202608-0003): **Exportar PDF** só aparece em chats finalizados (encerrado ou aguardando avaliação), não durante o atendimento
- WhatsApp (#947 / #S202608-0005): ao abrir o menu Editar/Apagar/Reagir (ou editar mensagem), o strip de emojis do hover deixa de cobrir as opções
- Sugestões (#855): os botões **Criar issue no GitHub** / **Sincronizar GitHub** deixam de aparecer na triagem da instância (isso é trabalho da equipa DeskRudder no painel SaaS)
- Sugestões (#856): o admin da instância deixa de alterar status ou enviar notas de produto — a fonte de verdade é o painel SaaS
- Atendimentos (#826): no mobile, cards do histórico deixam de cortar telefone e **Retomar contacto** (layout em coluna, sem overflow horizontal)


## [26.08.014] - 2026-08-25

### SaaS Control Plane

#### Melhorias

- Infra (#880): deploy GitHub Actions atualiza **duas** stacks — build/dist DuplexSoft e build/dist comercial; migrate em cada Postgres; health com flags SaaS distintas
- Infra: `stack-client.sh migrate` fecha o stdin (`-T` + `/dev/null`) para o `docker compose run` não engolir o resto do script SSH no deploy do admin-center
- Infra (#876 / #877 / #878): painel admin em `api.deskrudder.com.br` + SPA em `deskrudder.com.br`; fila e contas ops migradas para o Postgres comercial; DuplexSoft passa a só **ingerir** sugestões (control-plane desligado nessa instância)
- Infra (#876): stack `admin-center` sobe com Postgres TLS (self-signed) e `DATABASE_URL` com `sslmode=require`, exigido em produção

### DeskRudder

#### Melhorias

- WhatsApp (mobile): ao **Atender**, o modal de setor fica **centralizado** com lista tocável (sem dropdown cortado no rodapé); o Select genérico também abre para cima quando não há espaço abaixo
- Infra (#876): stacks de cliente (`deploy/clients/`) também sobem Postgres com TLS e `sslmode=require` em produção

## [26.08.013] - 2026-08-25

### SaaS Control Plane

#### Melhorias

- Sobre (#920): o painel ops lista **todas** as notas da versão, com etiqueta **Produto** ou **DevOps**. O helpdesk nas instâncias continua a ver só as de produto
- Login do painel admin: em produção deixa de aparecer a dica de desenvolvimento (e-mail local)
- Sugestões (#923): detalhe com **linha do tempo** (pedido + mensagens ao cliente); notas internas em cartão âmbar; status em passos clicáveis, como nos tickets
- Sugestões: textos de acompanhamento em português do Brasil; mensagem ao cliente **não pode citar** GitHub nem número de issue (isso fica na nota interna)
- Painel ops: menu **Equipe** (Usuários + Minha conta); **Sobre** e **Sair** no rodapé, no mesmo padrão do painel de atendimento
- Cursor: textos ao cliente e do MCP em **português do Brasil**; comentário sem flag explícita fica **interno**. O comando `/listar-solicitacoes` passa a ir no repositório; o MCP aponta para `api.deskrudder.com.br` (control-plane, #875), não para a API da DuplexSoft
- Infra (#876 / #877): stack do **painel admin** em `deploy/admin-center/` (Postgres + API em `127.0.0.1:8001`). Hosts: `deskrudder.com.br` e `api.deskrudder.com.br`. O helpdesk DuplexSoft continua na API `api-duplexsoft`

### DeskRudder

#### Correções

- Deploy: migration do chat interno (#916) usava um ID Alembic maior que 32 caracteres e quebrava o `upgrade` em produção; ID encurtado para caber em `alembic_version`

#### Melhorias

- WhatsApp: seleção de **Empresa do atendimento** no modal — lista deixa de ficar cortada/desproporcional (menu no fluxo do formulário; modal um pouco mais estreito)
- Configurações (#865): menu reorganizado — **Equipe** e **Tickets** separados; Tipos de negócio em Comercial/CRM; Catálogos PDV em **PDV**; Empresa só com dados da instalação; URLs antigas redirecionam
- Chat interno (#916): cada setor ativo passa a ter canal próprio (criação ao cadastrar/ativar + backfill); canais vazios aparecem em Interno → Setores; o vínculo do atendente ao setor basta para ver o canal; admin vê todos
- Sobre (#920): esta página mostra só melhorias de **produto**; as de DevOps não entram na lista

## [26.08.012] - 2026-08-24

### SaaS Control Plane

#### Melhorias

- Fila de sugestões no Cursor: cada ops gera o **próprio token** em Conta / Cursor (`/saas/conta`) e cola no Cursor. Recusar ou comentar fica ligado a essa conta, não a um segredo partilhado da VPS
- Painel SaaS: cadastro da **equipa** (`/saas/usuarios`) — contas do `/login/admin`. Senha temporária uma vez; cada pessoa gera o token Cursor na própria conta
- Login ops: no primeiro acesso (trocar senha) o painel SaaS já não mostra «não disponível nesta instância»; redirecciona para definir senha nova

### DeskRudder

#### Melhorias

- UI (#870): responsividade — coluna principal do painel ocupa sempre a largura disponível (grid + `w-full`/`min-w-0` no Layout); contentores internos alinhados; abas e header legíveis em qualquer largura
- UI (#866): botão **Cancelar** com gradiente vermelho preenchido (mesmo molde do Salvar), distinto de Excluir; ConfirmDialog, portal e formulários alinhados

## [26.08.011] - 2026-08-22

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

## [26.08.010] - 2026-08-20

### DeskRudder

#### Melhorias

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

#### Interno / Infra

- Mobile: brief (`MOBILE_APP_BRIEF.md`) alinhado ao estado real do épico #689 / L6 Android (PWA + Capacitor + listing docs; iOS = #738)
- Deploy (#734): ligação SSH ao VPS em IPv4, diagnóstico do IP do runner e segunda tentativa noutro runner só em timeout de rede
- Mobile (#735): `CORS_ORIGINS` das instâncias passa a incluir `https://localhost` (origem do WebView Android)
- Mobile (#735): projecto Capacitor Android no `frontend/` (`npm run build:android`); `stack-client.sh` documentado como `<comando> <slug>`

## [26.08.009] - 2026-08-18

### DeskRudder

#### Melhorias

- Proposta comercial (#323 / #345–#348): modelos HTML versionados, geração a partir da negociação (CNPJs à escolha), preview, PDF e marcar como enviada (com opção de avançar o funil) — sem custo/margem no documento do cliente
- Mobile (#692): no telemóvel, WhatsApp e tickets dão para operar por completo — assumir, responder (texto/mídia), transferir, encerrar, abrir ticket; fila e detalhe do chamado com botões grandes e teclado que não cobre o campo de mensagem
- WhatsApp (#723): quem abre um chat em atendimento (colega ou admin) também vê o cronômetro de inatividade; Pausar/Retomar continua só com o responsável
- Notificações (#693 / #694): no telemóvel podes receber alertas mesmo com a app fechada — fila de espera e mensagens nos chats/tickets já teus. Activa em Notificações; o silêncio da fila na mesa também vale com a app fechada
- Mobile (#695): no iPhone, o painel explica que os alertas com a app fechada só funcionam depois de adicionar o DeskRudder à tela inicial (Safari 16.4+)
- WhatsApp (#728): no modal da empresa do atendimento dá para **pesquisar pelo nome do posto**, em vez de só rolar a lista
- WhatsApp (#729): arrastar um ficheiro para a conversa abre a pré-visualização (como colar com Ctrl+V)
- WhatsApp (#730): no compositor há um atalho para **respostas prontas** do setor (insere o texto; o envio continua a ser teu)

#### Correções

- Chat: ao encerrar o atendimento na mesa, o painel fecha (como Voltar), em vez de ficar aberto com a lista vazia; se ainda falta classificar a demanda, o painel permanece
- Chat: o estado «Aguardando avaliação» passa a âmbar; «Encerrado» usa vermelho mais legível no tema escuro

## [26.08.008] - 2026-08-17

### DeskRudder

#### Melhorias

- Chat (#654): a mesa de atendimento fica sempre no mesmo endereço (`/chat/atendendo`, `/chat/espera`, `/chat/interno`) — o número da conversa deixa de aparecer na barra do navegador e a conversa aberta continua no painel ao trocar de aba
- Tickets (#655): abrir um chamado mantém o endereço `/tickets`, sem o número do ticket na barra do navegador; ao voltar, a lista preserva filtros e página
- Notificações (#697): o sininho e o e-mail interno do painel já não põem o número do chamado ou da conversa no endereço; o clique abre o item certo na mesa ou em tickets
- Chat e tickets (#699): o Voltar do navegador fecha o painel da conversa ou do chamado e permanece na mesa (`/chat/…`, `/tickets`), sem o número na barra
- Portal (#700): chamados e atendimentos WhatsApp ficam em `/portal/tickets` e `/portal/chats`, sem o número na barra; links antigos com id continuam a abrir o item certo
- Mobile (#690 / #691): o painel no endereço do cliente pode ser **adicionado à tela inicial** (PWA); o brief mobile descreve PWA primeiro, depois lojas
- Menu (#716): a barra de rolagem da sidebar (painel e portal) fica fina e alinhada ao tema, sem o visual nativo do Windows
- CI: testes do backend deixam de repetir bcrypt lento em cada caso; PRs só de interface já não esperam o pytest, e o contrário também (job do lado inalterado conclui em segundos)

#### Correções

- WhatsApp (#712): após registar demanda no chat aberto, o encerramento por inatividade continua a contar e o worker fecha o atendimento quando o prazo esgota (marco de demanda já não “prende” o relógio em 00:00)
- Dark mode (#713): texto e caixa de confirmação ao concluir sem demanda ficam legíveis no tema escuro
- Sobre (#672): notas antigas que começam com «SaaS» deixam de aparecer em `/sobre` mesmo se o histórico foi publicado antes da separação por produto
- Funcionários da rede (#685): ao editar/criar, o formulário volta a mostrar o topo e a rolar até ao fim — sem espaço vazio abaixo dos botões nem conteúdo preso fora do ecrã
- Links antigos (#654 / #655 / #700): endereços com número (chat da fila, conversa do WhatsApp, detalhe de ticket no painel ou no portal) continuam a funcionar e abrem o item certo no novo formato
- Chat (#698): a mesa deixa de gravar a conversa aberta só por desenhar a lista — só o clique (ou o sininho) muda o painel

## [26.08.007] - 2026-08-14

### DeskRudder

#### Melhorias

- CRM (#322 / #336–#344): perfil comercial, funil, leads e negociações multi-CNPJ (API + UI — lista/Kanban, detalhe com custos/margem e timeline); configuração dos estágios em Cadastros; simulação e leitura do catálogo de custos para comercial (CRUD do catálogo continua só admin)
- Sobre: as notas de atualização passam a mostrar só o que mudou no helpdesk nesta instância; melhorias do painel SaaS deixam de aparecer misturadas (#672 / #674)
- WhatsApp (#684): número do contacto visível no header da conversa (com copiar)
- WhatsApp (#681): clique na foto do contacto abre a imagem em tela cheia
- WhatsApp (#682): no telemóvel, dá para ocultar detalhes (protocolo, tags, demandas) e ver mais o chat
- WhatsApp (#680): vídeos da conversa abrem em overlay ampliado, com opção de tela cheia nativa
- WhatsApp (#679): documentos mostram e descarregam com o **nome original** do ficheiro (envio e recebimento)

#### Correções

- Login (#677): em subdomínio do cliente, **Voltar ao site** abre a landing DeskRudder (apex) em vez de voltar ao próprio login
- WhatsApp (#683): envio de mensagem/áudio/anexo já não mostra toast verde que cobria o botão de enviar (erros continuam)

### SaaS Control Plane

#### Melhorias

- Painel SaaS: página **Sobre / Novidades** com o histórico só de entregas do control-plane (licenças, planos, provisionamento) (#672 / #675)
- Release notes: CHANGELOG e API separam DeskRudder e SaaS no mesmo deploy CalVer (#672 / #673 / #676)

#### Correções

- Landing (#668): modal «Quero ver uma demonstração» fica centrado na tela, com scroll se o formulário for alto (deixa de cortar Nome/E-mail)

## [26.08.006] - 2026-08-12

### Melhorias

- WhatsApp: ao iniciar conversa com número avulso e o cliente responder, deixa de abrir chat novo na fila (alerta de «novo atendimento») quando o `wa_id` chega em variante (DDI / nono dígito BR) ou como `@lid` com `senderPn` / `remoteJidAlt`
- WhatsApp (#667): em Atendimentos (e Avaliações), **Próxima** / **Anterior** deixam de voltar sozinhas para a página 1; o `offset` da URL é respeitado ao abrir/recarregar
- Chat (#651): **Silenciar** na fila Aguardando corta o alerta na hora (loop + pulse); o toque passa a tocar completo e a reiniciar em sequência, sem intervalo de silêncio
- WhatsApp (#653): **Esc** na conversa já não percorre o histórico do browser (evita reabrir chat encerrado); fecha overlays locais e, ao sair, vai à lista de origem (Atendendo / Aguardando / etc.)
- Chat (#652): com a aba em segundo plano, novo chat na fila dispara notificação do sistema (se permitida) e o áudio é desbloqueado no primeiro clique; ao voltar à aba o alerta retoma de imediato
- Chat (#652): banner no painel pede permissão de notificações («Ativar alertas») para avisar novos chats na fila mesmo com outra aba ou o navegador minimizado
- SaaS: **controle de licenças** — histórico/timeline na ficha, snapshot de módulos + limites na licença, preço/limites nos planos, e-mail de entrega com plano/módulos/acesso, conversão de lead com plano, `SAAS_MODULOS` no provisionamento e lista de instâncias no resumo
- SaaS: catálogo comercial de **planos e módulos** (CRUD, activar/desactivar, seed Trial/Profissional/Enterprise); licença escolhe plano em vez de texto livre
- SaaS: lista de licenças com **filtros** (plano, aprovação, provisionamento, renovação), cartões do resumo clicáveis e **escolha de plano** ao aprovar go-live
- SaaS: URL da instância deixa de ser campo livre — só o **nome da base (slug)**; URL = `https://{slug}.{domínio}/`; em local o «Abrir» usa a porta API (DNS público não resolve)
- SaaS: trial só **pede aprovação**; **Aprovar e criar base** enfileira a criação da instância/Postgres
- SaaS: **entrega pós-health** ao contacto (`entrega_notificada_em` + `reenviar-entrega`)
- SaaS: lead → licença com **vínculo persistido** (`POST ./leads/{id}/converter` + `lead_id` no formulário)
- SaaS: **suspender/reativar** pede (ou executa) `stack-client.sh down|up` e confirmação ops
- SaaS: trial público entra com **aprovação pendente**; painel com **Aprovar go-live** / **Rejeitar** (`aprovacao_status`)
- SaaS DeskRudder (#519 / #516 / #521–#528): painel de **licenças** (contactos, resumo ops, renovação flexível, lead→licença); **leads comerciais** da landing (formulário «Fale conosco», inbox `/saas/leads`); **provisionamento** em fila; **trial** em `/trial`; **renovações** com alertas e suspensão ao vencer
- Comercial (#321 / #331–#335): simulador com desconto posto <100k L (20% SM), override de custo/valor TEF só na proposta e snapshot imutável do pacote (catálogo TEF continua com valores padrão)
- Comercial (#321 / #329–#334): catálogo de custos — salário mínimo com histórico por vigência (atualizar valor sem reescrever o passado), itens (% SM, valor fixo, TEF) e simulador em Cadastros → Catálogo de custos (admin)

## [26.08.005] - 2026-08-03

### Melhorias

- Dashboard (#599): filtros de período Hoje | Esta semana (seg–dom) | Este mês | Mês passado | Personalizado no geral, tickets e WhatsApp (substitui 7/30/90); CSAT do geral respeita o intervalo
- WhatsApp (#594): análise de demandas no dashboard — drill-down por natureza/motivo, ranking por empresa, insights (erro → atualização; dúvida → treinamento) e sugestão de novo motivo a partir de «Outros» repetido
- Rede e Empresa (#595): aba Análises com tickets + demandas WhatsApp no período, insights e ranking (reutiliza #594/#599)

## [26.08.004] - 2026-08-02

### Melhorias

- WhatsApp: na visualização ampliada de imagens, dá para fazer zoom (+/−, scroll e duplo clique), rodar e arrastar; repor volta à vista normal (também no chat interno)
- Chat: duplo clique **dentro** do balão já não inicia resposta (dá para selecionar/copiar o texto); responder com duplo clique fica só **ao lado** do balão
- WhatsApp: menu com seta no canto do balão para Editar/Apagar (em vez de botões flutuantes que saltavam para a mensagem de cima)
- WhatsApp: Enter na legenda do anexo deixava de enviar a imagem **duas vezes** (o evento subia ao painel e disparava o envio de novo)

## [26.08.003] - 2026-08-02

### Melhorias

- WhatsApp (#628): ao atender com vários setores, o modal «Escolher setor» voltava vazio (pedido com `limit` acima do máximo da API); a lista passa a carregar com paginação válida

## [26.08.002] - 2026-08-02

### Melhorias

- Frontend: alinhamento de `react` e `react-dom` em **19.2.8** (o Dependabot tinha subido só o `react`, o que gerava tela preta com React error #527 em produção)

## [26.08.001] - 2026-08-02

### Melhorias

- WhatsApp (#628): no WhatsApp do cliente, mensagens do atendente saem com prefixo **setor do atendimento + nome** e o texto na linha de baixo (ex.: `[ Suporte - Ana ]:`); ao assumir, 1 setor é gravado automaticamente e vários setores pedem escolha no painel
- WhatsApp (#629): no lightbox de imagens da conversa, dá para navegar entre as fotos (botões e setas ←/→) com contador e legenda atualizada; Esc continua a fechar só a visualização
- WhatsApp (#630): foto de perfil do contacto no header e nas listas Atendendo/Aguardando (com cache e fallback para a inicial do nome)
- WhatsApp (#630): reações no chat com o cliente — ver emoji do cliente no balão e o atendente responsável pode reagir (👍 ❤️ 😂 😮 😢 🙏); clique de novo remove
- WhatsApp (#630): editar (até 15 min) e apagar para todos (até 48 h) mensagens de texto enviadas pelo responsável; também sincroniza quando o cliente edita ou apaga
- WhatsApp: no header da conversa, o chip da empresa abre a página de detalhe da empresa (Voltar regressa ao chat); alterar empresa multi-empresa continua no menu ⋮
- Chat (#626): ícone de som junto a **Aguardando** para silenciar/reativar o alerta contínuo da fila (WhatsApp + portal); preferência guardada no browser — não afeta alertas de ticket nem do chat interno
- Chat (#625): ao **Ver** um chat da fila Aguardando, a lista com **Atender** permanece na lateral; na conversa há CTA **Atender** (WhatsApp e portal) para assumir sem voltar à lista
- WhatsApp (#627): com anexo pendente, **Enter** na legenda (ou no painel, em áudio) envia o anexo — equivalente a «Enviar anexo»
- Login / site: «Voltar ao site» e hosts DeskRudder apontam para deskrudder.com.br (redirect da apex connect)

## [26.07.014] - 2026-07-22

### Melhorias

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
- Chat (#607): na aba **Atendendo**, secções **Comigo** e **Outros atendentes** quando o admin acompanha colegas; badge «Você» e destaque visual nos seus; nome do responsável legível nos de outros
- WhatsApp (#606): conversa mais utilizável no **mobile** — composer com campo largo e botão de manuais só ícone; menu **⋮** com Transferir/Tickets; metadados em linha separada; painel de demandas colapsável; `safe-area` no composer
- WhatsApp (#608): duas mensagens inbound seguidas do mesmo contacto deixam de abrir dois chats/protocolos — lock por `wa_id` no webhook e uma única sequência de auto-mensagens por sessão
- WhatsApp (#598): após encerrar com avaliação, janela de ~30 min (configurável) para a nota; se o cliente mandar outro texto, abre atendimento novo com essa mensagem; sem resposta, finaliza sozinho

## [26.07.013] - 2026-07-18

### Melhorias

- WhatsApp (#577): countdown até o aviso e, após o aviso, até encerrar; enviar mensagem (ou o cliente falar) sai automaticamente da pausa
- WhatsApp: após encerramento por inatividade, o chat fica em **A classificar demanda** (somente leitura) até registar, manter demandas existentes ou confirmar sem demanda; nova mensagem do mesmo cliente abre chat novo na fila
- WhatsApp (#575): ticks de entrega/leitura no painel passam a atualizar (✓✓ / ✓✓ azul) — o webhook da Evolution com `keyId` + `DELIVERY_ACK`/`READ` era ignorado; mark-as-read no WhatsApp do cliente também quando chega mensagem nova com o responsável no chat

## [26.07.012] - 2026-07-18

### Melhorias

- WhatsApp (#577): encerramento por inatividade conta desde a **última mensagem** (cliente ou atendente); botão **Pausar/Retomar** com countdown no chat
- WhatsApp (#575): ✓✓ azul no WhatsApp do cliente só quando o **atendente responsável** abre o chat no painel
- WhatsApp (#568): ao anexar imagem, só o campo de legenda fica visível (sem o composer por baixo)
- WhatsApp (#569/#572/#574): legenda de mídia com a mesma fonte do texto; PDF/vídeo mostram legenda; sem placeholder «[Imagem enviada]» quando não há legenda
- WhatsApp (#571): Esc no zoom da imagem fecha só a visualização, sem sair do chat
- WhatsApp (#576): cancelar gravação de áudio já não envia o ficheiro
- WhatsApp (#573): ao reabrir o chat, o scroll volta à última posição vista (não salta para o início)
- WhatsApp (#570): contacto já vinculado é reconhecido em chats novos do mesmo número

## [26.07.011] - 2026-07-17

### Melhorias

- PDVs: código editável na edição (ex.: 001 ↔ 002 ao trocar equipamento); listagem mostra só o código, sem prefixo «PDV»; colunas separadas de acesso remoto, ID e senha (copiar ID/senha; revelar senha com o olho)
- Modo escuro: texto digitado nos campos de pesquisa (listagens e chat interno) volta a ficar legível

## [26.07.010] - 2026-07-17

### Melhorias

- Chat interno: alerta sonoro ao receber nova mensagem; em grupos, opção de **Silenciar** / **Ativar som** (preferência por pessoa)
- Chat interno: ao passar o mouse em mensagens próximas, as opções (Responder/Editar/Apagar) e reações não “saltam” mais para a mensagem de cima

## [26.07.009] - 2026-07-16

### Melhorias

- Chat interno (grupos/canal): menções com `@` — autocomplete de participantes e `@all` (todos); destaque visual na mensagem
- Equipe online: lista funciona com vários workers do servidor (presença gravada no banco); admin pode **Forçar saída** de um atendente conectado
- Chat interno: balões mais próximos — opções/reações só no hover; em grupos, avatar e cor por pessoa para distinguir quem fala
- Equipe online: «0 online» mesmo com painel aberto (lista lia só a memória do worker errado)
- Chat interno: espaço excessivo entre mensagens após colocar ações/reações fora do balão

## [26.07.008] - 2026-07-16

### Melhorias

- Equipe online (#545–#547): administradores veem quem está com o painel aberto e desde quando (menu **Equipe online**), para coordenar atendimento de chats e tickets
- Chat interno: no grupo, clique no nome na barra superior para ver participantes e administradores; admins promovidos também podem gerenciar membros
- WhatsApp: na busca «Vincular existente», cada resultado mostra **rede** e **empresa(s)** para distinguir homónimos
- WhatsApp (#534): identificar/cadastrar contato do cliente também em atendimento **encerrado** (Histórico); o número do WhatsApp passa a ser gravado no telefone do cadastro para retomar pela aba Contatos
- WhatsApp (#531): aba **Contatos** no hub de chat — lista funcionários com empresa e telefone; iniciar conversa (ou número avulso / retomar no Histórico); chat já fica em atendimento com o iniciador; telefone no cadastro do funcionário da rede
- WhatsApp: o feed deixa de puxar sozinho para o fim enquanto você lê mensagens acima; ao reabrir a conversa, retoma a posição em que parou
- Chat interno: ações (Responder/Editar/Apagar) e reações ficam fora do balão da mensagem
- Chat interno: clique na imagem abre visualização em tela cheia (antes só tinha o cursor de zoom, sem ação)
- Anexos de ticket: ficheiros deixam de desaparecer após atualização do sistema; se o arquivo já tiver sido perdido, o aviso deixa isso claro

## [26.07.007] - 2026-07-16

### Melhorias

- WhatsApp: removido botão duplicado «Identificar contato» no header — fica só o do banner enquanto o contacto não está vinculado; após vincular o CTA some
- WhatsApp: encerramento por inatividade só conta a partir da última mensagem do cliente quando o chat já está em atendimento e o atendente já enviou mensagem humana (auto_assumido/BOT não disparam o timer)
- WhatsApp: Ctrl+V no composer cola imagem/ficheiro do clipboard (pré-visualização antes de enviar), como no chat interno
- Chat: removida a borda branca de foco no campo de mensagem e nos demais inputs/textareas (outline nativo + alinhamento ao design system)
- Chat interno: contraste no hover de Responder/Editar/Apagar; duplo clique na mensagem (ou ao lado do balão) inicia resposta e foca o composer — também no WhatsApp

## [26.07.006] - 2026-07-15

### Melhorias

- Chat (#539): após enviar mensagem (WhatsApp e chat interno), o cursor permanece no campo de texto; painel de emoji fica aberto ao escolher vários; **Responder** mensagem no chat interno (direta, equipe e grupo)
- WhatsApp: na busca «Vincular existente», cada resultado mostra **rede** e **empresa(s)** para distinguir homônimos
- WhatsApp / modais: ao digitar na descrição da demanda no **Encerrar atendimento**, o campo perdia o foco a cada atualização da conversa — diálogo já não refoca o painel; formulário não é limpo pelo poll

## [26.07.005] - 2026-07-15

### Melhorias

- WhatsApp (#534): identificar/cadastrar contato do cliente também em atendimento **encerrado** (Histórico); o número do WhatsApp passa a ser gravado no telefone do cadastro para retomar pela aba Contatos

## [26.07.004] - 2026-07-15

### Melhorias

- WhatsApp (#531): aba **Contatos** no hub de chat — lista funcionários com empresa e telefone; iniciar conversa (ou número avulso / retomar no Histórico); chat já fica em atendimento com o iniciador; telefone no cadastro do funcionário da rede
- Sons de alerta: toque de **abertura de ticket** e de **novo chat** (fila WhatsApp/Portal) estavam trocados — ticket usa `notification.mp3` e chat na fila usa `alerta.mp3`

## [26.07.003] - 2026-07-14

### Melhorias

- WhatsApp: conversa em atendimento disparava loop de pedidos a `/demandas` (e esgotava recursos do browser com `ERR_INSUFFICIENT_RESOURCES`) — o painel de demandas já não notifica o pai no carregamento inicial
- Base de conhecimento (#468): chat ao vivo no portal `/kb` — widget para visitantes; atendimento na mesma inbox WhatsApp (abas Aguardando/Atendendo) com badge Portal; protocolo unificado `#C`; mensagens automáticas, avaliação ao encerrar, anexos e áudio como no WhatsApp; transferência, demandas e encerramento com revisão

## [26.07.001] - 2026-07-11

### Melhorias

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
- Persistência do manifest de releases após cada deploy em staging

## [26.06.008] - 2026-06-29

### Melhorias

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
- Persistência do manifest de releases após cada deploy em staging

## [26.06.005] - 2026-06-27

### Melhorias

- WhatsApp (#449): corrigido link do Histórico/Avaliações para conversa — query `?from=` separada do `pathname` (React Router v7)
- Notificações (#452): pendências de mensagem não lida abrem o ticket ou chat concreto (`/tickets/{id}`, `/whatsapp/c/{id}`) — removido fallback genérico para listagens
- WhatsApp (#447): terminologia «contato do cliente» no chat e tickets — distingue colaborador da rede de atendente interno
- WhatsApp (#453): ícones por tipo de ficheiro (PDF, Word, Excel, etc.) nas mensagens de documento
- WhatsApp (#446): marco «Demanda registada» na timeline via evento interno + SSE em tempo real; removido ao excluir demanda
- WhatsApp (#455): Histórico lista chats em atendimento — colegas do setor consultam e comentam internamente; ordenação e filtros de data corrigidos
- WhatsApp (#443): barra de composição estilo WhatsApp Web (+ anexos, figurinhas em breve, microfone à direita)
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
- Identidade visual DeskRudder no painel (logos, login, favicon e componentes de marca)

## [26.06.004] - 2026-06-25

### Melhorias

- Som de ticket novo na fila sem responsável tocava múltiplas vezes por emissões SSE duplicadas e hook de alerta montado em mais de um componente (#406)
- Base de conhecimento (#293–#299): menu **Ajuda** para consultar manuais durante o atendimento; gestão de categorias e artigos (admin); consulta integrada em tickets e WhatsApp; manuais «só para a equipe»; imagens no texto; histórico de versões; reordenar categorias arrastando; manuais consultados ficam disponíveis offline neste computador
- Auditoria (#290–#292): registro detalhado de ações no sistema (atribuição e transferência de tickets, chats WhatsApp, e-mails ao cliente, credenciais PDV e exportações)
- Auditoria: filtros por ação, período e atendente; exportação CSV; painel com detalhes do registro
- Página Sobre: badges de categoria (Melhorias, Correções, etc.) com texto centralizado e alinhamento uniforme na lista (#426)
- Chat WhatsApp (#403): administradores acompanham chats alheios apenas com comentário interno; envio ao cliente restrito ao operador responsável
- Chat WhatsApp (#423): registro de demandas por sessão (natureza/motivo), auto-registro ao abrir ticket e agregação no dashboard de chats; edição via `PATCH`, marco na timeline e fluxo completo no modal de encerramento (#445)
- SLA (#418): pausa automática da contagem quando o ticket está em status configurado (flag `pausa_sla`; «Aguardando cliente» ativado por padrão)
- SLA: políticas opcionais por natureza do ticket; filtro «em risco» e dashboard usam o motor completo (calendário + pausa); prazo efetivo no card SLA
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
