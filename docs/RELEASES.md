# Releases — DX Connect (#400)

Este documento descreve como versionamos entregas e como manter o changelog consumido pelo painel.

## CalVer (`YY.MM.NNN`)

- Formato: **`v26.06.001`** (exibição) / **`26.06.001`** (arquivo `VERSION`, sem prefixo `v`)
- Fuso de referência: **`America/Sao_Paulo`**
- **`.NNN`** reinicia em `001` a cada mudança de mês; incrementa dentro do mesmo mês
- Bump automático no **deploy de `staging`** (workflow `.github/workflows/deploy.yml`)

## Arquivos

| Arquivo | Função |
|---------|--------|
| `VERSION` | Versão atual (sem `v`) |
| `CHANGELOG.md` | Histórico humano; seção `[Unreleased]` é consumida no deploy |
| `docs/releases/manifest.json` | Manifesto estruturado de releases publicadas |
| `backend/app/data/release_notes.json` | Payload servido pela API (gerado por script) |
| `frontend/public/release-notes.json` | Cópia estática opcional para fallback/offline |

## Fluxo no deploy (`staging`)

1. `scripts/prepare_release.py --deploy` calcula a próxima CalVer, lê `[Unreleased]` do `CHANGELOG.md` e append em `manifest.json`
2. Atualiza `VERSION`, finaliza a seção no changelog e regenera `release_notes.json`
3. O build do frontend recebe `VITE_APP_VERSION` / `VITE_APP_VERSION_DISPLAY`
4. Artefatos de release (`VERSION`, `CHANGELOG.md`, manifest e JSON) são sincronizados para o VPS antes do build Docker
5. No VPS, `DX_CONNECT_VERSION` é aplicada ao container da API

> **Nota:** O bump no deploy atualiza os arquivos no runner e no VPS, mas **não faz commit automático** em `staging`. Para manter o repositório alinhado, commite manualmente ou automatize um bot após deploy.

## «Em breve»

Itens listados como **Em breve** vêm do diff Git **`origin/staging..origin/main`** (commits ainda não promovidos a staging). Categorização heurística: mensagens `fix…` → correções; demais → melhorias.

## API (autenticada)

- `GET /v1/system/info` — versão, ambiente, `git_sha`
- `GET /v1/system/release-notes` — release atual, histórico e upcoming

Visível para **todos os atendentes e admins** autenticados.

## Manutenção manual (antes do merge em `staging`)

1. Acrescente bullets em `CHANGELOG.md` under `## [Unreleased]`, agrupados por `### Melhorias`, `### Correções` ou `### Interno / Infra`
2. Após merge na `main` e promoção para `staging`, o deploy publica a release

## Desenvolvimento local

Regenerar JSON sem bump:

```bash
python scripts/prepare_release.py
```

Simular bump (não commitar em branch de feature):

```bash
python scripts/prepare_release.py --deploy
```
