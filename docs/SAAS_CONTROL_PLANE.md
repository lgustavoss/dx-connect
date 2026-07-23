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

- UI: `/saas/licencas` (admin)
- Menu: **SaaS DeskRudder → Licenças**
- Landing: atalho «Painel de licenças» e formulário de trial em `/trial`

## API

| Método | Rota | Quem |
|--------|------|------|
| CRUD + ações | `/v1/saas/clientes` | admin + control-plane |
| Trial | `POST /v1/saas/public/trial` | público (rate limit) |

Ações: `suspender`, `reativar`, `renovar`, `registrar-instancia`, `solicitar-provisionamento`.

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
