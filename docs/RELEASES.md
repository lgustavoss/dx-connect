# Releases — DX Connect (#400 / #672)

Guia de versionamento, CHANGELOG e o que o usuário vê em **Sobre**.

## CalVer (`YY.MM.NNN`)

| Exibição | Arquivo `VERSION` | Quando |
|----------|-------------------|--------|
| `v26.06.001` | `26.06.001` | 1º deploy do mês |
| `v26.06.002` | `26.06.002` | 2º deploy no mesmo mês |

Bump automático no **deploy de `staging`** (fuso `America/Sao_Paulo`).

## Dois produtos, um deploy

Uma CalVer por merge `main → staging`, mas **dois feeds** de notas:

| Produto | Código no manifest | Onde o usuário vê | API |
|---------|--------------------|-------------------|-----|
| DeskRudder (helpdesk na instância) | `deskrudder` | `/sobre` | `GET /v1/system/release-notes` |
| SaaS Control Plane | `saas` | `/saas/sobre` | `GET /v1/saas/release-notes` (RBAC `saas_ops`) |

- **Comercial** (CM/FN, simulador, custos) = DeskRudder (roda no cliente).
- **Landing / trial / leads B2B / licenças / planos** = SaaS.

## Fluxo do time

```
feature → PR main (+ CHANGELOG por produto) → PR main → staging (aprovação humana) → deploy → /sobre e /saas/sobre
```

1. **Cada PR para `main`** com mudança de produto: bullets em `CHANGELOG.md` → `## [Unreleased]` na **subseção do produto** certo
2. **PR `main → staging`**: o `[Unreleased]` descreve **todo o lote** que será publicado
3. **Merge em `staging`**: **só após análise e aprovação humana no GitHub** (`staging` = produção). Agentes/CI **não** mergeiam este PR automaticamente — usar `/release-staging` para abrir o PR e parar.
4. **Deploy em `staging`**: consome `[Unreleased]`, gera nova CalVer, append em `docs/releases/manifest.json` (cada bullet com `product`), zera `[Unreleased]`

## Formato do CHANGELOG

```markdown
## [Unreleased]

### DeskRudder

#### Melhorias

- Descrição curta para o atendente/admin (#123)

#### Correções

- …

### SaaS Control Plane

#### Melhorias

- Descrição curta para a equipe ops (#456)
```

Compatibilidade: bullets só com `### Melhorias` / `### Corrigido` (sem produto) → tratados como **DeskRudder** + warning no pipeline.

## Requisito de PR (obrigatório)

Se o PR altera código de produto, **`CHANGELOG.md` deve ter bullets em `[Unreleased]`** na subseção correta:

| Paths (heurística CI) | Subseção exigida |
|-----------------------|------------------|
| `frontend/src/pages/saas/`, `backend/app/api/saas*`, `backend/app/services/saas_*`, … | `### SaaS Control Plane` |
| Demais `backend/`, `frontend/src/`, … | `### DeskRudder` |
| Diff misto | **ambas** as subseções |

O CI executa `scripts/check_changelog.py` e **bloqueia merge** se faltar.

Isento (sem exigir CHANGELOG): só docs internos, planning, artefatos de release gerados, etc.

## O que o usuário vê

### `/sobre` (DeskRudder)

| Seção | Conteúdo |
|-------|----------|
| **Versão atual** | CalVer do deploy |
| **O que há de novo** | Só bullets `product=deskrudder` da release atual |
| **Histórico** | Releases anteriores **sem** cards que só tinham itens SaaS |

### `/saas/sobre` (ops)

Mesma CalVer; só bullets `product=saas` (licenças, planos, provisionamento, leads).

## Arquivos

| Arquivo | Função |
|---------|--------|
| `CHANGELOG.md` | Fonte editada pelo time; `[Unreleased]` → próxima release |
| `VERSION` | Versão publicada (sem `v`) |
| `docs/releases/manifest.json` | Histórico estruturado (`product` por bullet) |
| `backend/app/data/release_notes.json` | Payload da API (gerado no deploy) |
| `scripts/migrate_release_notes_product.py` | One-off / idempotente para taguear histórico (#676); `--reclassify-saas` corrige bullets «SaaS…» tagueados como DeskRudder |

A API `/v1/system/release-notes` também **reclassifica em runtime** bullets cujo texto começa com «SaaS» (histórico em produção anterior à migração).

Após cada deploy, o workflow commita `VERSION`, `CHANGELOG.md`, `manifest.json` e JSONs em `staging` (mensagem com `[skip ci]` para não redeployar).

## API (autenticada)

- `GET /v1/system/info` — versão em execução
- `GET /v1/system/release-notes` — feed DeskRudder
- `GET /v1/saas/release-notes` — feed SaaS (`saas_ops` + control plane ligado)

## Checklist — PR para `main`

- [ ] Bullets em `CHANGELOG.md` → `[Unreleased]` na subseção do produto (se mudou produto)
- [ ] Texto compreensível para o público certo (atendente vs ops), não jargão de dev

## Checklist — PR `main → staging`

- [ ] `[Unreleased]` lista **todas** as entregas do lote (por produto)
- [ ] Revisão de redação (sem «deploy», «branch», «commit»)
- [ ] **Aprovação e merge manuais** no GitHub (agente não executa `gh pr merge`)

## Desenvolvimento local

Validar CHANGELOG como no CI:

```bash
python scripts/check_changelog.py --base origin/main --head HEAD
```

Simular publicação (cuidado — altera arquivos):

```bash
python scripts/prepare_release.py --deploy
```

Reclassificar histórico do manifest:

```bash
python scripts/migrate_release_notes_product.py
```
