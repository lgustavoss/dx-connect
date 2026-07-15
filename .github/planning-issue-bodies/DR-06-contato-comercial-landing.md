# DR-06 — Contato comercial na landing (canal B2B)

## Contexto

Issue existente revisada: [#516](https://github.com/lgustavoss/dx-connect/issues/516).

**Decisão de produto (2026-07):** o chat do portal `/kb` serve o **cliente final** do cliente DeskRudder. O contato na landing é **prospect → comercial DeskRudder**. **Não** reutilizar `/kb/public/chat/*` nem `portal_chats` como canal de venda.

## Objetivo

Canal de contato na landing (`/`) da instância `deskrudder.com.br`: widget ou formulário + conversa/ticket no setor Comercial, domínio próprio (leads comerciais ou inbox dedicada).

## Escopo

### Dentro

- UX «Fale conosco» na LP-01
- Captura nome + e-mail (+ mensagem)
- Roteamento para equipe comercial na instância DeskRudder
- Modelo/API **separados** do portal KB do produto (pode inspirar UX, não compartilhar fila `/kb`)

### Fora

- Reuso de `portal_chats` / badge Portal do produto
- Trial (DR-07)
- CRM do produto CM02 (#322) — opcional integração futura

## Critérios de aceite

- [ ] Prospect inicia contato na landing; comercial DeskRudder recebe
- [ ] Fluxo **não** passa por endpoints `/kb/public/chat/*`
- [ ] `/kb` nas instâncias de clientes inalterado
- [ ] `npm run build` / testes relevantes passam

## Dependências

- Requer: LP-01 / #515 (slot)
- Substitui premissa antiga de #516

## Labels

`marketing`, `frontend`, `backend`, `ux`
