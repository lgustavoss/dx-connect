# RBAC no backend (API v1)

Política alinhada à issue **#38**: perfis **admin** e **atendente**, com escopo por **setor** (inclui setores homônimos — ver `app.core.setor_scope`).

## Autenticação

| Prefixo | Quem acessa |
|---------|-------------|
| `/v1/auth/*` | Público (login / refresh). |

## Só administrador (`exigir_admin` → 403 para não admin)

| Recurso | Rotas |
|---------|--------|
| Redes | `GET/POST/PATCH/DELETE /v1/redes`, `GET /v1/redes/{id}`, `GET /v1/redes/{id}/funcionarios` |
| Empresa (detalhe / mutação / CNPJ) | `GET/PATCH/DELETE /v1/empresas/{id}`, `POST /v1/empresas`, `GET /v1/empresas/consultar-cnpj/...` |
| Funcionários da rede | `GET/POST/PATCH/DELETE /v1/funcionarios-rede` e por id |
| Atendentes (cadastro) | `GET/POST/PATCH/DELETE /v1/atendentes`, `GET /v1/atendentes/{id}` |
| Setor (detalhe / mutação) | `GET/PATCH/DELETE /v1/setores/{id}`, `POST /v1/setores` |
| Status de ticket (detalhe / mutação) | `GET/POST/PATCH/DELETE /v1/status-ticket/{id}`, `POST /v1/status-ticket` |
| Tipos de negócio (detalhe / mutação) | `GET/POST/PATCH/DELETE /v1/tipos-negocio/{id}`, `POST /v1/tipos-negocio` |
| Auditoria | `GET /v1/audit` |
| Cadastro auxiliar (IBGE) | `POST /v1/cadastro-aux/municipios/sincronizar` |
| WhatsApp (Evolution) — settings / QR / teste | Rotas sob `GET/PATCH /v1/settings/whatsapp` e POST associados (`app/api/whatsapp_settings.py`, dependência `exigir_admin`) |

## Autenticado com escopo de setor (`obter_atendente_atual`)

| Recurso | Comportamento |
|---------|----------------|
| **Tickets** | Listagem e operações respeitam setores visíveis; regras extra em `tickets.py` (responsável, fila, fechado, reabrir só admin). |
| **Dashboard** | Agregações filtradas por setor para não admin. |
| **Notificações** | Contagens e itens filtrados por setor / responsável. |
| **GET /v1/setores** | Lista apenas setores aos quais o atendente está vinculado (e homônimos). |
| **GET /v1/empresas** | Admin: modelo completo. Atendente: resumo mínimo (sem PII ampla) só de empresas cujas **redes** já tiveram ticket em algum dos seus setores (`select_rede_ids_com_ticket_nos_setores`). |
| **GET /v1/atendentes/por-setor/{id}** | Só se o setor pertencer ao escopo do atendente (admin: qualquer). |
| **GET /v1/atendentes/me** e **POST /v1/atendentes/me/trocar-senha** | Próprio utilizador. |
| **Status / tipos de negócio — listagem** | `GET /v1/status-ticket`, `GET /v1/tipos-negocio` — leitura para UI de tickets (mutações continuam admin). |
| **Cadastro auxiliar** | `GET` UFs/municípios/CEP: autenticado (evita uso anónimo de proxies externos). |
| **Chats WhatsApp** | Rotas `GET/POST /v1/whatsapp/chats/...`: atendente autenticado; listagens e permissões respeitam setores visíveis; **envio** de texto/mídia só com chat em `em_atendimento` e (se não for admin) como **atendente responsável**. Contratos e fluxo UI: `docs/WHATSAPP_EVOLUTION.md`. |

**Nota:** o webhook `POST /v1/webhooks/evolution` não usa JWT; valida segredo/configuração conforme `whatsapp_webhook.py`.

## Referência de código

- `app.core.auth`: `obter_atendente_atual`, `exigir_admin`.
- `app.core.setor_scope`: `ids_setores_visiveis_atendente`, `ids_setores_mesmo_nome`, `responsavel_elegivel_para_setor_do_ticket`, `select_rede_ids_com_ticket_nos_setores`.
- Testes: `backend/tests/test_rbac_tickets.py`, `test_rbac_catalogos.py`, `test_rbac_admin_only.py`; fluxo WhatsApp (fila, webhook, citação): `test_whatsapp_chats.py`.

## Frontend (alinhamento)

- **Menu**: grupos «Clientes» e «Configurações» (inclui **WhatsApp (Evolution)**) só aparecem para `role === 'admin'` (`Sidebar.tsx`). O grupo **Chat** (Atendendo / Histórico) é visível a todos os autenticados.
- **Rotas**: páginas de cadastro usam `AdminRoute` em `App.tsx` — atendente vê `AcessoNegado` se aceder por URL.
- **Tickets / novo ticket**: listas de **setores** e **empresas** seguem o filtro da API; não se recorta setor no cliente por `setor_ids` do `/me` (homônimos). Quando o atendente ainda não tem empresas no escopo, o UI explica o critério da rede com ticket nos setores dele.
- **403**: mensagens vêm do corpo da API (`api/client` + `errorMessage.ts`).
