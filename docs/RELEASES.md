# Releases — DX Connect (#400)

Guia de versionamento, CHANGELOG e o que o usuário vê em **Sobre** (`/sobre`).

## CalVer (`YY.MM.NNN`)

| Exibição | Arquivo `VERSION` | Quando |
|----------|-------------------|--------|
| `v26.06.001` | `26.06.001` | 1º deploy do mês |
| `v26.06.002` | `26.06.002` | 2º deploy no mesmo mês |

Bump automático no **deploy de `staging`** (fuso `America/Sao_Paulo`).

## Fluxo do time

```
feature → PR main (+ CHANGELOG) → PR main → staging → deploy → /sobre
```

1. **Cada PR para `main`** com mudança de produto: inclua bullet(s) em `CHANGELOG.md` → `## [Unreleased]`
2. **PR `main → staging`**: o `[Unreleased]` descreve **todo o lote** que será publicado
3. **Deploy em `staging`**: consome `[Unreleased]`, gera nova CalVer, append em `docs/releases/manifest.json`, zera `[Unreleased]`

## Requisito de PR (obrigatório)

Se o PR altera código de produto (`backend/`, `frontend/src/`, etc.), **`CHANGELOG.md` deve ter bullets em `[Unreleased]`**.

- Texto para o **usuário final** (curto, claro)
- Agrupe em `### Melhorias`, `### Correções` ou `### Interno / Infra`
- Um bullet por entrega relevante; referência `(#issue)` opcional

O CI executa `scripts/check_changelog.py` e **bloqueia merge** se faltar.

Isento (sem exigir CHANGELOG): só docs internos, planning, artefatos de release gerados, etc.

## O que o usuário vê em `/sobre`

| Seção | Conteúdo |
|-------|----------|
| **Versão atual** | CalVer em produção (`v26.06.002`) |
| **O que há de novo nesta versão** | Bullets publicados na **última** release |
| **Histórico** | Releases anteriores (`v26.06.001`, …) com os **mesmos bullets** de quando foram publicadas |

Exemplo após publicar `v26.06.002`:

- **O que há de novo** → itens do lote de `.002`
- **Histórico** → card `v26.06.001` com o texto que estava em «O que há de novo» antes

O histórico vem de `docs/releases/manifest.json`, append a cada deploy (nunca sobrescreve releases antigas).

## Arquivos

| Arquivo | Função |
|---------|--------|
| `CHANGELOG.md` | Fonte editada pelo time; `[Unreleased]` → próxima release |
| `VERSION` | Versão publicada (sem `v`) |
| `docs/releases/manifest.json` | Histórico estruturado de todas as releases |
| `backend/app/data/release_notes.json` | Payload da API (gerado no deploy) |

Após cada deploy, o workflow commita `VERSION`, `CHANGELOG.md`, `manifest.json` e JSONs em `staging` (mensagem com `[skip ci]` para não redeployar).

## API (autenticada)

- `GET /v1/system/info` — versão em execução
- `GET /v1/system/release-notes` — release atual + array `releases` (histórico)

## Checklist — PR para `main`

- [ ] Bullets em `CHANGELOG.md` → `[Unreleased]` (se mudou produto)
- [ ] Texto compreensível para atendente/admin, não jargão de dev

## Checklist — PR `main → staging`

- [ ] `[Unreleased]` lista **todas** as entregas do lote
- [ ] Revisão de redação (sem «deploy», «branch», «commit»)

## Desenvolvimento local

Validar CHANGELOG como no CI:

```bash
python scripts/check_changelog.py --base origin/main --head HEAD
```

Simular publicação (cuidado — altera arquivos):

```bash
python scripts/prepare_release.py --deploy
```
