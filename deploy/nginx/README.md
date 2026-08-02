# Nginx — exemplos para deploy

O **backend** já envia logs corretamente atrás de proxy (Gunicorn com `forwarded_allow_ips`). Estes ficheiros **não** são aplicados automaticamente: copie-os para o VPS e ajuste domínios e caminhos.

## DeskRudder — hosts

| Host | Função |
|------|--------|
| `deskrudder.com.br` | Landing / site comercial |
| `{slug}.deskrudder.com.br` | Painel do cliente (ex.: `duplexsoft.deskrudder.com.br`) |
| `api-{slug}.deskrudder.com.br` | API do cliente (ex.: `api-duplexsoft.deskrudder.com.br`) |

Exemplos: [`deskrudder-landing.conf.example`](deskrudder-landing.conf.example), [`deskrudder-duplexsoft.conf.example`](deskrudder-duplexsoft.conf.example) (se presentes), template em [`../clients/_template/nginx.site.conf.example`](../clients/_template/nginx.site.conf.example).

### Domínios legados (`*.duplexsoft.com.br`)

[`connect-duplexsoft-redirect.conf.example`](connect-duplexsoft-redirect.conf.example) — `301` de `connect.` / `api.connect.` para os hosts DeskRudder do cliente piloto.

## Requisitos no VPS
