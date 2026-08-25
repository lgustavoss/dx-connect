# Listar solicitações

Mostra no chat as solicitações **pendentes** da fila SaaS DeskRudder (o mesmo painel `/saas/solicitacoes`).

Este arquivo está no git (`.cursor/commands/`). Depois de um `git pull`, se `/listar-solicitacoes` não aparecer, recarregue a janela do Cursor.

## Pré-requisito — MCP no PC de cada pessoa

A fila **não** está no clone local. Cada desenvolvedor liga o MCP **no próprio Cursor** (`.cursor/mcp.json` é gitignored, não compartilhe token):

1. Copiar `.cursor/mcp.json.example` → `.cursor/mcp.json`
2. Entrar no painel admin (`https://deskrudder.com.br/login/admin`) com a conta `saas_ops`
3. Abrir **Minha conta** (`/saas/conta`) e gerar o token Cursor (aparece **uma vez**)
4. Colar em `DESKRUDDER_MCP_TOKEN`. A URL do example é a **API comercial**:
   `https://api.deskrudder.com.br`
   (épico #875 — stack própria, não a da DuplexSoft). Enquanto o split não estiver no ar, esse host ainda não existe; não use a API do cliente como se fosse o control-plane.
5. Cursor → Settings → MCP → habilitar `deskrudder-saas` (fica verde)
6. No Windows, se o servidor não iniciar: trocar `"command": "python"` por `"command": "py"`

Sem MCP ligado: **não inventar a fila**. Pedir para completar os passos acima. Não ler nem imprimir o token.

## O que é «pendente»

Por omissão: status `aberta` (Recebida) e `em_analise`.

Se o usuário pedir «todas», «planejadas» ou um protocolo/`#S…`, use esse filtro em vez do padrão.

## Como listar

Chamar `listar_solicitacoes` **duas vezes** (ou HTTP `GET /v1/saas/solicitacoes?status=…&limit=50`):

- `status=aberta`
- `status=em_analise`

Não misturar com notas internas, GitHub ou peso se o usuário só pediu um resumo — o peso (`peso_clientes`) pode ir numa coluna curta.

## Apresentação (português do Brasil)

Tabela ou lista compacta:

| Campo | Origem |
|-------|--------|
| Protocolo | `#SYYYYMM-NNNN` |
| Título | título |
| Cliente | slug da instância |
| Tipo | sugestão / problema |
| Status | rótulo (Recebida / Em análise) |
| Peso | `peso_clientes` se > 1 |

No topo: total pendente. Se `total=0`, dizer que a fila está vazia (ainda não chegou pedido ao control-plane).

Não despejar JSON cru. Não citar o `mcp.json`.

## HTTP de fallback (sem a ferramenta MCP, com `mcp.json` já configurado)

`GET {DESKRUDDER_API_URL}/v1/saas/solicitacoes?status=aberta&limit=50` com `Authorization: Bearer {DESKRUDDER_MCP_TOKEN}`.

Não imprimir o token.

## Depois da listagem

Só se o usuário pedir: detalhe (`obter_solicitacao`), alterar status, comentar, vincular pedidos ou ligar issue GitHub. Não triar sozinho.

Comentário ao cliente: **português do Brasil**, sem GitHub/`issue #`. Sem pedido explícito de falar com o cliente, use nota interna (`publico_cliente=false`).
