# Control-plane SaaS DeskRudder

Instância comercial (`deskrudder.com.br`): registo de licenças, trial, provisionamento e alertas de renovação.

**Não** confundir com módulos do produto na instância do cliente (CM/FN, `/kb`, portal).

## Ativar

```bash
# backend/.env (instância comercial)
SAAS_CONTROL_PLANE=true
SAAS_NOTIFY_EMAIL=comercial@deskrudder.com.br
SAAS_TRIAL_DAYS=14
SAAS_RENEWAL_ALERT_DAYS_BEFORE=14
SAAS_PROVISION_BASE_DOMAIN=deskrudder.com.br
SAAS_PROVISION_API_PORT_START=8001
# Só no host de deploy com Docker/scripts:
# SAAS_PROVISION_EXEC_ENABLED=true
# SAAS_REPO_ROOT=/caminho/do/repo

# frontend
VITE_SAAS_CONTROL_PLANE=true
```

Em instâncias de clientes: deixar `SAAS_CONTROL_PLANE=false` (padrão).

## Painel

- UI: `/saas/licencas` (shell dedicado — role `saas_ops`)
- Menu: Licenças e Leads comerciais (sem tickets/chat do atendimento)
- Landing: atalho «Acessar painel admin» → `/login/admin`

### Login na apex (`deskrudder.com.br`)

Na raiz comercial o `/login` padrão pede **conta da empresa** e entrega a sessão no subdomínio (`{slug}.deskrudder.com.br` / `api-{slug}.deskrudder.com.br`).

Para a **equipa DeskRudder** (control-plane), use:

- Atalho da landing «Acessar painel admin» → `/login/admin`
- Conta com role **`saas_ops`** (não o admin do tenant cliente)

### Credenciais locais (dev)

Com `SAAS_CONTROL_PLANE=true`, o seed cria:

| Uso | E-mail | Senha | Role |
|-----|--------|-------|------|
| Painel SaaS (`/login/admin`) | `ops@deskrudder.local` | `ops123456` | `saas_ops` |
| Admin atendimento (`/login`) | `admin@email.com` | `admin123` | `admin` |
| Atendente (`/login`) | `atendente@email.com` | `atendente123` | `atendente` |

Sem `VITE_SAAS_CONTROL_PLANE=true`, a apex continua só com login por conta.

## API

| Método | Rota | Quem |
|--------|------|------|
| Resumo ops | `GET /v1/saas/resumo` | `saas_ops` + control-plane |
| CRUD + ações | `/v1/saas/clientes` | `saas_ops` + control-plane |
| Timeline | `GET /v1/saas/clientes/{id}/timeline` | `saas_ops` + control-plane |
| Planos | `/v1/saas/planos` (+ ativar/desativar) | `saas_ops` + control-plane |
| Módulos | `/v1/saas/modulos` (+ ativar/desativar) | `saas_ops` + control-plane |
| Leads B2B | `/v1/saas/leads` | `saas_ops` + control-plane |
| Trial | `POST /v1/saas/public/trial` | público (rate limit) |
| Contato landing | `POST /v1/saas/public/contato` | público (rate limit) |

Ações clientes: `suspender`, `reativar`, `renovar` (`dias` ou `nova_data`), `registrar-instancia`, `solicitar-provisionamento`, `confirmar-provisionamento`, `aprovar` (body opcional `plano_id` no go-live), `rejeitar`, `confirmar-stack`, `reenviar-entrega`.
Read de clientes inclui `comandos_ops` quando a fila está activa (`pendente` / `aguardando_ops` / `falha` / `em_progresso`), `comandos_stack` quando há `stack_ops_pendente` (`down`/`up`), e `aprovacao_status` / `aprovacao_notas` / `aprovacao_em`.

Listagem `GET /clientes` aceita filtros: `status`, `plano_id`, `aprovacao_status`, `provisionamento_status`, `provisionamento_fila`, `vencendo`, `vencidas` (+ busca/paginação). Na UI, os cartões do resumo aplicam estes filtros via query string.

Busca em `/clientes` cobre nome, slug, `contato_nome` e `contato_email`.

A **URL pública** da instância não é escolhida livremente: o ops/cliente define só o **slug** (nome da base) e o sistema monta `https://{slug}.{SAAS_PROVISION_BASE_DOMAIN}/`. Em desenvolvimento local o DNS `*.deskrudder.com.br` tipicamente **não resolve** (`ERR_NAME_NOT_RESOLVED`) — use `http://127.0.0.1:{api_port}/health` (atalho «Abrir» no painel quando o browser está em localhost).

## Planos e módulos (catálogo comercial)

- UI: `/saas/planos`, `/saas/modulos` — CRUD, activar/desactivar; plano associa `modulo_ids`.
- Licença: campo `plano_id` (select); `plano` fica como rótulo denormalizado do nome.
- Seed (migration `091`): módulos `helpdesk`, `whatsapp`, `contratos`, `boletos`; planos `trial`, `profissional`, `enterprise`.
- Planos podem ter `preco_mensal`, `max_postos`, `max_usuarios` (migration `092`).
- Ao atribuir/aprovar plano, a licença grava `modulos_snapshot` + limites (congelados na ficha comercial).
- No provisionamento, `SAAS_MODULOS` é escrito no `client.env` a partir do snapshot; o `/health` da instância expõe `capabilities.modulo_*` lidos dessa env.
- Enforcement fino de features no produto cliente (UI/RBAC por módulo) fica para follow-up — hoje o snapshot + env são a fonte de verdade comercial/ops.

## Histórico da licença

`GET /v1/saas/clientes/{id}/timeline` — eventos de `audit_log` (`entity_type=cliente_saas`) com rótulos legíveis. UI: cartão **Histórico** no detalhe.

## Checklist QA local (antes de testes manuais)

1. Flags dual: `SAAS_CONTROL_PLANE=true` + `VITE_SAAS_CONTROL_PLANE=true` só na instância comercial.
2. Migrations `084`–`092` aplicadas (`alembic upgrade head`).
3. Login ops via `/login/admin` (`ops@deskrudder.local`) → shell SaaS (Licenças / Planos / Leads), sem menu de tickets.
4. Login atendimento via `/login` (`admin@email.com` ou `atendente@email.com`) → painel de tickets/chat (sem menu SaaS).
5. Lead → **Converter em licença** (escolher plano) ou prefill manual; trial em `/trial`; contacto na LP.
6. Provisionar com `SAAS_PROVISION_EXEC_ENABLED=false` → `aguardando_ops` → copiar comandos → **Confirmar provisionamento** após health (dispara e-mail de entrega ao contacto se Resend estiver ok).
7. Trial com aprovação pendente → **Aprovar e criar base** (activo + fila de provisionamento) ou **Rejeitar** (churn).
8. Suspender/reativar com stack provisionada → comandos `down`/`up` → **Confirmar stack** (ou auto-exec).
9. Renovar por dias e por data; sincronizar URL a partir do slug; **Reenviar entrega** se necessário.
10. Criar/editar planos e módulos; atribuir plano na licença.
11. Workers activos no log do backend (`saas-provisionamento`, `saas-renovacoes`).
12. Sem Resend: fluxo continua (notify é no-op); com Resend + `SAAS_NOTIFY_EMAIL`: e-mails de trial/renovação; contacto recebe entrega pós-health.

## Contato comercial B2B (DR-06 / #516)

- Landing: CTA «Fale conosco» / demonstração abre formulário (nome, e-mail, mensagem) → `/v1/saas/public/contato`
- **Não** usa `/kb/public/chat/*` nem `portal_chats`
- Inbox: `/saas/leads` (menu SaaS DeskRudder)
- **Converter em licença**: `POST /v1/saas/leads/{id}/converter` cria `ClienteSaaS`, grava `cliente_saas_id` no lead e `lead_comercial_id` na licença, marca o lead como `fechado`
- Prefill manual (`/saas/licencas/novo?lead_id=…`) também persiste o vínculo ao guardar
- Sem control-plane: CTA continua com `mailto:` (landing não quebra)

## Provisionamento (DR-04)

Fluxo padrão no control-plane: **ops-assisted** (`SAAS_PROVISION_EXEC_ENABLED=false`).

### Ops-assisted (recomendado)

1. Em `/saas/licencas/{id}`, a equipa clica **Solicitar provisionamento** (ou o trial público já enfileira sozinho).
2. Status → `pendente`; o worker aloca `api_port` e passa a `aguardando_ops`, preenchendo a URL esperada `https://{slug}.{SAAS_PROVISION_BASE_DOMAIN}`.
3. O detalhe mostra um bloco **Comandos** (também em `comandos_ops` na API) para copiar:
   - `./deploy/scripts/provision-client.sh --slug … --base-domain … --api-port …`
   - `./deploy/scripts/stack-client.sh migrate|up|health {slug}`
4. No host de deploy, ops corre os scripts (Docker + DNS/Nginx — ver `deploy/clients/README.md` e #170).
5. Com `health` OK (`curl -sf http://127.0.0.1:{api_port}/health`), no painel: **Confirmar provisionamento** → status `sucesso` (audit `confirmar_provisionamento`). Se houver `contato_email`, envia e-mail de **entrega** (URL + link `/login`) e grava `entrega_notificada_em`.
6. Em **falha**: mensagem visível, comandos disponíveis, **Reenviar à fila** ou corrigir e **Confirmar**.

### Auto-exec (host Linux com Docker)

Com `SAAS_PROVISION_EXEC_ENABLED=true` e `SAAS_REPO_ROOT` apontando para o clone no host:

- O worker corre `provision-client.sh` e depois `stack-client.sh` com argumentos **`<comando> <slug>`** (`migrate`, `up`, `health`).
- Sucesso grava URL e status `sucesso`; erro grava `falha` + stderr truncado.

Não use auto-exec a partir do container Windows/dev sem o repositório e Docker do host montados.

### Pré-requisitos do host

- Docker Compose, `bash`, `openssl` (gera segredos no provision)
- Clone do repo com `deploy/scripts/` e `deploy/clients/_template/`
- Permissão para criar `deploy/clients/<slug>/` e subir stacks
- DNS / Nginx por cliente conforme `docs/DEPLOYMENT_ARCHITECTURE.md` e `deploy/clients/README.md`

**Não** altera o modelo single-tenant (1 Postgres por cliente).

## Trial (DR-07)

Formulário público (`/trial`) cria `ClienteSaaS` com `status=trial`, `aprovacao_status=pendente`,
`data_renovacao = hoje + SAAS_TRIAL_DAYS` e notifica `SAAS_NOTIFY_EMAIL` (se Resend estiver configurado).
**Não** cria base nem enfileira provisionamento neste passo.

O campo legado `solicitar_provisionamento` no body é ignorado.

## Aprovação go-live

Trials públicos entram com `aprovacao_status=pendente`. Licenças criadas manualmente no painel ficam
`aprovado` de imediato.

| Acção | Efeito |
|-------|--------|
| `POST …/aprovar` (`ativar=true`, `provisionar=true` por omissão) | `aprovacao_status=aprovado`; se `trial`/`suspenso` → `ativo`; **enfileira criação da base** (`provisionamento_status=pendente`) |
| `POST …/rejeitar` | `aprovacao_status=rejeitado`, `status=churn`; cancela fila se ainda não `sucesso` |

O resumo ops inclui `aprovacoes_pendentes`. Com `SAAS_PROVISION_EXEC_ENABLED=true` e `SAAS_REPO_ROOT`
no **host de deploy** (Docker socket + scripts), o worker cria a base automaticamente. Em local Windows,
a API corre dentro do container **sem** Docker socket — após aprovar, rode no host:

```bash
# Git Bash / WSL, na raiz do repo
./deploy/scripts/saas-drain-queue.sh
# ou um cliente:
./deploy/scripts/saas-create-base.sh codewave 8003 deskrudder.com.br
```

Depois confirme no painel se ainda estiver `aguardando_ops` (o drain já confirma via API).

## Suspender / reativar (stack)

Com instância provisionada (`provisionamento_status=sucesso` ou URL+porta):

| Acção | `SAAS_PROVISION_EXEC_ENABLED=false` (ops) | `=true` (auto) |
|-------|------------------------------------------|----------------|
| Suspender | `status=suspenso` + `stack_ops_pendente=down` + comandos | corre `stack-client.sh down` |
| Reativar | `status=ativo` + `stack_ops_pendente=up` + comandos | corre `up` (+ `health`) |
| Confirmar | `POST …/confirmar-stack` → `stack_status` `stopped`/`running` | — |

Sem stack provisionada, suspender/reativar só actualiza o estado da licença. A suspensão automática por
renovação vencida também dispara o mesmo fluxo de stack.

## Entrega pós-health

Após `provisionamento_status=sucesso` (confirmação ops ou auto-exec), o control-plane tenta e-mail ao
`contato_email` com URL, plano, módulos do snapshot, limites e nota de DNS local. Ops pode
**Reenviar entrega** (`POST …/reenviar-entrega`).

Requer o mesmo envio de sistema (Resend) das outras notificações SaaS; sem credenciais o fluxo não falha
na confirmação — só não grava `entrega_notificada_em`.

O resumo ops inclui `instancias` (slug, porta, stack, provisionamento) para visão rápida de health no painel.

## Renovações (DR-08)

Worker `saas-renovacoes` (intervalo `SAAS_RENEWAL_WORKER_INTERVAL_SECONDS`):

- Dentro da janela `SAAS_RENEWAL_ALERT_DAYS_BEFORE`: e-mail à equipa (dedup por data de renovação).
- Vencido (`data_renovacao < hoje`) em `trial`/`ativo`: passa a `suspenso` + e-mail.
- UI: destaque «vence em X dias» / vencidas; ação **Renovar** no detalhe.

## Referências

- Épico: `#519`
- Issues: DR-01…DR-08 em `.github/planning-issue-bodies/`
- Deploy por cliente: `docs/DEPLOYMENT_ARCHITECTURE.md`, `deploy/clients/README.md`
