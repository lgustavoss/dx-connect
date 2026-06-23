## Contexto

Follow-up pós-épico SLA (#259).

#277 entregou CRUD de calendários comerciais na **API**. #280 entregou seleção e listagem read-only na tela de policies. Não há editor visual para criar/editar calendários (horário semanal, feriados, timezone).

## Proposta

Em Configurações → Atendimento → SLA (ou subseção Calendários):

- Listar calendários comerciais
- Criar/editar/desativar (consome `/v1/sla/calendars`)
- Formulário de horário semanal (reutilizar padrão visual do WhatsApp se possível)
- Opção usar feriados nacionais

## Critérios de aceite

- [ ] CRUD completo via UI (admin-only)
- [ ] Validação de horários
- [ ] Calendário inativo não aparece em novos vínculos de policy

## Dependências

- Requer: #277 (API)

## Origem

Fora do escopo explícito de #280 (link/seleção apenas). Backlog v2 SLA.
