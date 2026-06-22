# Planejamento — DX Connect

## Onde fica cada coisa

| Tipo | Onde |
|------|------|
| Issues abertas (texto, aceite, comentários) | **GitHub** — fonte da verdade |
| Índice de épicos e números | [`ISSUES_CRIADAS.md`](ISSUES_CRIADAS.md) |
| Análises / spikes de viabilidade | [`analises/`](analises/) |

Não mantemos cópias locais do **corpo** de issues já publicadas no GitHub. Isso evita divergência entre repositório e o que o time revisa na issue.

## Como abrir issues novas

1. Criar direto no GitHub ou com `gh issue create`.
2. Usar labels e vincular ao épico/meta-issue relevante ([#16](https://github.com/lgustavoss/dx-connect/issues/16) para melhorias de produto).
3. Se fizer parte de um lote planejado, adicionar uma linha em [`ISSUES_CRIADAS.md`](ISSUES_CRIADAS.md) (só link e título — sem duplicar o corpo).

Para issues recorrentes (bug, feature), considere no futuro templates em `.github/ISSUE_TEMPLATE/` — padrão comum da comunidade para **orientar quem abre**, não para armazenar specs fechadas.

## Histórico

Antes desta pasta continha rascunhos `.md` + scripts (`create_planning_issues.py`, `create_commercial_planning_issues.py`) usados para criar issues em lote. Após criação e revisão no GitHub (#256–#308, #321–#375, etc.), os rascunhos foram removidos; permanecem apenas o índice e análises.
