# Planejamento — DX Connect

## Onde fica cada coisa

| Tipo | Onde |
|------|------|
| Issues, aceite, decisões, comentários de plano | **GitHub** — fonte da verdade |
| Índice opcional de épicos/números | [`ISSUES_CRIADAS.md`](ISSUES_CRIADAS.md) (só links — sem duplicar corpo) |
| Análises antigas (legado) | [`analises/`](analises/) — **não criar novos** por defeito; preferir comentário/issue no GitHub |

Épico SaaS DeskRudder (licenças/instâncias): [#519](https://github.com/lgustavoss/dx-connect/issues/519).

Não mantemos cópias locais do **corpo** de issues nem planos de feature em `.md`. Isso evita divergência e acumulação de rascunhos.

## Como abrir issues novas

1. Criar direto no GitHub ou com `gh issue create`.
2. Usar labels e vincular ao épico/meta-issue relevante ([#16](https://github.com/lgustavoss/dx-connect/issues/16) para melhorias de produto).
3. Se fizer parte de um lote, opcionalmente uma linha em [`ISSUES_CRIADAS.md`](ISSUES_CRIADAS.md) (só link e título).

## Como planear (`/planejar-feature`)

1. Plano no **chat**.
2. Decisões confirmadas → `gh issue comment` na issue/épico.
3. Sem ficheiro local em `analises/` ou `followups/`.

## Histórico

Antes havia rascunhos `.md` + scripts para criar issues em lote. Após publicação no GitHub, os corpos locais foram removidos. A pasta `analises/` ainda tem docs legados; novos planos vão para o GitHub.
