# Revisar e testar

Revise as alterações atuais (working tree ou PR) antes de merge/deploy.

## Escopo da revisão

Analise `git diff` e commits recentes. Se o usuário indicou arquivos ou PR, foque neles.

Confirme que a branch **não** é `main`/`staging`. Se for, avise para usar `/iniciar-feature`.

## Checklist de qualidade

### Geral
- [ ] Mudança mínima — sem refatoração não solicitada
- [ ] Critérios de aceite da issue atendidos
- [ ] Strings de UI/erro em português

### Backend
- [ ] Lógica na camada `services/`, rotas finas
- [ ] RBAC: admin vs atendente + escopo por setor (`setor_scope`)
- [ ] Testes cobrem caminho feliz e casos de 403/404 relevantes
- [ ] Migration: `revision`/`down_revision` consistentes; um único head

### Frontend
- [ ] API via `client.ts`; erros via `errorMessage.ts`
- [ ] Rotas admin protegidas com `AdminRoute`
- [ ] SSE integrado corretamente (sem conexão duplicada)

### Tempo real
- [ ] Eventos publicados após commit DB
- [ ] Payload compatível com consumidores existentes

## Executar testes (só o que o diff toca)

Mesma regra do GitHub Actions (`scripts/ci_detect_changes.py`): pytest do backend **não** corre em PR só de frontend, e `npm run build` **não** corre em PR só de backend.

```bash
git fetch origin
python scripts/ci_detect_changes.py --base origin/main --include-working-tree
```

Interprete `backend=true` / `frontend=true` e execute **apenas** o que aplicar:

```bash
# se backend=true
docker compose run --rm --no-deps backend pytest -q

# se frontend=true
cd frontend && npm run build
```

- `backend=false` → **não** rode pytest; no relatório: `pytest: omitido (diff sem backend/scripts/CI)`
- `frontend=false` → **não** rode `npm run build`; no relatório: `npm run build: omitido (diff sem frontend/CI)`
- Os dois `true` → rode os dois
- Os dois `false` (só docs/Cursor) → não rode testes pesados; diga isso no relatório

Se o script falhar (sem `origin/main`), assuma os dois `true`.

Se algum teste **executado** falhar, corrija antes de concluir a revisão.

Após mudar `backend/requirements-dev.txt`, faça `docker compose build backend` antes do pytest (a imagem precisa de `pytest-xdist`).

## Formato do relatório

```markdown
## Resumo
[1–2 frases]

## 🔴 Crítico (bloqueia merge)
- ...

## 🟡 Sugestão
- ...

## 🟢 OK / observações
- ...

## Testes executados
- pytest: [passou / falhou / omitido — motivo]
- npm run build: [passou / falhou / omitido — motivo]
```

Se revisão OK, sugira:

```
/criar-pr
```

**Não** commitar, push ou criar PR a menos que o usuário peça ou use `/criar-pr`.
