# Nginx — exemplos para deploy

O **backend** já envia logs corretamente atrás de proxy (Gunicorn com `forwarded_allow_ips`). Estes ficheiros **não** são aplicados automaticamente: copie-os para o VPS e ajuste domínios e caminhos.

## DeskRudder / domínio legado

| Ficheiro | Uso |
|----------|-----|
| [`connect-duplexsoft-redirect.conf.example`](connect-duplexsoft-redirect.conf.example) | `connect.duplexsoft.com.br` → `301` `https://deskrudder.com.br$request_uri` |
| App do cliente | `https://duplexsoft.deskrudder.com.br` |
| API legada (manter) | `https://api.connect.duplexsoft.com.br` |

## Requisitos no VPS

1. Backend a escutar **só em localhost** (ex.: `127.0.0.1:8000` — padrão do `docker compose` ao mapear `8000:8000` continua acessível no host; para fechar à internet deixe o `-p` apenas se usar rede interna; o mais comum é `ports: - "127.0.0.1:8000:8000"` no compose de produção).
2. Variáveis do app: `CORS_ORIGINS` deve incluir a origem do frontend (ex.: `http://app.seudominio.com` durante testes HTTP, depois `https://...`).

## Instalação rápida (Debian/Ubuntu)

```bash
sudo apt update && sudo apt install -y nginx
sudo cp api.http.conf.example /etc/nginx/sites-available/dx-connect-api
sudo cp frontend.http.conf.example /etc/nginx/sites-available/dx-connect-app
# Editar server_name e root
sudo ln -sf /etc/nginx/sites-available/dx-connect-api /etc/nginx/sites-enabled/
sudo ln -sf /etc/nginx/sites-available/dx-connect-app /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

## Testar em HTTP

- API: `curl -sS http://api.seudominio.com/health`
- App: abrir `http://app.seudominio.com` no browser e fazer login.

Depois ative **HTTPS** (Certbot ou certificado do painel) e atualize `CORS_ORIGINS`, `VITE_API_URL` e redirecionamentos `80 → 443`.

## Um domínio só (API + SPA)

Se quiser tudo no mesmo `server_name`, pode servir o `dist/` em `/` e fazer `location /api/` com `proxy_pass` — **neste projeto** a API não usa o prefixo `/api` nas rotas, seria preciso alinhar `proxy_pass` e o `VITE_API_URL`. O arranjo mais simples é **dois nomes**: `app.` e `api.`.

## Cabeçalhos de segurança (HTTPS + SPA)

Checklist ao colocar o site em produção:

1. **TLS**: redirecionar `80 → 443`; certificados válidos (ex.: Certbot).
2. **HSTS** no `server` HTTPS: `add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;`
3. **HTML estático** (`index.html` e assets): `Content-Security-Policy` alinhada ao que o bundle carrega (scripts, estilos, `connect-src` para a URL da API); `X-Frame-Options: DENY` ou `frame-ancestors 'none'` na CSP.
4. **Complementar a API**: a aplicação FastAPI já envia `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` e `Strict-Transport-Security` quando `X-Forwarded-Proto` é `https` — o proxy deve repassar `X-Forwarded-Proto` e `X-Forwarded-For`.
5. **Login (força bruta)**: além do limite na API, pode usar `limit_req` no Nginx em `POST` para `/auth/login` (ex.: `limit_req_zone` por `$binary_remote_addr`).

Exemplo mínimo de bloco TLS + cabeçalhos no `server` do frontend (ajuste CSP ao seu build):

```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "DENY" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
```
