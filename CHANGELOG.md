# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Versão CalVer (`YY.MM.NNN`) é atribuída automaticamente no deploy de `staging`.

## [Unreleased]

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
