# Control-plane SaaS DeskRudder

Instância comercial (`deskrudder.com.br`): registo de licenças, trial, provisionamento e alertas de renovação.

**Não** confundir com módulos do produto na instância do cliente (CM/FN, `/kb`, portal).

A instância comercial **não** partilha Postgres nem container com o cliente DuplexSoft. Runbook: [`deploy/admin-center/README.md`](../deploy/admin-center/README.md) (épico #875).

Em produção (após #877 / #878): API comercial em `https://api.deskrudder.com.br` (`saas_control_plane: true`); landing/`/saas` em `https://deskrudder.com.br`; DuplexSoft em `api-duplexsoft…` com `saas_control_plane: false` + ingest.

## Ativar

```bash
# backend/.env (instância comercial)
SAAS_CONTROL_PLANE=true
SAAS_NOTIFY_EMAIL=comercial@deskrudder.com.br
SAAS_TRIAL_DAYS=14
SAAS_RENEWAL_ALERT_DAYS_BEFORE=14
SAAS_PROVISION_BASE_DOMAIN=deskrudder.com.br
SAAS_PROVISION_API_PORT_START=8002
# Só no host de deploy com Docker/scripts:
# SAAS_PROVISION_EXEC_ENABLED=true
# SAAS_REPO_ROOT=/caminho/do/repo

# frontend
VITE_SAAS_CONTROL_PLANE=true
```

Em instâncias de clientes: deixar `SAAS_CONTROL_PLANE=false` (padrão).

## Painel

- UI: `/saas/licencas` (shell dedicado — role `saas_ops`)
- Menu: Licenças, Planos, Leads comerciais e Sugestões (sem tickets/chat do atendimento)
- Landing: atalho «Acessar painel admin» → `/login/admin`

### Login na apex (`deskrudder.com.br`)

Na raiz comercial o `/login` padrão pede **conta da empresa** e entrega a sessão no subdomínio (`{slug}.deskrudder.com.br` / `api-{slug}.deskrudder.com.br`).

Para a **equipe DeskRudder** (control-plane), use:

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

### Produção (`deskrudder.com.br/login/admin`)

Não uses as contas de desenvolvimento. O primeiro ops do control-plane é **`ops@deskrudder.com.br`**. A senha **não** está no git (foi gerada na VPS). Se não a tiveres, redefine na API (`docker exec` no container) — não corras o seed de dev em produção.

## API

| Método | Rota | Quem |
|--------|------|------|
| Resumo ops | `GET /v1/saas/resumo` | `saas_ops` + control-plane |
| CRUD + ações | `/v1/saas/clientes` | `saas_ops` + control-plane |
| Timeline | `GET /v1/saas/clientes/{id}/timeline` | `saas_ops` + control-plane |
| Planos | `/v1/saas/planos` (+ ativar/desativar) | `saas_ops` + control-plane |
| Módulos | `/v1/saas/modulos` (+ ativar/desativar) | `saas_ops` + control-plane |
| Leads B2B | `/v1/saas/leads` | `saas_ops` + control-plane |
| Sugestões das instâncias | `GET /v1/saas/solicitacoes` | `saas_ops` JWT ou `SAAS_MCP_TOKEN` (Cursor) |
| Triagem (status / comentário) | `PATCH …/solicitacoes/{id}/status`, `POST …/comentarios` | `saas_ops` + control-plane |
| Ingest (instância→SaaS) | `POST /v1/saas/ingest/solicitacoes` | token da licença (não JWT) |
| Ingest mídia | `POST /v1/saas/ingest/solicitacoes/{origem_id}/media` | token da licença (multipart; JSON já ingerido) |
| Sync triagem (SaaS→instância) | `GET /v1/saas/ingest/solicitacoes/sync` | token da licença (não JWT) |
| Trial | `POST /v1/saas/public/trial` | público (rate limit) |
| Contato landing | `POST /v1/saas/public/contato` | público (rate limit) |

Ações clientes: `suspender`, `reativar`, `renovar` (`dias` ou `nova_data`), `registrar-instancia`, `solicitar-provisionamento`, `confirmar-provisionamento`, `gerar-token-ingest` (plaintext uma vez; grava hash), `aprovar` (body opcional `plano_id` no go-live), `rejeitar`, `confirmar-stack`, `reenviar-entrega`.
Read de clientes inclui `comandos_ops` quando a fila está activa (`pendente` / `aguardando_ops` / `falha` / `em_progresso`), `comandos_stack` quando há `stack_ops_pendente` (`down`/`up`), e `aprovacao_status` / `aprovacao_notas` / `aprovacao_em`.

Listagem `GET /clientes` aceita filtros: `status`, `plano_id`, `aprovacao_status`, `provisionamento_status`, `provisionamento_fila`, `vencendo`, `vencidas` (+ busca/paginação). Na UI, os cartões do resumo aplicam estes filtros via query string.

Busca em `/clientes` cobre nome, slug, `contato_nome` e `contato_email`.

A **URL pública** da instância não é escolhida livremente: o ops/cliente define só o **slug** (nome da base) e o sistema monta `https://{slug}.{SAAS_PROVISION_BASE_DOMAIN}/`. Em desenvolvimento local o DNS `*.deskrudder.com.br` tipicamente **não resolve** (`ERR_NAME_NOT_RESOLVED`) — use `http://127.0.0.1:{api_port}/health` (atalho «Abrir» no painel quando o browser está em localhost).

## Planos e módulos (catálogo comercial)

- UI: `/saas/planos`, `/saas/modulos` — CRUD, ativar/desativar; plano associa `modulo_ids`.
- **Preço no módulo** (`saas_modulos.preco_mensal`); o `preco_mensal` do plano é sempre a **soma** dos módulos do pacote (recalcula ao editar preço ou composição).
- Plano também define `usuarios_inclusos` (default 3) e `preco_usuario_extra` (default R$ 10).
- Licença: `plano_id` (rótulo comercial) + `modulo_ids` opcional para **mix custom** (ex.: Essencial + 1 módulo Enterprise) + `usuarios_contratados` → grava em `max_usuarios` / `modulos_snapshot`.
- **Valor mensal negociado** (`preco_mensal_negociado`): opcional na licença; se preenchido, vira o valor comercial efetivo (`preco_mensal_efetivo`); senão usa a estimativa do catálogo (módulos + extras).
- Estimativa na ficha: `preco_modulos` + extras de usuário = `preco_mensal_estimado`.
- Seed (migrations `091` + `121` + `122` + `123`): módulos com preço; planos pela soma; coluna de valor negociado na licença.
- No provisionamento, `SAAS_MODULOS` vem do snapshot; `/health` expõe `capabilities.modulo_*`.
- Enforcement fino de features no produto cliente e bloqueio hard de usuários além do contratado ficam para follow-up.

## Fila de sugestões das instâncias (#855 / #856)

Quem **usa** o DeskRudder (admin/atendente da instância) abre sugestão ou problema nas Release Notes (`/sobre`). O pedido fica na instância (**Minhas solicitações**). Uma **cópia autenticada** vai para a fila única do control-plane (`/saas/solicitacoes`).

A **triagem** (status e respostas) é feita por `saas_ops` no detalhe `/saas/solicitacoes/{id}`. O protocolo `#SYYYYMM-NNNN` é **único no produto**: a instância comercial (control-plane, Postgres próprio na VPS) emite o número no ingest; o cliente vê o mesmo valor em Minhas solicitações após o sync. Pedidos iguais de vários clientes ligam-se **só no painel SaaS** (`POST …/vinculos`); o peso é o número de clientes no grupo e **não** volta à instância. No GitHub, o título usa um protocolo; o corpo leva `texto_github_demanda` (lista de protocolos). Comentários **públicos** e o status voltam à instância; notas internas e o grupo ficam só no SaaS. O admin da instância **não** altera status nem envia notas de produto.

**Máquina de estados (G1 #953):** só transições `aberta→em_analise→planejada→em_desenvolvimento→concluida`, com `nao_sera_desenvolvida` (+ motivo) a partir de qualquer etapa não final. Saltos ilegais → HTTP 400. Sync SaaS→instância aplica o status já validado no control-plane (e o histórico na instância continua a registar).

**Implementar (G2 #954):** `POST …/solicitacoes/{id}/implementar` a partir de `planejada` cria issue (API GitHub) ou liga URL/número e avança para `em_desenvolvimento`. Sem vínculo GitHub não entra nesse status. O cliente nível 2 **nunca** vê URL/número da issue.

O **posto** (portal) não entra neste fluxo. Análise no Cursor e issues GitHub **não** fazem parte deste lote (#857).

### Instância (`SAAS_CONTROL_PLANE=false`)

No `client.env` (provisionamento):

```
SAAS_INSTANCE_SLUG=<slug da licença>
SAAS_CONTROL_PLANE_INGEST_URL=https://api.deskrudder.com.br/v1/saas/ingest/solicitacoes
SAAS_INSTANCE_INGEST_TOKEN=<gerado no painel SaaS, nunca no browser>
```

Sem URL/token/slug, o pedido local continua; a cópia simplesmente não é enviada. Falha HTTP não faz rollback — a outbox (`webhook_outbox`, eventos `saas.solicitacao` e `saas.solicitacao.media`) tenta de novo. O JSON vai primeiro; a mídia (prints/anexos) segue em multipart para não meter ficheiros no payload JSON.

O worker `saas-triagem-pull` faz `GET …/ingest/solicitacoes/sync` com o mesmo token e aplica status + comentários públicos (idempotente por `origem_externa_id`).

No control-plane (`SAAS_CONTROL_PLANE=true`), a abertura grava directo na tabela `saas_solicitacoes_produto` (sem HTTP para si). A triagem aplica na instância local quando `instance_slug` coincide com `SAAS_INSTANCE_SLUG`.

### Control-plane

- `POST /v1/saas/ingest/solicitacoes` — Bearer ou `X-Saas-Instance-Token`; o token é conferido (SHA-256) com `clientes_saas.ingest_token_hash` do slug do body.
- `POST /v1/saas/ingest/solicitacoes/{origem_id}/media` — o mesmo token; `file` + `storage_key` (UUID da instância) + `papel`. A chave é reutilizada para o markdown `![…](/v1/solicitacoes-melhoria/media/…)` resolver no painel SaaS. 404 se o JSON ainda não chegou (a outbox reenvia).
- `GET /v1/saas/ingest/solicitacoes/sync` — mesmo token; devolve status + comentários públicos daquele slug (`?since=` opcional).
- `GET /v1/saas/solicitacoes` e `GET /v1/saas/solicitacoes/{id}` — `saas_ops` (JWT) ou token Cursor pessoal (`/saas/conta`) / `SAAS_MCP_TOKEN` legado.
- `PATCH …/solicitacoes/{id}/github` — liga a issue criada no GitHub ao pedido (e ao grupo, se houver). Só ops / MCP; o cliente não vê.
- `POST …/solicitacoes/{id}/implementar` — G2: cria ou liga issue e marca `em_desenvolvimento` (só a partir de `planejada`).
- `POST …/solicitacoes/{id}/vinculos` e `DELETE …/vinculos/{membro_id}` — grupo de pedidos iguais (peso). Só ops / MCP.
- `PATCH /v1/saas/solicitacoes/{id}/status` e `POST /v1/saas/solicitacoes/{id}/comentarios` — triagem (máquina de estados G1).
- `POST /v1/saas/me/mcp-token` — gera o token Cursor desta conta (plaintext uma vez). `GET` estado; `DELETE` revoga.
- `GET/POST /v1/saas/usuarios` e `PATCH /v1/saas/usuarios/{id}` — equipa `saas_ops` (nome, e-mail, activo). `POST …/senha-temporaria` devolve senha uma vez. Não são atendentes da instância do cliente.
- `POST /v1/saas/clientes/{id}/gerar-token-ingest` — devolve o plaintext **uma vez** e escreve no `client.env` se a pasta do cliente já existir.
- `SAAS_INGEST_PUBLIC_URL` (opcional) — URL escrita no env das instâncias; por omissão `https://api.{SAAS_PROVISION_BASE_DOMAIN}/v1/saas/ingest/solicitacoes`.

Handoff Cursor é #857: o Cursor **puxa** a fila (MCP `deskrudder-saas`) contra a **API do control-plane**, não o contrário.

### MCP em produção (VPS)

O script corre no PC do ops. A fila é a da instância comercial (`SAAS_CONTROL_PLANE=true`).

1. Entre no painel admin (`/login/admin`) com a **tua** conta `saas_ops`.
2. Abra **Minha conta** (`/saas/conta`) e gere o token. O valor aparece **uma vez** — copie para o Cursor. Regenerar invalida o token anterior.
3. Em cada Cursor: copiar `.cursor/mcp.json.example` para `.cursor/mcp.json` (gitignored), colar **o seu** token em `DESKRUDDER_MCP_TOKEN`, e manter:

   ```
   DESKRUDDER_API_URL=https://api.deskrudder.com.br
   ```

   Alvo do épico #875 (stack comercial própria). **Não** apontar o MCP para `api-duplexsoft` — essa é a API do cliente.

   Cursor → Settings → MCP → habilitar `deskrudder-saas`. No Windows, se o servidor não iniciar, use `"command": "py"` em vez de `"python"`.

   Comando no chat: `/listar-solicitacoes` (arquivo versionado em `.cursor/commands/`).

4. **Teste local** (Docker neste repo): no `.cursor/mcp.json` usa `http://127.0.0.1:8000` e um token gerado no painel local (não o da VPS).

O `SAAS_MCP_TOKEN` no `.env` da VPS ainda é aceite como **legado** (não identifica a pessoa). Prefira o token do painel.

Ferramentas: listar, obter, alterar status (máquina G1), **implementar** (G2), comentar, vincular pedidos iguais, ligar issue GitHub (aceitam `id` ou protocolo). Sem OpenAI e sem `CURSOR_API_KEY` no DeskRudder. Criar issue pode ser via `implementar` (token GitHub no control-plane) ou MCP GitHub à parte + `ligar_issue_github`.

## Runbook: desativar cliente sem derrubar o SaaS

Objetivo: tirar do ar (ou suspender) **só** a instância do cliente. O control-plane continua a servir licenças, fila, MCP e `/saas`.

### Pré-cheque (comercial viva)

```bash
curl -sf https://api.deskrudder.com.br/health   # saas_control_plane: true
curl -sf -o /dev/null -w "%{http_code}\n" https://deskrudder.com.br/login/admin
```

No Cursor: `/listar-solicitacoes` (ou MCP `deskrudder-saas`) ainda lista a fila — prova de que o MCP aponta a `api.deskrudder.com.br`, não a `api-duplexsoft`.

### Suspender pelo painel (recomendado)

1. `/saas/licencas` → cliente → **Suspender** (marca licença + fila de `stack down` se provisionada).
2. No host, se `SAAS_PROVISION_EXEC_ENABLED=false`, correr os comandos `down` mostrados no detalhe (ou `stack-client.sh down <slug>`).
3. **Não** pare o stack `admin-center` nem remova Nginx de `api.deskrudder.com.br` / `deskrudder.com.br`.

### Parar só a DuplexSoft (legado `docker-compose.prod.yml`)

Na VPS, como usuário de deploy:

```bash
cd /opt/dx-connect
docker compose --env-file backend/.env -f docker-compose.prod.yml stop
# ou: down — remove containers; volumes/Postgres do host ficam conforme o compose
```

**Não** execute `stack-client.sh down admin-center`.

### Pós-cheque

| Check | Esperado |
|-------|----------|
| `https://api.deskrudder.com.br/health` | `200`, `saas_control_plane: true` |
| `https://deskrudder.com.br/saas/...` (logado) | painel ops responde |
| MCP / `/listar-solicitacoes` | fila comercial acessível |
| `https://api-duplexsoft…/health` (se parou o cliente) | falha / indisponível — **ok** |
| Postgres `dx-connect-db-admin-center` | `Up` / healthy |

A **fila de sugestões** e as contas `saas_ops` vivem só no Postgres do admin-center. A BD do cliente não é fonte de verdade do control-plane; desligar o cliente não apaga a fila.

### Reativar

- Licença: **Reativar** no painel + `stack-client.sh up <slug>` (ou `docker compose … up -d` no legado DuplexSoft).
- Confirmar health do cliente e, se aplicável, **Confirmar stack** no detalhe da licença.

## Histórico da licença

`GET /v1/saas/clientes/{id}/timeline` — eventos de `audit_log` (`entity_type=cliente_saas`) com rótulos legíveis. UI: cartão **Histórico** no detalhe.

## Checklist QA local (antes de testes manuais)

1. Flags dual: `SAAS_CONTROL_PLANE=true` + `VITE_SAAS_CONTROL_PLANE=true` só na instância comercial.
2. Migrations `084`–`092` aplicadas (`alembic upgrade head`).
3. Login ops via `/login/admin` → shell SaaS (Licenças / Planos / Leads / Sugestões / Equipa / Conta / Cursor). Sem menu de tickets.
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

- Épico cutover: **#875** (filhas #876–#880; docs #879)
- Deploy por cliente: `docs/DEPLOYMENT_ARCHITECTURE.md`, `deploy/clients/README.md`, `deploy/admin-center/README.md`
- MCP example: `.cursor/mcp.json.example` (`DESKRUDDER_API_URL=https://api.deskrudder.com.br`)
