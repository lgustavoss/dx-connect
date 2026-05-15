# Configurações de e-mail e empresa do sistema (API v1)

Este documento descreve os endpoints do backend para:

- **Empresa do sistema** (singleton)
- **Configurações de e-mail** (SMTP/IMAP) com **teste de conexão** — *modo atual (credenciais na caixa)*

> Escopo técnico imediato: armazenar e testar SMTP/IMAP. A **integração completa ticketing ↔ correio** (abrir ticket, thread, respostas) será alinhada ao padrão de mercado descrito abaixo.

---

## Direção de desenvolvimento (padrão de mercado)

O modelo **mais usado** por produtos como Zendesk, Freshdesk, octadesk, sistemas próximos de «helpdesk SaaS», etc., **não** centra o onboarding em pedir ao cliente as credenciais IMAP/SMTP da caixa corporativa.

**Alvo DX Connect:**

| Aspecto | Padrão preferido |
|--------|-------------------|
| **Recepção** | Endereço de suporte sob controle da aplicação (subdomínio ou domínio do cliente verificado); **MX** apontados para infraestrutura de ingestão **ou** regra de **encaminhamento** do cliente para esse endereço; conversão MIME → POST interno (**inbound parse** / pipeline próprio). |
| **Credenciais** | O cliente **não** parte do princípio de guardar senha IMAP na nossa UI; uso de **credenciais do produto** + DNS quando for domínio próprio. |
| **Envio** | Correio sai pelos **relays/API do próprio produto**, com **SPF/DKIM/DMARC** configurados pelo cliente no domínio (ou marca compartilhada inicial). SMTP «BYO» (bring your own) pode existir como **opção**, não como caminho único. |
| **Thread / mesmo ticket** | Persistir **`Message-ID`**, **`In-Reply-To`**, **`References`** (e onde existir **`conversationId`**) para associar réplicas ao ticket certo e abrir **novo** ticket apenas quando não houver encadeamento válido (regra de negócio do produto). |
| **Microsoft / Google** | Conectores **OAuth** (Microsoft Graph / Gmail API) como **camada opcional**, útil onde o cliente exige ler a mailbox Office/Google sem encaminhar; não substituem por si só o modelo de ingestão própria. |

**Estado atual do repositório:** o painel admin e o `PUT /v1/settings/email` implementam apenas o caminho **genérico SMTP/IMAP + senha**. Esse modo serve como:

- compatibilidade com **provedores pequenos** que ainda suportam bem IMAP/SMTP basic auth;
- **prova de conceito** de envio/recepção até existir ingestão própria e webhooks.

**Próximo trabalho recomendado (issue):** evoluir ingestão (**thread / mesmo ticket**, UI de onboarding, envio outbound no fio) — ver épico [#162](https://github.com/lgustavoss/dx-connect/issues/162).

### Webhook de ingestão → ticket (v1 implementado)

`POST /v1/webhooks/email-inbound` — **não** usa JWT; autenticação por segredo em cabeçalho.

| Requisito | Variável / detalhe |
|-----------|-------------------|
| Segredo | `EMAIL_INBOUND_WEBHOOK_SECRET` — enviar cabeçalho **`X-Dx-Email-Webhook-Secret`** com o mesmo valor. Se não estiver definido → **503**. |
| Empresa / setor do ticket | `EMAIL_INBOUND_DEFAULT_EMPRESA_ID` e `EMAIL_INBOUND_DEFAULT_SETOR_ID` (v1 por ambiente; evoluir para persistência/UI). Se faltar algum → **503**. |
| Idempotência | Cabeçalho **`Message-ID`** na mensagem MIME ou no campo `headers` (formato SendGrid). Reenvio com o mesmo ID devolve **200** com `"duplicate": true`. |
| Corpo | JSON `{"rfc822": "..."}` (MIME completo) **ou** formulário `from`, `subject`, `text`/`html`, `headers`, opcionalmente `email` (RFC822). |

Resposta: `ticket_id`, `protocolo`, `duplicate`, `threaded` (`true` quando a mensagem foi anexada a um ticket **ainda aberto** via `In-Reply-To` / `References`), `after_close_new_ticket` (`true` quando a thread apontava para um ticket **já encerrado** — abre-se um **novo ticket de triagem** em vez de reabrir a conversa no fechado), `auto_reply_sent` (`true` quando foi enviado o e-mail automático ao cliente a explicar o encerramento; depende de SMTP configurado).

---

## Acesso

A maior parte dos endpoints abaixo é **admin-only** (JWT) com prefixo `/v1`. O webhook de ingestão de e-mail é **exceção** (ver tabela acima).

## Empresa do sistema (singleton)

### `GET /v1/settings/empresa-sistema`

Retorna a empresa do sistema (se não existir ainda, retorna tudo `null`/defaults).

### `PUT /v1/settings/empresa-sistema`

Atualiza/cria a empresa do sistema.

Campos de endereço (como no cadastro de empresa cliente): `endereco` (logradouro), `numero`, `complemento`, `bairro`, `cidade`, `estado` (UF, 2 letras), `cep` (apenas dígitos ou com máscara — o backend normaliza).

#### Regra importante

- **`cnpj` é imutável** após o primeiro save (se já houver `cnpj` gravado, tentar alterar retorna **400**).

## E-mail (SMTP/IMAP) — modo credenciais na caixa

⚠ Este bloco reflete a API **existente**. Não reflete o desenho de destino único para ticketing; ver seção «Direção de desenvolvimento» acima.

### `GET /v1/settings/email`

Devolve a configuração atual **sem expor segredos**.

Campos de password nunca são devolvidos; em vez disso, o backend retorna flags:

- `has_smtp_password`
- `has_imap_password`

### `PUT /v1/settings/email`

Atualiza/cria a configuração de e-mail.

#### Atualização de segredos

- Se `smtp_password`/`imap_password` **não forem enviados**: mantém o valor atual.
- Se forem enviados como **string vazia**: limpa o segredo.
- Se forem enviados com texto: o backend **cifra e guarda** (não devolve no GET).

O frontend unificou um único par **e-mail / senha da conta** ao gravar, preenchendo `smtp_*` e `imap_*` de forma consistente; o servidor pode alinhar senhas SMTP/IMAP quando o utilizador é o mesmo (ver código em `system_settings.py`).

### `POST /v1/settings/email/test-smtp`

Testa a conexão SMTP com os dados gravados.

### `POST /v1/settings/email/test-imap`

Testa a conexão IMAP com os dados gravados (faz login e `select` na pasta `imap_folder`, default `INBOX`).

**Microsoft 365:** o teste SMTP pode passar e o IMAP falhar («LOGIN failed») quando políticas de tenant bloqueiam autenticação básica no IMAP mesmo com SMTP autenticado permitido — cenário esperado até haver ingestão por Graph/webhook.

---

## Presets Gmail e Microsoft 365 (frontend)

No painel **Configurações → Empresa & e-mail → aba E-mail**, o utilizador pode escolher um **provedor** para preencher automaticamente **hosts, portas, STARTTLS/SSL e pasta IMAP** nos campos do formulário. Os valores são aplicados **só no browser**; o backend continua a receber um `PUT /v1/settings/email` genérico (os mesmos campos de sempre).

| Provedor | SMTP (host / porta / STARTTLS) | IMAP (host / porta / SSL) | Pasta |
|----------|-------------------------------|----------------------------|--------|
| **Google Gmail** | `smtp.gmail.com` / `587` / sim | `imap.gmail.com` / `993` / sim | `INBOX` |
| **Microsoft 365** (trabalho ou escola) | `smtp.office365.com` / `587` / sim | `outlook.office365.com` / `993` / sim | `INBOX` |

Contas **pessoais** `@outlook.com` / `@hotmail.com` costumam usar `smtp-mail.outlook.com` e `imap-mail.outlook.com`; o painel mostra uma nota quando o preset Microsoft está selecionado.

**Autenticação:** Gmail e Microsoft costumam exigir **senha de aplicação** ou políticas definidas pelo administrador — nem sempre basta a senha do site se houver MFA. O painel recolhe **e-mail da conta** e **senha da conta** aplicados ao SMTP e IMAP ao gravar.

---

## «Login social» (OAuth2) e Graph / Gmail API

Fluxo «Entrar com Google / Microsoft» para **substituir** SMTP/IMAP manual baseia-se em **OAuth 2.0**: registo da app no [Google Cloud Console](https://console.cloud.google.com/) ou [Microsoft Entra ID](https://portal.azure.com/), armazenamento cifrado de refresh token, e uso de **Microsoft Graph** / **Gmail API** para envio e sincronização de mensagens (em vez de IMAP com senha quando o tenant o bloqueia).

Este conector faz parte do **conjunto opcional para grandes SaaS**, em paralelo ao padrão **ingestão própria + encaminhamento** descrito na seção de direção.

---

## Deteção automática do preset no painel

Ao carregar a configuração, o frontend tenta classificar o provedor se os hosts coincidirem com Gmail ou Microsoft 365 (ou hosts consumer Outlook no código). Se o administrador alterar manualmente os campos de servidor SMTP ou IMAP, o seletor volta para **Personalizado**.

---

## Rastreamento (GitHub)

Épico de desenvolvimento alinhado à secção «Direção de desenvolvimento»: [E-mail → tickets (padrão SaaS)](https://github.com/lgustavoss/dx-connect/issues/162) (issues filhas [#163](https://github.com/lgustavoss/dx-connect/issues/163)–[#167](https://github.com/lgustavoss/dx-connect/issues/167)).

Meta-issue relacionada: [#16 — melhorias operacionais](https://github.com/lgustavoss/dx-connect/issues/16). Ingestão **IMAP legado / BYO** em [#20](https://github.com/lgustavoss/dx-connect/issues/20).

Rascunhos de texto usados na criação destas issues: pasta [`.github/planning-issue-bodies/`](https://github.com/lgustavoss/dx-connect/tree/main/.github/planning-issue-bodies).
