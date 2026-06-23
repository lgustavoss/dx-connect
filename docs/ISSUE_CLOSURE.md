# Encerramento de issues e follow-ups

Métrica padrão do time: **nenhuma entrega fecha sem rastrear o que ficou de fora**.

## Fluxo

```
Implementar (escopo da issue) → PR → merge → follow-ups? → fechar issue
                                      │
                                      └─ Sim: criar issues #NNN + linkar no comentário
```

## O que abrir como nova issue

| Situação | Ação |
|----------|------|
| Descoberta na implementação, fora do escopo atual | Nova issue + «Origem: #XXX» |
| Stub / campo nullable «até feature Y existir» e Y já mergeou | Nova issue para completar |
| Épico diz «issue futura» sem número | Criar issue antes de fechar o épico |
| Issue antiga substituída por épico filho | Fechar antiga com comentário (ex. superseded) |

## O que **não** misturar na issue atual

- Melhorias adjacentes «já que estamos aqui»
- UI completa quando a issue pedia só API
- Dashboard quando a issue era só backend de tickets

## Onde documentar

| Artefato | Uso |
|----------|-----|
| `.github/planning-issue-bodies/followups/` | Rascunho do corpo das issues follow-up |
| Comentário ao fechar issue/PR | Lista `Closes #X` + «Follow-ups: #416, #417» |
| `CHANGELOG.md` | Só o que **entrou** nesta release; follow-ups não entram até mergearem |

## Exemplo (épico SLA #259)

| Follow-up | Issue | Motivo |
|-----------|-------|--------|
| Métrica dashboard `sla_violacoes_abertas` | [#416](https://github.com/lgustavoss/dx-connect/issues/416) | Stub #282; SLA já existe |
| UI calendários comerciais | [#417](https://github.com/lgustavoss/dx-connect/issues/417) | #280 = policies; API #277 |
| Pausa SLA «aguardando cliente» | [#418](https://github.com/lgustavoss/dx-connect/issues/418) | Fora de escopo v1 #259 |
| SLA em WhatsApp | [#419](https://github.com/lgustavoss/dx-connect/issues/419) | Decisão de produto futura |
| Issue umbrella obsoleta | [#101](https://github.com/lgustavoss/dx-connect/issues/101) fechada | Substituída por #277–#281 |

## Checklist no PR (template)

Ver seção **Follow-ups / backlog** em `.github/pull_request_template.md`.
