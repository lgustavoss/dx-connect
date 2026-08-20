# App Android (Capacitor) — L6.1 / L6.2 / L6.3 (#735 / #736 / #737)

O APK é um WebView Capacitor com um **SPA mais leve**: login, **tickets** e **chat** (mesa WhatsApp / hub). Não leva landing, SaaS, CRM, cadastros nem dashboards.

**Não há base de dados no telemóvel.** Os dados são os da **instância da empresa** (mesmo Postgres da API). Um binário serve várias empresas via campo **Conta**.

## Conta da empresa (slug)

No primeiro login o atendente informa o identificador da empresa (o mesmo do endereço do painel), por exemplo `duplexsoft` → `https://duplexsoft.deskrudder.com.br`.

O app grava essa conta no aparelho e passa a chamar:

```text
https://api-{slug}.deskrudder.com.br
```

Nas vezes seguintes o ecrã de login já mostra essa empresa (e-mail/senha apenas). **Trocar** limpa a conta gravada **e os tokens** da sessão anterior (evita pedidos à API sem alvo ou à instância errada).

O login **só mantém** o slug no aparelho se a autenticação for bem-sucedida; se falhar (conta/senha errada), a conta anterior (se houver) é restaurada.

O Android usa **Capacitor HTTP** (pedido nativo), para o login não depender do CORS do browser. Mesmo assim, cada instância deve incluir `https://localhost` em `CORS_ORIGINS` (SSE e ferramentas web).

## Pré-requisitos

| Ferramenta | Notas |
|------------|--------|
| Node.js (mesmo do `frontend`) | `npm ci` na pasta `frontend/` |
| JDK 21 | Temporaries do Gradle / Android |
| Android Studio (Ladybug+) | SDK, emulador ou cabo USB com depuração |
| Variável `ANDROID_HOME` | Pasta do SDK (o Studio costuma definir) |

Não é preciso conta Google Play neste lote.

## O que está no repo

- `frontend/capacitor.config.ts` — `appId` `br.com.deskrudder.app`, `webDir` `dist`
- `frontend/android/` — projecto Gradle gerado pelo Capacitor
- `frontend/scripts/build-android.mjs` — `vite build` **sem** service worker PWA + `cap sync` (entrada `AppNative.tsx`)

O `npm run build` da CI **não** muda: continua a ser o PWA web completo. O APK usa `VITE_CAPACITOR=true`.

## Primeiro build debug

Na pasta `frontend/`:

```bash
npm ci
npm run build:android
npm run cap:open
```

Sem `VITE_API_URL`, o APK pede a conta no login (produção / várias empresas). **Builds de loja não devem definir `VITE_API_URL`** — senão o ecrã Conta é ignorado e todos os pedidos vão para essa URL fixa de debug.

API **local** (mesmo Postgres do `docker compose` / painel no browser), só em builds de desenvolvimento:

```bash
# Emulador
$env:VITE_API_URL = "http://10.0.2.2:8000"
# Telemóvel na mesma Wi-Fi (IP do PC, não 127.0.0.1)
$env:VITE_API_URL = "http://192.168.x.x:8000"
npm run build:android
```

Com `VITE_API_URL` definido, essa base **tem prioridade** sobre o slug (útil no emulador). Sem essa variável, o slug escolhe `https://api-{slug}.…`.

O `Host` da API no telemóvel, no modo local, é o IP do PC; o WebView continua origem `https://localhost`. Firewall do Windows tem de deixar TCP 8000 na LAN. HTTP claro no emulador: o manifesto debug do Capacitor já permite cleartext.

## Comandos

| Script | Função |
|--------|--------|
| `npm run build:android` | Dist nativo + `cap sync android` |
| `npm run cap:sync` | Só copia `dist` para o projecto nativo |
| `npm run cap:open` | Abre o Android Studio |

## Fora deste lote

- iOS (#738)
- Listing nas lojas (#739)

## Alertas com a app fechada (UnifiedPush / VAPID) — #737

Não há projecto Firebase nem `google-services.json`. O APK pede um endpoint **Web Push** (UnifiedPush) e grava-o na API da instância (`POST /v1/web-push/subscriptions`), com as mesmas chaves VAPID do `client.env`.

O worker `web-push-outbox` já existente envia para PWA **e** APK. Mute da fila e deep link são os da PWA.

O distribuidor embutido usa os servidores de push da Google só como transporte nos telemóveis com Play Services. Sem Play Services, o alerta com a app fechada não chega (a PWA no Chrome continua a funcionar).

Ícones/splash oficiais: usar os PNG em `frontend/public/deskrudder-pwa-*.png` num lote posterior (`@capacitor/assets`).

No Windows, se a pasta do clone tiver acentos (ex. `Repositórios`), o Gradle precisa de `android.overridePathCheck=true` em `frontend/android/gradle.properties` (já no repo).
