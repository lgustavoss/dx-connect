# DX Connect — Brief para app mobile (Android / iOS)

Documento para equipes/ferramentas que **não têm acesso ao GitHub**. Descreve stack, APIs, telas e MVP sugerido.

---

## 1. Correção importante sobre o backend

| Item | Valor |
|------|--------|
| **Framework** | **FastAPI** (Python) — **não é Django / DRF** |
| **Validação** | Pydantic (schemas JSON) |
| **Banco** | PostgreSQL |
| **Auth** | JWT Bearer (`access_token` + `refresh_token`) |
| **Prefixo API** | `/v1` |
| **Docs interativas** | `{API_URL}/docs` (Swagger) |

**Frontend web existente:** React 18 + Vite + TypeScript + Tailwind (referência de telas e chamadas em `frontend/src/`).

**Público do app mobile (v1):** **atendentes internos** (suporte/financeiro) — mesmo perfil do painel web. Portal para funcionários de postos é **futuro** (issues #263+).

---

## 2. URL base e autenticação

### Base URL

- **Desenvolvimento:** `http://localhost:8000/v1`
- **Produção:** configurar por build (ex.: `https://api.connect.duplexsoft.com.br/v1`)

### Login

```http
POST /v1/auth/login
Content-Type: application/json

{"email": "admin@email.com", "senha": "admin123"}
```

**Resposta 200:**

```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "must_change_password": false
}
```

### Refresh

```http
POST /v1/auth/login
POST /v1/auth/refresh
{"refresh_token": "..."}
```

### Requisições autenticadas

```http
Authorization: Bearer {access_token}
Content-Type: application/json
```

### Usuário logado

```http
GET /v1/atendentes/me
```

**Resposta 200:**

```json
{
  "id": 1,
  "email": "admin@email.com",
  "nome": "Administrador",
  "role": "admin",
  "ativo": true,
  "setor_ids": [1, 2],
  "must_change_password": false,
  "created_at": "2026-01-01T12:00:00",
  "updated_at": null
}
```

**Perfis:** `admin` | `atendente`. Atendentes veem dados filtrados por **setor** (#38).

### Erros

```json
{"detail": "E-mail ou senha inválidos"}
```

HTTP comuns: `401` (renovar token ou login), `403` (sem permissão), `422` (validação).

---

## 3. Paginação padrão

Listagens retornam:

```json
{
  "items": [ ... ],
  "total": 42
}
```

Query params: `offset`, `limit` (default ~20).

---

## 4. Domínio do produto

Sistema de **helpdesk** para **redes de postos/empresas**:

- **Rede** → várias **Empresas** (postos)
- **Tickets** — demanda assíncrona (e-mail, manual)
- **WhatsApp** — atendimento **síncrono prioritário** (Evolution API)
- **Atendentes** — usuários internos com JWT

**Regra operacional:** chat WhatsApp tem **prioridade** sobre tickets; filas **separadas** (não unificar inbox).

---

## 5. MVP mobile recomendado (fases)

### Fase 1 — Core

| Tela | Rotas API |
|------|-----------|
| Login | `POST /auth/login` |
| Trocar senha (se `must_change_password`) | `POST /atendentes/me/trocar-senha` |
| Dashboard resumo | `GET /dashboard` |
| Notificações (badge + lista) | `GET /notificacoes/resumo`, `GET /notificacoes/itens` |

### Fase 2 — WhatsApp (prioridade operacional)

| Tela | Rotas API |
|------|-----------|
| Fila aguardando | `GET /whatsapp/chats/fila` |
| Meus chats | `GET /whatsapp/chats/meus` |
| Conversa | `GET /whatsapp/chats/{id}`, `GET .../mensagens` |
| Assumir / Encerrar | `POST .../assumir`, `POST .../encerrar` |
| Enviar texto | `POST .../mensagens` `{"texto":"..."}` |
| Enviar mídia | `POST .../mensagens/midia` (multipart) |
| Abrir ticket do chat | `POST .../abrir-ticket` |

Estados do chat: `aguardando_atendente` | `em_atendimento` | `encerrado`

### Fase 3 — Tickets

| Tela | Rotas API |
|------|-----------|
| Lista (filtros) | `GET /tickets?situacao=abertos&meus=true` |
| Fila sem responsável | `GET /tickets?sem_responsavel=true` |
| Detalhe | `GET /tickets/{id}` |
| Mensagens | `GET /tickets/{id}/mensagens` |
| Nova mensagem | `POST /tickets/{id}/mensagens` |
| Assumir (PATCH) | `PATCH /tickets/{id}` `{"atendente_id": ME}` |
| Catálogos | `GET /status-ticket`, `GET /setores`, `GET /ticket-naturezas`, `GET /ticket-motivos` |

### Fora do MVP mobile v1

- Cadastros admin (redes, empresas, atendentes, config WhatsApp)
- Relatórios/dashboards avançados (#260)
- Portal do cliente (#263)

---

## 6. Exemplos JSON — endpoints principais

### Dashboard — `GET /v1/dashboard`

```json
{
  "resumo": {
    "total_tickets": 150,
    "abertos_hoje": 5,
    "por_status": [
      {"status_id": 1, "status_nome": "Aberto", "total": 12},
      {"status_id": 2, "status_nome": "Em atendimento", "total": 8}
    ]
  },
  "ultimos_tickets": [
    {
      "id": 99,
      "protocolo": "#T202606-0042",
      "empresa_id": 3,
      "empresa_nome": "Posto Exemplo",
      "setor_id": 1,
      "setor_nome": "Suporte",
      "status_id": 1,
      "status_nome": "Aberto",
      "atendente_id": null,
      "assunto": "Falha no PDV",
      "prioridade": "alta",
      "fechado_em": null,
      "created_at": "2026-06-14T10:00:00"
    }
  ]
}
```

### Notificações — `GET /v1/notificacoes/resumo`

```json
{
  "sem_responsavel_count": 3,
  "nao_lidas_count": 2,
  "wpp_fila_count": 1,
  "wpp_respostas_count": 4,
  "total_pendencias": 7
}
```

### Tickets lista — `GET /v1/tickets?situacao=abertos&limit=10`

```json
{
  "items": [
    {
      "id": 99,
      "protocolo": "#T202606-0042",
      "assunto": "Falha no PDV",
      "empresa_nome": "Posto Exemplo",
      "setor_nome": "Suporte",
      "status_nome": "Aberto",
      "atendente_nome": null,
      "prioridade": "alta",
      "motivo_nome": "PDV travado",
      "natureza_nome": "Suporte técnico",
      "fechado_em": null,
      "created_at": "2026-06-14T10:00:00"
    }
  ],
  "total": 1
}
```

**Filtros úteis:** `meus`, `sem_responsavel`, `com_responsavel`, `busca`, `protocolo`, `setor_id`, `situacao=abertos|fechados|todos`

**Prioridades:** `baixa` | `normal` | `alta` | `urgente`

### Ticket mensagem — `POST /v1/tickets/{id}/mensagens`

```json
{
  "corpo": "Olá, estamos verificando.",
  "tipo": "publico",
  "notificar_cliente_por_email": false
}
```

Tipos: `publico` (cliente vê) | `interno` (só equipe).

### WhatsApp fila — `GET /v1/whatsapp/chats/fila`

```json
[
  {
    "id": 12,
    "protocolo": "#C202606-0003",
    "wa_id": "5511999999999",
    "cliente_nome": "João",
    "estado": "aguardando_atendente",
    "setor_nome": "Suporte",
    "atendente_id": null,
    "empresa_nome": "Posto Centro",
    "created_at": "2026-06-14T09:55:00"
  }
]
```

### WhatsApp mensagens — `GET /v1/whatsapp/chats/{id}/mensagens`

```json
[
  {
    "id": 501,
    "chat_id": 12,
    "direcao": "inbound",
    "corpo": "Bom dia, PDV não abre",
    "tipo_midia": null,
    "midia_disponivel": false,
    "atendente_nome": null,
    "created_at": "2026-06-14T09:56:00"
  },
  {
    "id": 502,
    "chat_id": 12,
    "direcao": "outbound",
    "corpo": "Olá, sou Maria. Vou ajudar.",
    "atendente_nome": "Maria",
    "created_at": "2026-06-14T10:01:00"
  }
]
```

`direcao`: `inbound` | `outbound`. Mídia: `GET /v1/whatsapp/chats/{id}/mensagens/{msg_id}/midia`

### Assumir chat — `POST /v1/whatsapp/chats/{id}/assumir`

Retorna objeto `WhatsappChatRead` atualizado (`estado`: `em_atendimento`).

---

## 7. Mapa de rotas API (referência)

| Módulo | Prefixo | Autenticação |
|--------|---------|--------------|
| Auth | `/v1/auth/*` | Público |
| Atendentes | `/v1/atendentes/*` | JWT |
| Dashboard | `/v1/dashboard` | JWT |
| Notificações | `/v1/notificacoes/*` | JWT |
| Tickets | `/v1/tickets/*` | JWT |
| WhatsApp chats | `/v1/whatsapp/chats/*` | JWT |
| Setores | `/v1/setores` | JWT (lista filtrada) |
| Status ticket | `/v1/status-ticket` | JWT |
| Catálogos ticket | `/v1/ticket-naturezas`, `/v1/ticket-motivos` | JWT |
| Respostas prontas | `/v1/respostas-prontas/disponiveis` | JWT |
| Redes/Empresas/Admin | `/v1/redes`, `/v1/empresas`, … | JWT **admin** |

OpenAPI completo: `{API_URL}/docs`

---

## 8. Navegação sugerida (mobile)

```
[Login]
   ↓
[Home / Dashboard] ← badge notificações
   ├── [WhatsApp]
   │     ├── Fila (aguardando) ← prioridade, alerta
   │     ├── Meus chats
   │     └── Conversa → Assumir | Enviar | Encerrar | Abrir ticket
   └── [Tickets]
         ├── Abertos / Meus / Fila
         └── Detalhe → Mensagens | Status | Assumir
```

**Bottom navigation sugerida:** Início | WhatsApp | Tickets | Perfil

---

## 9. Abordagem técnica mobile (resposta à AI Studio)

O projeto web já é **React + TypeScript**. Opções:

| Abordagem | Prós |
|-----------|------|
| **PWA / SPA mobile-first + Capacitor** | Reutiliza mental model React; empacota `.apk`/`.ipa`; API idêntica |
| **React Native (Expo)** | UX nativa; lógica de serviços/state portável do web |
| **Flutter / nativo** | Consome mesma REST API documentada acima |

**Recomendação do time:** React Native ou Capacitor consumindo **REST JSON** (Fetch/Axios), **não** GraphQL.

### Cliente HTTP (pseudocódigo)

```typescript
const API = 'https://api.exemplo.com/v1';

async function api(path: string, options: RequestInit = {}) {
  const token = await SecureStore.getItem('access_token');
  const res = await fetch(`${API}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
  if (res.status === 401) { /* refresh ou logout */ }
  if (!res.ok) throw await res.json();
  return res.json();
}
```

### Polling vs tempo real

Hoje o web usa **polling** para chat/notificações. Roadmap: **SSE** (#256) — mobile pode começar com polling (15–30s) e evoluir.

---

## 10. Credenciais de desenvolvimento

Somente ambiente local (nunca produção):

- E-mail: `admin@email.com`
- Senha: `admin123`

---

## 11. Repositório (para humanos)

- GitHub: `lgustavoss/dx-connect` (privado)
- Cliente HTTP tipado: `frontend/src/api/client.ts`
- Rotas web: `frontend/src/App.tsx`
- RBAC: `docs/BACKEND_RBAC.md`

---

## 12. Resposta pronta para colar na AI Studio

> **Projeto:** DX Connect — helpdesk para redes de postos.  
> **Backend:** FastAPI + JWT em `/v1` (não Django).  
> **Mobile v1:** app para **atendentes** (login, dashboard, notificações, **WhatsApp prioritário**, tickets).  
> **Começar por:** Login → Dashboard → Fila WhatsApp → Conversa (assumir/enviar/encerrar).  
> **Auth:** `POST /v1/auth/login` → Bearer token → `GET /v1/atendentes/me`.  
> **APIs principais:** `/dashboard`, `/notificacoes/resumo`, `/whatsapp/chats/fila`, `/whatsapp/chats/{id}/mensagens`, `/tickets`.  
> **Stack sugerida:** React Native ou Capacitor + TypeScript, Fetch/Axios, design mobile-first com bottom nav.  
> **Ver exemplos JSON completos** neste documento (secção 6).
