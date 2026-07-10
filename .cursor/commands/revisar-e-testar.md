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

## Executar testes

```bash
docker compose run --rm --no-deps backend pytest -q
cd frontend && npm run build
```

Se algum teste falhar, corrija antes de concluir a revisão.

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
- pytest: [passou/falhou]
- npm run build: [passou/falhou]
```

Se revisão OK, sugira:

```
/criar-pr
```

**Não** commitar, push ou criar PR a menos que o usuário peça ou use `/criar-pr`.
