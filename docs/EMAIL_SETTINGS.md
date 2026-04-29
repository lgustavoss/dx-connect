# Configurações de e-mail e empresa do sistema (API v1)

Este documento descreve os endpoints do backend para:

- **Empresa do sistema** (singleton)
- **Configurações de e-mail** (SMTP/IMAP) com **teste de conexão**

> Escopo: base para integrações por e-mail (ex.: criação de ticket por caixa, envio de notificações).

## Acesso

Todos os endpoints abaixo são **admin-only** (JWT) e usam o prefixo ` /v1`.

## Empresa do sistema (singleton)

### `GET /v1/settings/empresa-sistema`

Retorna a empresa do sistema (se não existir ainda, retorna tudo `null`/defaults).

### `PUT /v1/settings/empresa-sistema`

Atualiza/cria a empresa do sistema.

#### Regra importante

- **`cnpj` é imutável** após o primeiro save (se já houver `cnpj` gravado, tentar alterar retorna **400**).

## E-mail (SMTP/IMAP)

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

### `POST /v1/settings/email/test-smtp`

Testa a conexão SMTP com os dados gravados.

### `POST /v1/settings/email/test-imap`

Testa a conexão IMAP com os dados gravados (faz login e `select` na pasta `imap_folder`, default `INBOX`).

