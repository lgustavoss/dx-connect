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
| Leads B2B | `/v1/saas/leads` | `saas_ops` + control-plane |
| Trial | `POST /v1/saas/public/trial` | público (rate limit) |
| Contato landing | `POST /v1/saas/public/contato` | público (rate limit) |

Ações clientes: `suspender`, `reativar`, `renovar` (`dias` ou `nova_data`), `registrar-instancia`, `solicitar-provisionamento`.

Busca em `/clientes` cobre nome, slug, `contato_nome` e `contato_email`.

## Checklist QA local (antes de testes manuais)

1. Flags dual: `SAAS_CONTROL_PLANE=true` + `VITE_SAAS_CONTROL_PLANE=true` só na instância comercial.
2. Migrations `078`–`080` aplicadas (`alembic upgrade head`).
3. Login ops via `/login/admin` (`ops@deskrudder.local`) → shell SaaS (Licenças / Leads), sem menu de tickets.
4. Login atendimento via `/login` (`admin@email.com` ou `atendente@email.com`) → painel de tickets/chat (sem menu SaaS).
5. Lead → **Criar licença** (prefill); trial em `/trial`; contacto na LP.
6. Provisionar com `SAAS_PROVISION_EXEC_ENABLED=false` → status `aguardando_ops`.
7. Renovar por dias e por data; suspender/reativar; registar URL.
8. Workers activos no log do backend (`saas-provisionamento`, `saas-renovacoes`).
9. Sem Resend: fluxo continua (notify é no-op); com Resend + `SAAS_NOTIFY_EMAIL`: e-mails de trial/renovação.

## Contato comercial B2B (DR-06 / #516)

- Landing: CTA «Fale conosco» / demonstração abre formulário (nome, e-mail, mensagem) → `/v1/saas/public/contato`
- **Não** usa `/kb/public/chat/*` nem `portal_chats`
- Inbox: `/saas/leads` (menu SaaS DeskRudder)
- Sem control-plane: CTA continua com `mailto:` (landing não quebra)

## Provisionamento (DR-04)

1. Admin clica **Solicitar provisionamento** (ou trial com a opção ligada).
2. Cliente fica com `provisionamento_status=pendente` e `api_port` alocada.
3. Worker `saas-provisionamento`:
   - Se `SAAS_PROVISION_EXEC_ENABLED=false` (padrão): mantém na fila, grava URL esperada `https://{slug}.{SAAS_PROVISION_BASE_DOMAIN}` e notifica a equipa — ops corre os scripts manualmente.
   - Se `true`: executa `deploy/scripts/provision-client.sh` + `stack-client.sh migrate|up|health` no host (`SAAS_REPO_ROOT`).

Pré-requisitos do host: Docker, scripts em `deploy/scripts/`, permissões, DNS/Nginx conforme `deploy/clients/README.md` e skill `deploy-cliente`.

**Não** altera o modelo single-tenant (1 Postgres por cliente).

## Trial (DR-07)

Formulário público cria `ClienteSaaS` com `status=trial`, `data_renovacao = hoje + SAAS_TRIAL_DAYS`, e notifica `SAAS_NOTIFY_EMAIL` (se Resend estiver configurado).

## Renovações (DR-08)

Worker `saas-renovacoes` (intervalo `SAAS_RENEWAL_WORKER_INTERVAL_SECONDS`):

- Dentro da janela `SAAS_RENEWAL_ALERT_DAYS_BEFORE`: e-mail à equipa (dedup por data de renovação).
- Vencido (`data_renovacao < hoje`) em `trial`/`ativo`: passa a `suspenso` + e-mail.
- UI: destaque «vence em X dias» / vencidas; ação **Renovar** no detalhe.

## Referências

- Épico: `#519`
- Issues: DR-01…DR-08 em `.github/planning-issue-bodies/`
- Deploy por cliente: `docs/DEPLOYMENT_ARCHITECTURE.md`, `deploy/clients/README.md`
