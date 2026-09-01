# Releases — DX Connect (#400 / #672)

Guia de versionamento, CHANGELOG e o que o usuário vê em **Sobre**.

## CalVer (`YY.MM.NNN`)

| Exibição | Arquivo `VERSION` | Quando |
|----------|-------------------|--------|
| `v26.06.001` | `26.06.001` | 1º deploy do mês |
| `v26.06.002` | `26.06.002` | 2º deploy no mesmo mês |

Bump automático no **deploy de `staging`** (fuso `America/Sao_Paulo`).

## Uma CalVer, umas notas (#920)

Uma versão por merge `main → staging`. **Um** CHANGELOG / manifest — as subsecções `### DeskRudder` e `### SaaS Control Plane` são **tags** (produto vs devops), não feeds separados.

| Tag no manifest | Significado | Quem vê |
|-----------------|-------------|---------|
| `deskrudder` (**Produto**) | Helpdesk na instância (chat, tickets, ponto, comercial na rede…) | `/sobre` (só estas) e `/saas/sobre` (com etiqueta) |
| `saas` (**DevOps**) | Control-plane (licenças, planos, provisionamento, leads, equipa ops) | só `/saas/sobre`, com etiqueta DevOps |

- **Comercial** (CM/FN, simulador, custos) = Produto (roda no cliente).
- **Landing / trial / leads B2B / licenças / planos** = DevOps.

## Fluxo do time

```
feature → PR main (+ CHANGELOG com tags Produto/DevOps) → PR main → staging (aprovação humana) → deploy → /sobre e /saas/sobre
```

1. **Cada PR para `main`** com mudança visível: bullets em `CHANGELOG.md` → `## [Unreleased]` na **subseção** certa (tag Produto ou DevOps)
2. **PR `main → staging`**: o `[Unreleased]` descreve **todo o lote** que será publicado
3. **Merge em `staging`**: **só após análise e aprovação humana no GitHub** (`staging` = produção). Agentes/CI **não** mergeiam este PR automaticamente — usar `/release-staging` para abrir o PR e parar.
4. **Deploy em `staging`**: consome `[Unreleased]`, gera nova CalVer, append em `docs/releases/manifest.json` (cada bullet com `product`), zera `[Unreleased]` e commita em `staging` (`chore(release): publica v… [skip ci]`)
5. **Sync na `main`** (obrigatório, mesmo comando `/release-staging`): após Deploy verde, PR `chore/sync-changelog-…` → `main` copiando artefatos de `origin/staging` e preservando bullets de `[Unreleased]` que existam só na `main` (`origin/staging..origin/main`). Ver Passo 5 em `.cursor/commands/release-staging.md`.

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

Isento (sem exigir CHANGELOG): só docs internos, planning, artefatos de release gerados, **somente** bumps em `package.json` / `package-lock.json` / `requirements*.txt`, **somente** alterações em `backend/tests/`, etc.

## O que o usuário vê

### `/sobre` (DeskRudder — produto)

| Seção | Conteúdo |
|-------|----------|
| **Versão atual** | CalVer do deploy |
| **O que há de novo** | Só bullets `product=deskrudder` da release atual |
| **Histórico** | Releases anteriores **sem** cards que só tinham itens DevOps |

### `/saas/sobre` (ops — tudo, com tags)

Mesma CalVer e as **mesmas** notas. Cada bullet mostra etiqueta **Produto** ou **DevOps**.

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
- `GET /v1/system/release-notes` — só bullets de produto (painel da instância)
- `GET /v1/saas/release-notes` — todas as notas, com `product` em cada bullet (`saas_ops` + control plane ligado)

## Checklist — PR para `main`

- [ ] Bullets em `CHANGELOG.md` → `[Unreleased]` na subseção do produto (se mudou produto)
- [ ] Texto compreensível para o público certo (atendente vs ops), não jargão de dev

## Checklist — PR `main → staging`

- [ ] `[Unreleased]` lista **todas** as entregas do lote (por produto)
- [ ] `python scripts/check_changelog.py --base origin/staging --head origin/main` → **OK** (merge simulado; evita `[Unreleased]` vazio após conflito de CHANGELOG)
- [ ] Revisão de redação (sem «deploy», «branch», «commit»)
- [ ] **Aprovação e merge manuais** no GitHub (agente não executa `gh pr merge`)

## Checklist — pós-deploy (sync `main`)

Executado pelo agente no **Passo 5** de `/release-staging` (após merge do release + Deploy verde em `staging`):

- [ ] Workflow Deploy em `staging` concluído (commit `chore(release): publica v…`)
- [ ] `CHANGELOG.md` na `main` alinhado com `staging` (seção CalVer nova; `[Unreleased]` sem itens já publicados)
- [ ] `VERSION`, `manifest.json` e JSONs de release notes sincronizados
- [ ] Se `main` tem commits à frente de `staging`, bullets novos **permanecem** em `[Unreleased]`
- [ ] PR `chore/sync-changelog-…` → `main` mergeado (CI verde)

## Desenvolvimento local

O Docker da API só monta `backend/` — o ficheiro `VERSION` da raiz **não** entra no contentor. A API usa então `current_version` de `backend/app/data/release_notes.json`, para **Sobre** não ficar vazio.

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
