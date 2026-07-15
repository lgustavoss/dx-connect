# [Marketing] Landing page pública — deskrudder.com.br

## Contexto

O **DeskRudder** (DX Connect) já possui rotas públicas (`/login`, `/kb`, `/avaliar-ticket`), mas não há uma **página institucional** na raiz do domínio para divulgação comercial.

Hoje, quem acessa a URL do sistema tende a cair no **login** ou no painel autenticado. Para prospecção (redes de postos, coordenadores de suporte, gestores de TI), precisamos de uma landing em **`deskrudder.com.br/`** que apresente o produto e suas funcionalidades **já em operação**.

**Marca:** DeskRudder — tagline «Organize. Foque. Direcione» (`frontend/src/brand/tokens.ts`).

**Relacionado:** LP-02 / DR-06 (contato comercial B2B na landing — **não** o chat do `/kb` do produto). Esta issue cobre **somente** o conteúdo e layout da página; o canal de contato é entregue em LP-02.

**Épico SaaS:** ver `DR-epic-saas-licencas-instancias.md` e análise `analises/saas-deskrudder-licencas-vs-produto.md`.

## Objetivo

Publicar uma landing page **responsiva**, em português, que:

1. Explique o produto em linguagem de negócio (não técnica).
2. Destaque módulos **já operacionais** (inventário abaixo).
3. Direcione interessados para contato (espaço reservado para o widget LP-02) e clientes existentes para `/login`.
4. Reutilize identidade visual DeskRudder (cores, logo, gradientes).
5. Seja indexável (SEO básico: title, description, Open Graph).

## Público-alvo

- Gestores de TI / operações de redes de postos
- Coordenadores de suporte e SAC
- Donos de software house que revendem suporte
- Prospects que chegam por indicação, LinkedIn, eventos, etc.

## Inventário de funcionalidades (copy — só o que está em operação)

Agrupar na landing em **blocos de valor** (4–6 cards), não em lista de issues:

### 1. Atendimento multicanal
- Tickets por e-mail e abertura manual — fila, prioridade, transferência, histórico
- WhatsApp integrado (Evolution API) — inbox unificada, fila Aguardando/Atendendo, mídia, áudio, demandas por sessão
- Hub de chat (`/chat`) — WhatsApp + chat interno num só lugar
- Portal KB com chat ao vivo (#468) — visitante no `/kb` fala com atendente na mesma inbox

### 2. Organização e produtividade da equipe
- Setores e atendentes com RBAC (admin vs atendente, escopo por setor)
- Distribuição automática de tickets (round-robin, menor carga)
- Roteamento automático por regras (setor, prioridade, natureza, motivo)
- Chat interno — direto 1:1, canais por setor, grupos, anexos, reações
- Notificações em tempo real (SSE)

### 3. SLA e visibilidade gerencial
- Políticas de SLA por setor/prioridade/natureza
- Calendário comercial e pausa automática
- Alertas em risco/violado (e-mail + SSE)
- Dashboards e relatórios exportáveis (CSV)

### 4. Base de conhecimento
- Manuais internos no menu Ajuda
- Portal público `/kb` **por instância**: cada cliente DeskRudder publica os próprios manuais (marca/logo) para o **cliente final dele** — não misturar com a home comercial `deskrudder.com.br`
- Chat ao vivo no portal do cliente (visitante ↔ atendentes daquele cliente)
- Sugestão de manuais na classificação de tickets/demandas

### 5. Cadastro e contexto do cliente
- Redes, empresas e funcionários (sócio, supervisor, colaborador)
- Vínculo de contato WhatsApp ao cadastro

### 6. Governança e confiança
- Auditoria expandida (ações, IP, request-id, exportação CSV)
- Atendimento humano no WhatsApp (sem chatbot — decisão #122)
- Deploy single-tenant por cliente (dados isolados por instância)

> **Regra de copy:** não citar «em breve», roadmap ou features parciais.

## Proposta de UX

### Seções (scroll único)

1. **Hero** — logo, tagline, subtítulo, CTA primário (área para LP-02) + secundário «Já sou cliente» → `/login`
2. **Problema → solução** — caos de WhatsApp + e-mail + planilhas vs centralização
3. **Funcionalidades** — 4–6 cards com ícone + título + 2 linhas (blocos acima)
4. **Como funciona** — 3 passos: configure setores → atenda num hub → meça com dashboards
5. **Diferenciais** — SLA, KB + chat no portal, chat interno, auditoria, atendimento humano
6. **Público** — redes de postos, suporte B2B, equipes multicanal
7. **CTA final** — reforço de contato (placeholder para widget LP-02)
8. **Rodapé** — link login, e-mail institucional (constante/env), versão opcional, privacidade (quando existir)

### Rascunho Hero (revisar na implementação)

- **Título:** «Centralize o atendimento da sua rede em um só lugar»
- **Subtítulo:** «Tickets, WhatsApp, base de conhecimento e SLA — com equipe organizada por setor e visibilidade em tempo real.»
- **CTA secundário:** «Já sou cliente» → `/login`

### Comportamento de rotas

| Visitante | URL `/` | Demais rotas |
|-----------|---------|--------------|
| Anônimo | Landing pública | `/login`, `/kb`, etc. como hoje |
| Autenticado | Redirecionar para dashboard (`/` → painel ou `/dashboard`) | Inalterado |

> A landing **não** substitui `/kb` nem `/login`. É a home do domínio `deskrudder.com.br` para quem não está logado.

## Escopo

### Dentro

- Página pública em `/` (visitante anônimo)
- Copy centralizado em `frontend/src/content/landing.ts` (ou equivalente)
- Layout marketing sem shell do painel (`MarketingLayout`)
- Reuso de `brand/tokens.ts`, `BrandLogo`, Tailwind
- Meta tags + Open Graph (imagem: lockup ou asset em `public/`)
- Responsivo mobile-first (320px+)
- `npm run build` sem regressão

### Fora

- Widget de chat (LP-02)
- Depoimentos e logos de clientes
- CMS/admin para editar textos
- Formulário de lead com backend
- Pré-cadastro e trial gratuito (épico futuro LP-03+)
- Blog, pricing, comparativo com concorrentes
- i18n, A/B testing, analytics (follow-ups)

## Mapa técnico

| Ação | Caminho provável |
|------|------------------|
| criar | `frontend/src/pages/marketing/LandingPage.tsx` |
| criar | `frontend/src/pages/marketing/MarketingLayout.tsx` |
| criar | `frontend/src/content/landing.ts` |
| criar | `frontend/src/components/marketing/*` (seções Hero, Features, etc.) |
| alterar | `frontend/src/App.tsx` — rota `/` pública + redirect se autenticado |
| reutilizar | `frontend/src/brand/tokens.ts` |

**Backend / migration:** não necessário.

## RBAC

- Rota 100% pública — sem auth.
- Não expor URLs internas de clientes, credenciais ou dados de tenant.
- Screenshots (se usados): ambiente demo/staging sanitizado.

## Critérios de aceite

- [ ] Visitante anônimo em `deskrudder.com.br/` vê a landing (não o login)
- [ ] Usuário autenticado em `/` é redirecionado ao painel
- [ ] Conteúdo cobre os 6 blocos de funcionalidades (sem prometer o que não existe)
- [ ] Visual alinhado à marca DeskRudder
- [ ] Layout responsivo — legível em mobile
- [ ] CTA «Já sou cliente» leva a `/login`
- [ ] Área reservada no layout para montar o widget de LP-02 (slot ou import futuro)
- [ ] `<title>` e `meta description` preenchidos; Open Graph com imagem
- [ ] Sem depoimentos de clientes na v1
- [ ] `npm run build` passa

## Dependências

- Nenhuma issue bloqueante de backend.
- **LP-02** depende desta issue (ou pode ser desenvolvida em paralelo se o slot do widget existir).

## Deploy / infra (nota operacional)

- `deskrudder.com.br` deve apontar para a **instância comercial/marketing** do DeskRudder (single-tenant).
- Não confundir com subdomínios de clientes (`cliente.connect...`).

## Labels

`marketing`, `frontend`, `ux`, `fase-interna`

## Próximo passo

→ `/implementar-issue @LP-01-landing-page-marketing.md`  
→ Em seguida: LP-02 (chat comercial na landing)
