# IC-10 — Chat interno: grupos personalizados

## Contexto

Follow-up épico #478. Atendentes precisam de conversas com **N participantes** escolhidos manualmente, além de direta 1:1 e canal de setor.

## Proposta

### Modelo (migration 063)

- `tipo = 'grupo'`
- `titulo VARCHAR(120) NOT NULL` para grupos
- `CheckConstraint` atualizado: setor exige `setor_id`; direta/grupo exigem `setor_id IS NULL`
- `conversas_internas_participantes`: coluna `papel` (`admin` | `membro`); criador entra como `admin`

### Regras de produto

- Máximo **50 atendentes** por grupo (incluindo criador)
- **Admins** do grupo: criador (automático) + membros promovidos a admin
- Só **admins** adicionam/removem membros e promovem/rebaixam admins
- Removido: não vê nem envia mensagens **novas**; histórico no grupo **preservado** para quem permanece
- Admin global do sistema **não** vê grupos dos quais não participa (privacidade = direta)

### API

- `POST /conversas/grupo` — `{ titulo, atendente_ids[] }`
- `PATCH /conversas/{id}/participantes` — adicionar/remover/promover (admins)
- Inbox inclui `tipo=grupo` com título

### Frontend

- Fluxo «Novo grupo» no modal de conversa (nome + multi-select)
- Filtro inbox «Grupos»; visual distinto na lista e thread
- Tela/modal gerenciar membros (admins)

### SSE / notificações

- Destinatários = participantes ativos (como direta)

## Critérios de aceite

- [ ] Criar grupo com 3+ atendentes; todos veem na inbox
- [ ] Não-participante recebe 403
- [ ] Admin do grupo adiciona/remove membro; membro comum não
- [ ] Removido some da inbox e não acessa thread; histórico intacto para demais
- [ ] Mensagens, mídia, reações, edição e paginação funcionam em grupo
- [ ] Testes backend (RBAC 403, limite 50)

## Dependências

- IC-08, IC-09 recomendados antes ou no mesmo lote

## Fora de escopo

- Grupos com permissões granulares além de admin/membro
- Chat com funcionários da rede

## Origem

Fora de escopo v1 #478 — lote `feat/chat-interno-v3`.
