# Análise de viabilidade: integração com retaguarda / ERP

## O que foi sugerido originalmente

Hoje o DX Connect guarda **metadados** sobre sistemas de retaguarda (ex.: campo `login_retaguarda` na rede, credenciais de acesso remoto no cadastro de PDV), mas **não há troca automática de dados** com o software de retaguarda do posto (PDV, NF, estoque, etc.).

A sugestão era criar uma **ponte bidirecional**:

1. **Retaguarda → DX Connect:** quando o sistema detecta falha (ex.: PDV offline, erro de sincronização NF), abrir ou atualizar um ticket automaticamente.
2. **DX Connect → Retaguarda:** consultar status do PDV/loja ao atender um chamado, evitando pedir informação que já existe no ERP.
3. **Sincronização de cadastro:** lista de PDVs/empresas alinhada entre os dois sistemas.

## Por que isso surgiu no contexto de postos

Redes de postos costumam ter:

- **Retaguarda proprietária** (ex.: produtos Duplexsoft) ou ERP de terceiros
- Chamados recorrentes do tipo «PDV travou», «NF não entrou», «preço não atualizou»
- Atendentes que alternam entre Connect e retaguarda para diagnosticar

Integrar reduziria retrabalho e permitiria **abertura proativa** de tickets antes do cliente ligar.

## O que já existe no código (base parcial)

| Recurso | Onde | Uso atual |
|---------|------|-----------|
| `login_retaguarda` | Model Rede | Metadado informativo |
| PDVs por empresa | `empresa_pdvs` | Código PDV, tipo acesso remoto, credenciais |
| Classificação motivo | `ticket_catalogos` | Motivos como «Falha no PDV», «Entrada de NF» |
| Tickets filhos em massa | #117 | Comunicados para toda a rede |

Nada disso **chama API externa** hoje.

## Níveis de integração (do mais simples ao mais complexo)

### Nível 1 — Link contextual (baixo esforço, alto valor imediato)

- No detalhe do ticket/chat, botão «Abrir retaguarda» com URL/login da rede
- Exibir código PDV e credenciais (já auditadas em `reveal_credential`)
- **Viabilidade:** alta; só frontend + dados já cadastrados
- **Recomendação:** pode virar issue pequena se desejado (não incluída neste lote)

### Nível 2 — Webhook unidirecional retaguarda → Connect (médio esforço)

- Endpoint autenticado: `POST /v1/integrations/retaguarda/evento`
- Payload: `{ rede_id, empresa_id, pdv_codigo, tipo_evento, descricao }`
- Connect abre ticket com classificação sugerida
- **Viabilidade:** média; depende de **contrato de API** com equipe retaguarda
- **Risco:** cada cliente pode ter retaguarda diferente → começar só com **produto próprio Duplexsoft**

### Nível 3 — Consulta status PDV (médio-alto esforço)

- Connect consulta API retaguarda: «PDV 03 online? última sync?»
- Exibe painel lateral no ticket
- **Viabilidade:** média; exige API estável e latência aceitável
- **Risco:** credenciais e permissões por rede

### Nivel 4 — Sincronização contínua de cadastro (alto esforço)

- Master data: empresas/PDVs sempre alinhados
- **Viabilidade:** baixa no curto prazo; conflito com cadastro manual atual
- **Recomendação:** adiar até produto interno maduro

## Recomendação alinhada ao roadmap atual

| Momento | Ação |
|---------|------|
| **Agora (uso interno)** | Não abrir épico de integração ERP; foco em tickets, chat, SLA, dashboards |
| **Curto prazo opcional** | Nível 1 (deep links + exibição contextual) se operação pedir |
| **Médio prazo** | Nível 2 **apenas** se equipe mobile/retaguarda definir contrato API com Duplexsoft |
| **App mobile** | Pode ser o **primeiro consumidor** de API Connect (não retaguarda direta) |

## Dependências para viabilizar Nível 2+

1. Documentação OpenAPI da retaguarda (eventos, autenticação)
2. Ambiente de homologação compartilhado
3. Mapeamento evento retaguarda → natureza/motivo ticket
4. Política de idempotência (mesmo evento não abre 10 tickets)
5. Acordo comercial sobre quais clientes usam integração

## Conclusão

A integração retaguarda **faz sentido estrategicamente** para redes de postos, mas **não é prioridade** enquanto o produto interno não estiver consolidado — alinhado à decisão do time sobre API pública (#12).

**Registrar como ideia futura** (issue tipo *research/spike*) somente quando:

- Produto interno estável
- Equipe retaguarda disponível para definir contrato
- Pelo menos um cliente piloto confirmado

Até lá, os metadados de PDV e classificação por motivo já cobrem boa parte do fluxo **manual** de suporte.
