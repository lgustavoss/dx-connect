# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Versão CalVer (`YY.MM.NNN`) é atribuída automaticamente no deploy de `staging`.

## [Unreleased]

### DeskRudder

#### Melhorias

- Controle de ponto (#761–#765 / #770–#772): entrada e saída pelo próprio utilizador; histórico com totais; admin vê a equipe e a visão do dia; no cadastro do atendente há flag **Usa escala** e ciclo personalizável (horas trabalhadas × horas de folga, ex. 12×36) com data de início
- Ponto (#766–#768): pausas (almoço) sem fechar o dia; ajustes manuais do admin com motivo e auditoria; exportação CSV da equipe
- Ponto (#769 / #773 / #774): banner de lembretes (online sem ponto / jornada longa / dia de escala sem entrada); indicador «Online sem ponto» na visão do dia; justificativas do utilizador com aprovação do admin
- Ponto (#778–#782): horário previsto e tolerância de atraso; feriados (nacionais + extras da instância) sem contar falta; banco de horas simples; digest diário do admin; fecho automático overnight opcional (desligado por padrão)
- Mobile chat (#747–#759): lista a 100% da largura; teclado sem vão/corte no campo; composer estilo WhatsApp; reagir pelo menu da seta; demanda e modais em folha inferior; header da app oculto na conversa; Encerrar/empresa/setor no telemóvel; empty states úteis; ícones PWA legíveis (fundo claro + contorno branco no desktop)
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
- Mobile (#735 / #736): app Android (instalação pelo APK) focado em **tickets e chat**; na primeira vez escolhes a **conta da empresa** (ex. duplexsoft) e nas seguintes o login já usa essa base
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

- Deploy (#734): ligação SSH ao VPS em IPv4, diagnóstico do IP do runner e segunda tentativa noutro runner só em timeout de rede
- Mobile (#735): `CORS_ORIGINS` das instâncias passa a incluir `https://localhost` (origem do WebView Android)
- Mobile (#735): projecto Capacitor Android no `frontend/` (`npm run build:android`); `stack-client.sh` documentado como `<comando> <slug>`

#### Correções

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
