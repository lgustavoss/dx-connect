# Planejar feature

Planeje uma feature **antes** de implementar. Use a skill `design-feature` como guia.

## Entrada

Se o usuário não passou referência, peça:
- caminho do body em `.github/planning-issue-bodies/` **ou**
- número/link da issue GitHub **ou**
- descrição livre da feature

## Fluxo

### 1. Contexto

- Ler issue/épico completo
- Ler código existente relacionado (use subagent `explore` se o domínio for grande)
- Identificar padrões vizinhos no repo (api/services/models similares)

### 2. Plano (skill design-feature)

Produzir plano com:
- Escopo dentro/fora
- Mapa de arquivos (criar vs alterar)
- Decisões RBAC (admin vs atendente, setor_scope, casos 403)
- SSE e notificações (se aplicável)
- Migration Alembic (se aplicável)
- Ordem de implementação em etapas
- Testes mínimos
- Riscos e dúvidas em aberto

### 3. Validação com o usuário

- Apresente o plano completo
- Se houver ambiguidade de produto, **pare e pergunte** antes de seguir
- Não escreva código nesta fase

### 4. Handoff

Encerre com:

```
Plano pronto. Próximos passos:
/iniciar-feature
/implementar-issue @<arquivo-da-issue.md>
```

**Não** commitar, criar arquivos de código nem abrir PR nesta fase — só o plano.
