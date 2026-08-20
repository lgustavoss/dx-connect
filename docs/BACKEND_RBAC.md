# RBAC no backend (API v1)

Política alinhada à issue **#38** (admin / atendente + setor) e **#336** (perfil **comercial** para CRM).

## Perfis

| Role | Uso |
|------|-----|
| `admin` | Cadastros, configuração, visão total, CRM e catálogo de custos. |
| `atendente` | Tickets / chats no escopo de setor; **sem** CRM nem catálogo de custos. |
| `comercial` | CRM (leads/negociações) + `POST /v1/comercial/custos/simular`; **sem** CRUD de catálogo nem cadastros admin. |

Dependência: `exigir_comercial_ou_admin` em `app.core.auth`.

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
| Catálogo comercial (CRUD) | `POST/PATCH/DELETE /v1/comercial/salario-minimo*`, `POST/PATCH/DELETE /v1/comercial/custos/itens*` |
| Catálogo comercial (leitura itens) | `GET /v1/comercial/custos/itens` — também comercial (montar pacote na negociação) |
| Funil CRM (mutação) | `POST/PATCH /v1/crm/funil-estagios` — UI em Configurações → Cadastros → Funil CRM |
| Modelos de proposta (CRUD) | `POST/PATCH /v1/comercial/proposta-templates`, `POST /v1/comercial/proposta-templates/preview` — UI em Cadastros → Modelos de proposta |
| Modelos de contrato (CRUD) | `POST/PATCH /v1/comercial/contrato-templates`, `POST /v1/comercial/contrato-templates/preview`, `GET /v1/comercial/contrato-templates/chaves` |
| Política de reajuste do contrato | `PATCH /v1/comercial/contrato-politica` (percentual e rótulo padrão da instância) |

## Comercial ou administrador (`exigir_comercial_ou_admin`)

| Recurso | Comportamento |
|---------|----------------|
| **CRM** | `GET/POST/PATCH /v1/crm/leads`, `GET/POST/PATCH /v1/crm/negociacoes*`, atividades, mover estágio. Listagem vê **todas** as leads/negociações; filtro opcional `so_minhas=true`. |
| **Funil (leitura)** | `GET /v1/crm/funil-estagios` |
| **Simular custos** | `POST /v1/comercial/custos/simular` |
| **Listar itens catálogo** | `GET /v1/comercial/custos/itens` (mutações continuam só admin) |
| **Proposta comercial** | `GET /v1/comercial/proposta-templates` (ativos), `POST/GET /v1/comercial/propostas*`, `GET .../pdf`, `POST .../marcar-enviada` |
| **Contrato comercial** | `GET /v1/comercial/contrato-templates` (ativos), `GET /v1/comercial/contrato-templates/chaves`, `GET /v1/comercial/contrato-politica`, `POST/GET /v1/comercial/contratos*`, `GET .../pdf`, `POST/GET .../pdf-assinado`, `POST .../marcar-enviado`, `POST .../marcar-assinado`, `POST .../cancelar` (também rescinde assinado com estimativa de multa no payload/atividade). Lista e detalhe (incl. PDF e `multa_rescisao`): comercial só as próprias negociações; admin todos (filtros `so_minhas` e `responsavel_id`). Marcar assinado cria/vincula Rede e Empresa internamente — comercial **não** ganha CRUD de Rede/Empresa. |

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

## Referência de código

- `app.core.auth`: `obter_atendente_atual`, `exigir_admin`, `exigir_comercial_ou_admin`, `validar_role`.
- `app.core.setor_scope`: `ids_setores_visiveis_atendente`, `ids_setores_mesmo_nome`, `responsavel_elegivel_para_setor_do_ticket`, `select_rede_ids_com_ticket_nos_setores`.
- Testes: `backend/tests/test_rbac_tickets.py`, `test_rbac_catalogos.py`, `test_rbac_admin_only.py`, `test_crm.py`.

## Frontend (alinhamento)

- **Menu**: grupos «Clientes» e «Configurações» só aparecem para `role === 'admin'` (`Sidebar.tsx`).
- **Rotas**: páginas de cadastro usam `AdminRoute` em `App.tsx` — atendente vê `AcessoNegado` se aceder por URL.
- **Tickets / novo ticket**: listas de **setores** e **empresas** seguem o filtro da API; não se recorta setor no cliente por `setor_ids` do `/me` (homônimos). Quando o atendente ainda não tem empresas no escopo, o UI explica o critério da rede com ticket nos setores dele.
- **403**: mensagens vêm do corpo da API (`api/client` + `errorMessage.ts`).
- **CRM UI** (#341–#344): menu **CRM** e rotas `/crm/leads`, `/crm/negociacoes/:id` para `admin` e `comercial`.
- **Proposta** (#345–#348): card na negociação para comercial/admin; CRUD de templates só admin.
- **Contrato** (#349–#357): card na negociação, lista `/crm/contratos` (comercial: próprias; admin: todas); CRUD de templates e política de reajuste em Cadastros (só admin).
