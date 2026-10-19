# Cliente acesso remoto DeskRudder (Windows)

Spike do instalador personalizado (marca DeskRudder + servidor Duplex).

| Pasta / ficheiro | Função |
|------------------|--------|
| `server.config.json` | Host, relay e chave pública |
| `config.env.example` | Variáveis para build |
| `branding/` | `icon.ico` e PNGs DeskRudder |
| `scripts/encode_config.py` | Gera/decodifica a string `--config` |
| `scripts/apply_branding.sh` | Aplica marca + servidor num clone do rustdesk |
| `windows/Install-DeskRudderRemote.ps1` | Fase 0: oficial + config |

Documentação: [`docs/RUSTDESK_CLIENT_WINDOWS.md`](../../docs/RUSTDESK_CLIENT_WINDOWS.md).
