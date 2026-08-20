# Publicação nas lojas — DeskRudder (#739)

Runbook para **listing mínimo** e release do app Capacitor. O binário Android já está na `main` (L6.1–L6.3). Este documento fecha o aceite de código/docs do **#739**; o upload na Console depende das contas developer (Luis).

**Não** exige PWA global `app.` — um APK/AAB + campo Conta → `api-{slug}`.

| Canal | Estado |
|-------|--------|
| Play Store (Android) | Pronto para listing + AAB em teste interno (conta Google Play) |
| App Store (iOS) | Bloqueado por **#738** (Mac + Apple Developer) — secção stub abaixo |

Build técnico do APK/AAB: [`docs/MOBILE_CAPACITOR.md`](MOBILE_CAPACITOR.md).

---

## Identidade do app

| Campo | Valor |
|-------|--------|
| Nome | DeskRudder |
| Nome curto (≤12) | DeskRudder |
| `applicationId` / package | `br.com.deskrudder.app` |
| Categoria Play | Produtividade / Empresas |
| Contacto | `contato@deskrudder.com.br` |
| Política de privacidade (URL pública) | `https://deskrudder.com.br/privacidade` |
| Ícone loja | `frontend/public/deskrudder-pwa-512.png` (fundo Deck) + outline `deskrudder-pwa-512-outline.png` |
| Feature graphic (1024×500) | Gerar a partir do mark + wordmark (`BRAND.md`); não versionar binário grande no git até existir arte final |

Tagline: **O leme da sua operação de atendimento**.

---

## Textos Play Console (copiar/colar)

### Descrição curta (≤80 caracteres)

```text
Atendimento WhatsApp e tickets no telemóvel — conta da sua empresa.
```

### Descrição completa

```text
O DeskRudder no telemóvel para atendentes: fila WhatsApp, chats em curso e tickets da sua empresa — com os mesmos dados do painel web.

• Conta da empresa: no primeiro login indica o identificador (ex. duplexsoft); nas seguintes o app já aponta para a API certa.
• Operação: assumir fila, responder (texto e mídia), transferir, encerrar e abrir tickets.
• Alertas com a app fechada: fila e mensagens dos atendimentos já teus (quando a instância tiver Web Push/VAPID configurado).
• Um único app para várias empresas clientes DeskRudder — sem base de dados local no telemóvel.

Requer ligação à internet e uma conta DeskRudder activa na instância da sua empresa.
```

### O que há de novo (modelo por release)

```text
Melhorias de estabilidade e alinhamento com o painel web. Actualize para manter alertas e login por conta da empresa.
```

(Preencher com bullets reais do `CHANGELOG.md` → `[Unreleased]` / CalVer no dia do upload.)

### Classificação de conteúdo / dados

- Público-alvo: **atendentes internos** (não consumidores finais do posto).
- Dados: autenticação, chats/tickets da **instância** do cliente; sem anúncios; sem venda de dados.
- Permissões típicas Android: Internet; notificações; microfone/câmara/ficheiros só para anexos WhatsApp (conforme uso).

---

## Checklist — Play (teste interno / fechado)

1. [ ] Conta Google Play Console activa (Luis).
2. [ ] Criar app `DeskRudder` / package `br.com.deskrudder.app`.
3. [ ] Preencher listing (nome, descrições acima, ícone 512, feature graphic).
4. [ ] URL de privacidade: `https://deskrudder.com.br/privacidade` (página no repo; deploy na apex).
5. [ ] Gerar **AAB** assinado — ver `MOBILE_CAPACITOR.md` → «Gerar APK / AAB».
6. [ ] Bump `versionCode` / `versionName` em `frontend/android/app/build.gradle` **antes** de cada upload.
7. [ ] Upload na track **Internal testing** (ou Closed); adicionar e-mails dos testers.
8. [ ] Smoke no dispositivo: checklist 11 itens em `MOBILE_CAPACITOR.md`.
9. [ ] Confirmar push (VAPID na instância + UnifiedPush) com app fechada.

Keystore e `google-services.json` (se algum dia necessário) **fora do git**.

---

## Versão Android (convenção)

| Campo | Onde | Regra |
|-------|------|--------|
| `versionCode` | `app/build.gradle` | Inteiro monotónico (+1 por upload Play) |
| `versionName` | idem | Semântico curto alinhado ao produto (ex. `1.0.0`, `1.0.1`) — independente do CalVer do painel web |

Nunca publicar com `VITE_API_URL` definido no build de loja.

---

## App Store / TestFlight (#738)

Quando existir Mac + Apple Developer:

1. `npx cap add ios` / `cap sync ios` (issue #738).
2. Bundle ID alinhado a `br.com.deskrudder.app` (ou variante registada na Apple).
3. Listing: reutilizar textos PT-BR desta página; screenshots iPhone.
4. Privacidade: mesma URL `https://deskrudder.com.br/privacidade`.
5. TestFlight interno antes de App Review.

Até lá, o épico Mobile (#689 / #696) considera **Android + docs de loja** como L6 entregue no código; iOS permanece follow-up explícito.

---

## Relação com o épico

| Issue | Entrega |
|-------|---------|
| #735 / #736 | Shell Android + Conta |
| #737 | Push UnifiedPush/VAPID |
| #739 | Este doc + URL de privacidade + textos listing |
| #738 | iOS + APNs (fora deste lote) |
