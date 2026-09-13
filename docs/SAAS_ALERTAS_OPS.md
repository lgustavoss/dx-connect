# Alertas operacionais SaaS Ops (#1036 / #1040)

Catálogo MVP de sinais, severidades e playbook para a equipe DeskRudder no **painel admin** (`/saas/alertas`).  
Não aparece na aplicação da instância do cliente.

## Acesso

| Quem | Acesso |
|------|--------|
| `saas_ops` no control-plane | Após selecionar o cliente: lista, filtros, detalhe |
| Admin/atendente da instância | Sem acesso (403/404) |
| Cliente final | Sem acesso |

**UI:** `/saas/alertas` não carrega alertas de todos os clientes ao abrir — é obrigatório escolher o cliente (query `?cliente=`). A API de listagem exige `cliente_saas_id`.

**Escopo de deploy:** o motor roda só no control-plane e faz probe HTTP (`/health`, `/ready`) + lê `stack_status` já gravado. Não altera containers nem imagens das instâncias cliente.

**Changelog:** bullet em `### SaaS Control Plane` — aparece em `/saas/sobre` (Ops). A página Sobre da instância (`product=deskrudder`) não exibe essas notas.

## Severidades

| Código | Uso |
|--------|-----|
| `amarelo` | Degradação ou risco; serviço pode estar parcial |
| `vermelho` | Indisponibilidade ou falha crítica; ação imediata |

## Estados do alerta

| Estado | Significado |
|--------|-------------|
| `ativo` | Sinal ainda presente |
| `mitigado` | Ops reconheceu / contornou; sinal pode persistir |
| `resolvido` | Sinal normalizou (health OK / stack running) |

**Mitigado vs resolvido:** mitigado é ação humana (marcar no painel); resolvido é automático quando o motor deixa de ver o sinal.

## Sinais MVP

| Código | Módulo | Severidade | Quando abre | Quando resolve |
|--------|--------|------------|-------------|----------------|
| `instancia_indisponivel` | `api` | vermelho | Probe `GET /health` falha (timeout, conexão, HTTP ≠ 2xx) | Probe OK |
| `instancia_nao_pronta` | `api` | amarelo | `GET /health/ready` retorna 503 / status degradado | Ready OK |
| `stack_parada` | `stack` | vermelho | `stack_status == stopped` | `stack_status == running` |
| `stack_desconhecida` | `stack` | amarelo | Instância provisionada (`sucesso`) e `stack_status` vazio/`unknown` | `stack_status == running` |

Limiares padrão (configuráveis via env):

- Intervalo do worker: `SAAS_ALERTAS_OPS_INTERVAL_SECONDS` (padrão 120)
- Timeout HTTP do probe: `SAAS_ALERTAS_OPS_PROBE_TIMEOUT_SECONDS` (padrão 5)
- Falhas consecutivas antes de abrir `instancia_indisponivel`: `SAAS_ALERTAS_OPS_PROBE_FALHAS` (padrão 2)

## Playbook rápido

### Triagem inicial
1. Abrir `/saas/alertas` e **selecionar o cliente**.
2. Filtrar por severidade vermelho (se necessário) e abrir o detalhe com a evidência (URL probeada, status HTTP, `stack_status`).
3. Conferir licença em `/saas/licencas/:id` (provisionamento, porta, URL).

### Validações na VPS
1. `curl -sf http://127.0.0.1:{api_port}/health` e `/health/ready`
2. `docker compose … ps` / `stack-client.sh health` do cliente
3. Logs do container API da instância (sem colar segredos no painel)

### Comunicação interna
- Comentar no canal Ops com slug do cliente, código do sinal e horário de início.
- Se impacto ao usuário final: coordenar mensagem via fluxo comercial (não pelo alerta).

### Encerramento
- Preferir deixar o motor **resolver** sozinho após normalizar.
- Usar **mitigar** só quando houver contorno consciente (ex.: manutenção planejada).

## Fora do MVP

- Streaming bruto de logs da instância
- Taxa 5xx / fila de jobs / pico de auth (requer métricas/ingest)
- Auto-remediação e on-call externo
- Health Center completo (#888–#890)

## Relação

- Épico #1036 · motor #1037 · API #1038 · UI #1039 · este catálogo #1040
- Complementa renovação comercial (`SaasAlertaEmitido`) — domínio separado
