---
name: analisar-backlog
description: Analisa a fila SaaS e as issues abertas do GitHub para recomendar o próximo lote de trabalho do DX Connect. Use ao decidir "o que fazer agora", revisar prioridades ou preparar um ciclo novo.
---

# Analisar backlog — DX Connect

Objetivo: responder **"qual é o próximo passo?"** com evidência, cruzando **fila SaaS**, **GitHub** e **estado real do código**. Não implementar nesta fase.

## Quando usar

- Início de ciclo, depois de um release, ou quando o usuário perguntar "o que podemos implementar?"
- Antes de `/planejar-feature` ou de montar um lote para `/implementar-issue`
- Quando surgir dúvida entre pedido de cliente e item de épico interno

## Regras

- **pt-BR** sempre (UI, chat, comentários).
- **Não triar sozinho**: não alterar status no SaaS, não criar issue, não comentar para o cliente sem pedido explícito do usuário. Ações de escrita só depois de confirmação.
- **Não inventar a fila**: se o MCP `deskrudder-saas` não estiver disponível, usar o fallback HTTP documentado em `/listar-solicitacoes`. Sem token, dizer que a fila não pode ser lida — nunca preencher com suposição.
- **Nunca imprimir token**, nem colar credenciais no chat.
- **Plano não vira `.md` local**: decisões vão para a issue no GitHub (rule `planning-github-source`).
- Separar **fato** (dados coletados) de **recomendação** (julgamento).

## Passo 1 — Fila SaaS (pedidos de cliente)

Chamar `mcp__deskrudder-saas__listar_solicitacoes` **duas vezes**, com `status=aberta` e `status=em_analise` (limit 50).

Coletar por item: `protocolo` (#SYYYYMM-NNNN), `titulo`, `tipo` (sugestão/problema), `status_rotulo`, `instance_slug`/`cliente_nome`, `peso_clientes`, `github_issue_number`, `versao_contexto`, `created_at_origem`.

Interpretar:
- `total=0` → fila vazia (não "sem dados").
- `peso_clientes > 1` → vários clientes pedindo o mesmo: sobe a prioridade.
- **sem `github_issue_number`** → pedido ainda **não triado**: não entra em implementação antes de virar issue.
- Só buscar detalhe com `obter_solicitacao` para itens que entram no lote recomendado (economiza contexto).

## Passo 2 — Issues do GitHub (backlog interno)

```bash
gh issue list --limit 120 --state open --json number,title,labels,milestone,updatedAt
gh pr list --state open
gh issue list --limit 20 --state closed --search "sort:updated-desc"
```

Agrupar por **épico/fase** (ex.: o épico de produto vigente, com fases P0→P3) e marcar para cada candidato: prioridade da fase, dependências declaradas no corpo, e se tem bloqueio externo (credencial, infra, parecer, decisão de produto).

Ler o corpo só dos candidatos que sobem no ranking (`gh issue view <n>`).

## Passo 3 — Estado do repositório

```bash
git status --short --branch
git log --oneline -10
```

- Ver `CHANGELOG.md` → seção `[Unreleased]`: o que já está pronto.
- **Conferir no código a premissa de cada candidata** antes de recomendar: o arquivo citado na issue ainda tem o comportamento descrito? (issue desatualizada é comum). Use `grep`/`read` escopados.

## Passo 4 — Cruzar as fontes

Montar a tabela:

| Item | Origem | Cliente/Peso | Estado | Bloqueio | Prontidão |
|------|--------|--------------|--------|----------|-----------|

E reportar explicitamente os três buracos:
1. **solicitação sem issue** — pedido que ainda não foi triado;
2. **issue sem relação com pedido** — backlog interno (épico/técnico);
3. **issue com premissa inválida** — o código já mudou ou já entrega parte do escopo.

## Passo 5 — Classificar e recomendar

Classificar cada candidato em:
- **pronto** — sem dependência externa, dá para começar hoje;
- **bloqueado** — falta credencial, infraestrutura, parecer jurídico ou decisão de produto;
- **dependente** — espera outra issue do próprio backlog.

Ordem de prioridade (aplicar em sequência):
1. fase **P0** do épico vigente;
2. **peso/nº de clientes** e impacto operacional (fila SaaS);
3. **prontidão** (destravar o bloqueado só se o desbloqueio for barato);
4. **esforço** (lote curto antes de um épico);
5. **risco** (migration, RBAC, integração externa).

Recomendar:
- **1 lote** (1–3 issues) com justificativa curta e ordem de execução;
- **2ª e 3ª opção** em uma linha cada;
- **pontos de decisão** que dependem do humano (ex.: RBAC, migration, custo de provedor);
- **não escrever código** nem abrir PR nesta fase.

## Saída — template

```markdown
## Fila SaaS — N pendentes
| Protocolo | Título | Cliente | Tipo | Status | Peso |
|---|---|---|---|---|---|

## Issues abertas — resumo
- <épico/fase>: #x, #y (P0); #z bloqueada por ...

## Cruzamento
- Pedidos sem issue: ...
- Issues sem pedido: ...

## Recomendação
**Lote:** ...
**Por quê:** ...
**Riscos/decisões:** ...

## Próximo passo
/iniciar-feature → /implementar-issue #...
```

## Handoff

- Lote aprovado → `/iniciar-feature` e `/implementar-issue #...`
- Feature nova/épico → `/planejar-feature`
- Triagem de solicitação (só se o usuário pedir) → `alterar_status` + `implementar` no MCP, com o protocolo confirmado
