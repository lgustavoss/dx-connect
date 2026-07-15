# DR-07 — Trial / pré-cadastro

## Contexto

Ex-LP-03. Parte do épico SaaS (Fase 4 do roadmap).

## Objetivo

Formulário público (landing ou rota dedicada) que cria lead + licença em status `trial` e, quando DR-04 existir, dispara ou enfileira provisionamento.

## Escopo

### Dentro

- Formulário: nome, e-mail, empresa, slug desejado
- Cria registro SaaS `trial` com prazo configurável
- Notifica equipe DeskRudder
- Ligação opcional a DR-04

### Fora

- Gateway de pagamento
- Trial self-service total sem revisão humana (pode ser v1 com aprovação manual)

## Critérios de aceite

- [ ] Submissão cria registro trial visível no painel DR-03
- [ ] Validação de slug (formato + unicidade)
- [ ] E-mail/notificação interna à equipe

## Dependências

- Requer: DR-01, DR-02, DR-03
- Ideal: DR-04 para provision automático

## Labels

`enhancement`, `frontend`, `backend`, `marketing`
