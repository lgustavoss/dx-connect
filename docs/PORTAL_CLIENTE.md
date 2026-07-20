# Portal do cliente (`/portal`)

Portal autenticado para funcionários da rede (sócio, supervisor, colaborador) abrirem e acompanharem chamados. Distinto do portal KB público (`/kb`) e do chat visitante (`portal_chat`).

Épico: [#263](https://github.com/lgustavoss/dx-connect/issues/263)

## Autenticação

- JWT com claim `aud=portal` (separado do painel interno)
- Credenciais em `funcionarios_rede.senha_hash` (admin define no cadastro)

## RBAC por papel (#604)

Escopo implementado em `backend/app/core/portal_scope.py`.

| Papel | Tickets | Chats WhatsApp (API #603) |
|-------|---------|---------------------------|
| **Colaborador** | Só os **próprios** (`aberto_por_id` = funcionário) | Só contactos **vinculados** a ele (`funcionario_rede_id`) |
| **Supervisor** | Todos das **empresas vinculadas** | Todos das empresas vinculadas |
| **Sócio** | Toda a **rede** (incl. tickets só com `rede_id`) | Toda a rede |

Colaborador **não** vê ticket aberto pela equipe interna (sem `aberto_por_id`) nem chamado de colega da mesma empresa.

Supervisor vê tickets de todos os funcionários das empresas em que está vinculado, não apenas os que ele abriu.

## Chats WhatsApp (#603)

- Listagem em `/portal/chats` e detalhe com timeline legível (somente leitura)
- Mensagens internas da equipe (comentários, transferências, marcos de demanda, fluxo de avaliação) ficam ocultas
- API: `GET /v1/portal/chats`, `GET /v1/portal/chats/{id}`, `GET /v1/portal/chats/{id}/mensagens`

## Gestão de equipe (#602)

Disponível apenas para **sócio** autenticado no portal.

- Listagem e CRUD de **colaboradores** e **supervisores** da mesma rede
- Senha do portal, empresas vinculadas e situação (ativo/inativo)
- **Não** é possível criar ou promover outro **sócio** pelo portal
- Outros sócios aparecem na listagem; só é permitido alterar situação, senha e notificações
- Colaborador e supervisor recebem **403** em `/v1/portal/equipe/*`
- API: `GET/POST/PATCH /v1/portal/equipe/funcionarios`, `GET /v1/portal/equipe/empresas`
- UI: menu **Equipe** (só sócio) em `/portal/equipe`

## Branding white-label (#605)

Reutiliza `KbPortalSettings` e logo de **Configurações → Sistema → Empresa** (mesma fonte do `/kb`).

- Admin edita cores e textos em **Configurações → Base de conhecimento**
- **Título do `/portal`:** derivado do nome da empresa (`Portal — {nome}`), independente do título da central `/kb`
- **Cores:** navbar (`cor_header`) e menu lateral (`cor_sidebar`, padrão = navbar) configuráveis no painel
- API pública: `GET /v1/portal/public/branding` (sem auth; logo via `/v1/kb/public/logo`)
- Login e shell `/portal` aplicam CSS variables (`--portal-primary`, etc.)
- Fallback com cores padrão e título «Portal do cliente» se settings incompletos
- Código: `backend/app/services/instancia_branding.py`, `frontend/src/contexts/PortalBrandingContext.tsx`

## Chat ao vivo (widget)

Botão flutuante no `/portal` (mesmo padrão da central `/kb`), habilitado quando **Chat ao vivo** está ativo em Configurações → Base de conhecimento.

- Reutiliza a API pública `portal_chat` (`/v1/kb/public/chat`) — o atendimento aparece no hub **Chat** do painel DeskRudder da **mesma instância**
- Nome e e-mail pré-preenchidos com o usuário autenticado do portal
- Token de sessão em `localStorage` separado do visitante `/kb` (`dxconnect.portal.cliente.chat_token`)

### Isolamento entre clientes (produção)

Produção = **single-tenant por instância** (subdomínio + Postgres dedicado). O widget do portal da DuplexSoft só fala com a API dessa instância; o SSE/fila de chat só notifica atendentes daquele DeskRudder. Não há compartilhamento de chats entre clientes DeskRudder.

## Referências de código

- API: `backend/app/api/portal.py`
- Tickets: `backend/app/services/portal_tickets.py`
- Equipe: `backend/app/services/portal_equipe.py`
- Testes: `backend/tests/test_portal_cliente.py`
