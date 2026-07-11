# IC-08 — Chat interno: paginação infinita no histórico

## Contexto

Follow-up pós-lote v2 do chat interno (#502, #503). Hoje a thread carrega `offset=0, limit=100` em ordem ASC — em conversas longas o usuário vê as mensagens **mais antigas**, não as recentes.

## Proposta

### Backend

- Constante fixa `MENSAGENS_POR_PAGINA = 50` (não exposta ao usuário)
- `GET /conversas/{id}/mensagens?antes_de_id=` opcional
  - Sem cursor: retorna as **50 mais recentes** (ordem cronológica no JSON)
  - Com `antes_de_id`: retorna até 50 mensagens **anteriores** ao id
- Resposta: `items`, `total`, `tem_mais_antigas: bool`
- Remover `offset`/`limit` configuráveis da API pública

### Frontend

- Carga inicial sem cursor
- Ao rolar perto do topo: `antes_de_id` = id da mensagem mais antiga carregada; **prepend** com preservação de scroll
- SSE/polling: merge por `id` (não substituir array inteiro)

## Critérios de aceite

- [ ] Conversa com 200+ mensagens abre nas mais recentes
- [ ] Rolar ao topo carrega bloco anterior sem pular posição
- [ ] Indicador «Carregando mensagens anteriores…» no topo
- [ ] SSE adiciona mensagem nova sem perder histórico já carregado
- [ ] Scroll inteligente (#504) continua funcionando
- [ ] Testes backend para cursor e `tem_mais_antigas`

## Regras de produto

- 50 mensagens por bloco, fixo no servidor

## Dependências

- Chat interno v1+v2 mergeados (#478, #502, #503)

## Fora de escopo

- Configuração de tamanho de página pelo usuário
- Paginação na inbox

## Origem

Lacuna identificada ao fechar épico #478 — lote `feat/chat-interno-v3`.
