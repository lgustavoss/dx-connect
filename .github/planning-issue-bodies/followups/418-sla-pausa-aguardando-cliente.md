## Contexto

Follow-up pós-épico SLA (#259).

O épico #259 documentou **fora de escopo v1**: pausa automática do relógio SLA quando ticket está em status tipo «aguardando cliente». #278 implementa pausa por **horário comercial** (fim de semana/feriados), não pausa por status.

## Proposta

- Flag em `StatusTicket` (ex.: `pausa_sla`) ou regra por status slug `aguardando_cliente`
- Motor de cálculo SLA deixa de contar minutos decorridos enquanto pausado
- Retomada ao sair do status
- Testes: pausa + retomada + violação após retomada

## Critérios de aceite

- [ ] Admin configura quais status pausam SLA (ou flag fixa no status)
- [ ] `GET /tickets/{id}/sla` reflete pausa
- [ ] Worker/alertas respeitam pausa

## Dependências

- Requer: #277, #278

## Origem

Explicitamente «issue futura» no corpo do épico #259.
