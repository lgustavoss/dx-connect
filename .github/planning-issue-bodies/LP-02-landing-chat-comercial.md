# [Marketing] Contato comercial na landing — canal B2B (LP-02)

## Contexto

Épico: **DeskRudder SaaS** (licenças, instâncias e go-to-market) + landing [#515](https://github.com/lgustavoss/dx-connect/issues/515).

Parte de: **LP-01** (landing institucional) e **DR-06**.

### Decisão de produto (2026-07)

O DeskRudder é vendido para empresas de suporte. O portal `/kb` é **módulo do produto por instância**: cada cliente DeskRudder publica manuais (e chat opcional) para o **cliente final dele**.

| Canal | Público | Objetivo |
|-------|---------|----------|
| Chat `/kb` na instância do cliente | Cliente final | Suporte / dúvida sobre manuais daquele cliente |
| Contato na landing `deskrudder.com.br` | Prospect | Comercial DeskRudder (venda / demo) |

**Não** reutilizar `/kb/public/chat/*`, `portal_chats` nem o badge «Portal» do produto como funil de venda.

Análise: `.github/planning-issue-bodies/analises/saas-deskrudder-licencas-vs-produto.md`

## Objetivo

Exibir contato **«Fale conosco»** na landing (`/`) da instância comercial DeskRudder, com captura de lead (nome + e-mail + mensagem) e atendimento pela equipe comercial — domínio de dados **próprio** (não a fila do portal KB).

## Pré-requisitos operacionais (fora do código)

Na instância `deskrudder.com.br`:

- [ ] Setor **Comercial** (ou equivalente)
- [ ] Atendentes responsáveis por prospects
- [ ] Processo para monitorar leads/conversas comerciais (inbox ou tickets dedicados)

## Proposta técnica (v1)

### Abordagem

Canal B2B dedicado na superfície SaaS. Pode **inspirar** UX no widget do `/kb`, mas:

- Novos endpoints e/ou modelo (ex. `comercial_leads` / conversas comerciais), **ou** ticket público no setor Comercial
- **Não** chamar `POST /kb/public/chat/session`
- **Não** misturar com `portal_chats` das instâncias de clientes

### Arquivos / áreas prováveis

| Ação | Caminho |
|------|---------|
| criar | API + modelo lead/conversa comercial (backend) |
| criar | Widget/formulário na landing (`frontend/src/pages/marketing/` ou `components/marketing/`) |
| alterar | `LandingPage` / slot CTA (LP-01) |
| testes | Backend + smoke na instância comercial |

### Textos sugeridos

| Elemento | Copy |
|----------|------|
| Botão / CTA | «Fale conosco» |
| Formulário | Nome + e-mail (+ mensagem) |
| Título | «Tire dúvidas sobre o DeskRudder» |
| Placeholder | «Como podemos ajudar?» |

## Escopo

### Dentro

- Contato na landing LP-01
- Persistência e atendimento na instância DeskRudder (comercial)
- Graceful se canal desabilitado (landing não quebra)
- `npm run build` / testes relevantes

### Fora

- Reuso da API/fila `/kb/public/chat/*`
- Alterar comportamento do `/kb` nas instâncias de clientes
- Trial / pré-cadastro (DR-07)
- Painel completo de CRM produto (#322)
- Provisionamento (DR-04)

## RBAC e privacidade

- Rotas públicas de captura — sem auth do visitante
- Dados do prospect só na BD da **instância comercial** DeskRudder
- Atendentes comercial/admin veem leads; não expor a outras instâncias

## Critérios de aceite

- [ ] Prospect inicia contato na landing; equipe comercial recebe
- [ ] Fluxo **não** usa `/kb/public/chat/*` nem `portal_chats` do produto
- [ ] `/kb` em instâncias de clientes permanece inalterado
- [ ] Copy é de contato comercial DeskRudder
- [ ] Landing não quebra se canal estiver desligado
- [ ] `npm run build` passa

## Testes

- [ ] Fluxo visitante → comercial → resposta (staging instância comercial)
- [ ] Regressão: chat `/kb` do produto em instância de cliente

## Dependências

- **Requer:** LP-01 / #515 (slot)
- **Épico SaaS:** DR-06
- **Relacionado:** DR-07 (trial), DR-01+ (licenças)

## Ordem sugerida (mesmo lote com LP-01)

1. LP-01 — layout landing + rota `/` (#515)
2. LP-02 / DR-06 — canal comercial B2B
3. Smoke ponta a ponta na instância comercial

## Follow-ups

- **DR-07** — trial / pré-cadastro
- **DR-01…03** — painel de licenças
- **DR-04** — provisionamento automático

## Labels

`marketing`, `frontend`, `backend`, `ux`, `fase-interna`

## Próximo passo

→ Implementar após ou junto com LP-01 na branch `feat/landing-deskrudder`  
→ Body canônico também em `DR-06-contato-comercial-landing.md`
