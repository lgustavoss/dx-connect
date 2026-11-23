# Assinatura eletrônica de contratos (#1380 / #1429)

Modelo de mercado (ClickSign/DocuSign): cada parte tem **CPF + papel + link único**. O comercial copia o link (WhatsApp) ou envia por e-mail. Não há portal «um link + digitar CPF».

## Fluxos

### A — Assinar no DeskRudder (DocuSeal multiparte)

1. Na ficha do contrato (rascunho/enviado), **Enviar para assinatura**.
2. Informe as partes:
   - **Contratante** (obrigatório) — nome, **CPF**, e-mail
   - **Contratada** (obrigatório) — nome, **CPF**, e-mail
   - **Testemunhas** (opcional, até 4) — deixe em branco para omitir
3. O backend gera/garante o PDF canônico e cria a submissão no DocuSeal com um submitter por papel (CPF pré-preenchido no campo do template).
4. A ficha mostra o status de cada parte, CPF mascarado e o **link individual**.
5. Por parte: **Copiar link** (cole no WhatsApp) ou **Enviar por e-mail**.
6. Cada signatário abre o formulário, confere o **CPF**, assina e anexa a **selfie**.
7. Enquanto faltar alguém: envelope `parcial` — o contrato **ainda não** é marcado como assinado.
8. Quando **todas** as partes concluírem, o webhook baixa PDF + trilha e executa «marcar assinado» (#1322).

### B — Assinar por fora (fallback)

1. **Anexar PDF assinado** (documento já completo fora do DeskRudder).
2. Registra envelope `provedor=externo` e badge «assinado externamente».
3. **Marcar assinado** continua disponível após o anexo.

## Variáveis de ambiente

| Variável | Uso |
|----------|-----|
| `DOCUSEAL_URL` | Base do DocuSeal self-hosted |
| `DOCUSEAL_API_TOKEN` | Token `X-Auth-Token` |
| `DOCUSEAL_WEBHOOK_SECRET` | Segredo `X-Docuseal-Secret` |
| `DOCUSEAL_TEMPLATE_ID` | ID do template na UI do DocuSeal |
| `DOCUSEAL_EXPIRACAO_DIAS` | Padrão `7` |
| `CONTRATO_ASSINATURAS_DIR` | Storage das evidências (`data/contratos`) |

Convite por e-mail usa o **e-mail transacional da instância** (Resend / `RESEND_API_KEY` + `TRANSACTIONAL_FROM_EMAIL`). Sem isso, o botão responde 503 com mensagem clara.

## Template DocuSeal

> **Checklist de go-live (obrigatório):** sem este template a criação do envelope falha ou o CPF não aparece no formulário.

Criar **uma vez** pela UI (Open Source não cria template pela API pública), com roles **exatos** (maiúscula/minúscula e acentos):

| Role | Uso |
|------|-----|
| `Contratante` | Cliente |
| `Contratada` | Sua empresa |
| `Testemunha 1` … `Testemunha N` | Opcionais (app envia até 4; crie no template pelo menos até o N que for usar) |

Em **cada** role:

- Campo `signature` obrigatório
- Campo `image` (selfie segurando o documento)
- Campo de texto com nome **exato** `CPF` (o DeskRudder pré-preenche com `fields[].name = "CPF"`)

Depois: copiar o ID do template para `DOCUSEAL_TEMPLATE_ID` e configurar o webhook `POST /v1/webhooks/docuseal` com `DOCUSEAL_WEBHOOK_SECRET`.

Operação: `SECRET_KEY_BASE` e `APP_URL` fixos; volume `/data` obrigatório. Manter `send_email=false` na API — o DeskRudder controla o convite.

## RBAC

- Enviar / reenviar / cancelar / e-mail de convite: `contratos.emitir`
- Ver evidências: `contratos.ver`; download gera `AuditLog` `action=download`
- Webhook: público, autenticado pelo segredo

## Endpoints

- `POST /v1/comercial/contratos/{id}/assinatura/enviar` — `{ signatarios: [{ papel, nome, email, cpf, telefone? }], forcar_reenvio? }`
- `POST /v1/comercial/contratos/{id}/assinatura/cancelar`
- `POST /v1/comercial/contratos/{id}/assinatura/partes/{parte_id}/enviar-email`
- `GET /v1/comercial/contratos/{id}/assinatura` — `partes[]` com `cpf_mascarado`
- `GET /v1/comercial/contratos/{id}/assinatura/evidencias/{pdf|audit|selfie}`
- `POST /v1/webhooks/docuseal`

## Retenção

Evidências vivem enquanto o PDF assinado existir. Regenerar/descartar o PDF cancela envelopes ativos e apaga arquivos em `CONTRATO_ASSINATURAS_DIR`.
