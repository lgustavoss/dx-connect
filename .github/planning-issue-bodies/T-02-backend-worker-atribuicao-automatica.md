# Distribuição tickets — worker de atribuição automática (backend)

## Contexto

Épico: **Distribuição automática de tickets**.

Parte de: **T-F2**

## Proposta

Worker periódico (30–60s) + hook pós-criação ticket:

1. Lista tickets `atendente_id IS NULL` em setores com auto
2. Filtra elegíveis (status aberto, não encerrado)
3. Para `auto_apos_timeout`: `created_at + timeout < now`
4. Seleciona atendente via estratégia (round-robin persistido em `setor_distribuicao_state`)
5. Atribui + histórico status opcional «Atribuído automaticamente»
6. Notifica atendente (#109)

**Concorrência:** lock ticket row FOR UPDATE.

## Critérios de aceite

- [ ] Dois workers não atribuem mesmo ticket
- [ ] Atendente inativo excluído
- [ ] Admin sempre elegível se vinculado? (definir: sugerido **não** auto-atribuir admin)
- [ ] Testes estratégias round-robin e carga

## Dependências

- Requer: T-01

## Labels

`backend`, `tickets`, `fase-interna`, `distribuicao`
