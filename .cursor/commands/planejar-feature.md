# Planejar feature

Planeje uma feature **antes** de implementar. Use a skill `design-feature` como guia.

## Entrada

Se o usuário não passou referência, peça:
- número/link da **issue GitHub** (preferido) **ou**
- descrição livre da feature

Não peça caminho de `.md` local em `.github/planning-issue-bodies/` — a verdade está no GitHub.

## Fluxo

### 1. Contexto

- Ler issue/épico completo com `gh issue view`
- Ler código existente relacionado (use subagent `explore` se o domínio for grande)
- Identificar padrões vizinhos no repo (api/services/models similares)

### 2. Plano (skill design-feature)

Produzir plano **no chat** (não gravar ficheiro local) com:
- Escopo dentro/fora
- Mapa de arquivos (criar vs alterar)
- Decisões RBAC (admin vs atendente/comercial, setor_scope, casos 403)
- SSE e notificações (se aplicável)
- Migration Alembic (se aplicável)
- Ordem de implementação em etapas / lotes
- Testes mínimos
- Riscos e dúvidas em aberto

### 3. Validação com o usuário

- Apresente o plano completo
- Se houver ambiguidade de produto, **pare e pergunte** antes de seguir
- Não escreva código nesta fase
- **Não** criar `.md` em `planning-issue-bodies/` ou `analises/`

### 4. Persistir decisões (obrigatório se há issue)

Quando o utilizador confirmar decisões de produto:

```bash
gh issue comment <número> --body "..."
```

Incluir no comentário: decisões fechadas, fora de escopo, ordem de lotes/PRs.

### 5. Handoff

```
Plano pronto. Próximos passos:
/iniciar-feature
/implementar-issue #<número-da-issue-ou-lote>
```

**Não** commitar, criar ficheiros de código nem abrir PR nesta fase — só o plano no chat + comentário na issue.
