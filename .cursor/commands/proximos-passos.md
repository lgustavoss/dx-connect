# Próximos passos

Analisa o que temos em aberto (fila SaaS + issues do GitHub + estado do repo) e recomenda o **próximo lote** de trabalho, com justificativa e o que está bloqueado.

Use a skill `analisar-backlog` como método. Esta fase **não** implementa nada: só diagnostica e recomenda.

## Entrada

Opcional:
- foco (`backend`, `frontend`, `faturamento`, `contratos`…)
- cliente/protocolo específico (`#S202611-0002`)
- épico (`#1390`)

Sem entrada: analisar tudo e recomendar o lote mais curto de maior impacto.

## Fluxo

1. **Fila SaaS**: `mcp__deskrudder-saas__listar_solicitacoes` com `status=aberta` e `status=em_analise`.
   Sem MCP → fallback HTTP de `/listar-solicitacoes`; sem credencial → avisar e seguir só com o GitHub.
2. **GitHub**: issues abertas (`gh issue list`), PRs abertos, último release (`CHANGELOG`).
3. **Repo**: `git status`/`git log` e conferir no código a premissa das issues candidatas.
4. **Cruzar**: pedido sem issue, issue sem pedido, premissa desatualizada.
5. **Recomendar**: 1 lote (1–3 issues) + alternativas + bloqueios + pontos de decisão.

## Saída esperada

Tabelas curtas no chat (não despejar JSON): fila pendente, candidatos com prontidão, e a recomendação com ordem de execução. Ver template na skill `analisar-backlog`.

## Regras

- Não triar sozinho, não alterar status no SaaS, não criar issue e não implementar código sem o usuário confirmar.
- pt-BR; nunca imprimir token.
- Plano/decisões vão para a issue no GitHub, não para `.md` local.

## Handoff

`/iniciar-feature` → `/implementar-issue #...`
