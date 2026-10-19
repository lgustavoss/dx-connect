# Cliente Windows DeskRudder (acesso remoto)

**O que o utilizador final recebe:** um único ficheiro  
`DeskRudder-AcessoRemoto-<versão>.exe`  
Já tem a marca DeskRudder e o servidor da Duplex (`31.97.160.79` + chave).  
Não precisa de colar string nem de correr comandos.

## Como obter o `.exe` (equipa)

1. No GitHub: **Actions** → workflow **«RustDesk DeskRudder Windows»**
2. **Run workflow** (tag padrão `1.5.0`)
3. Esperar o job (~40–90 min na 1.ª vez)
4. Em **Artifacts**, descarregar `DeskRudder-AcessoRemoto-windows`
5. Distribuir o `.exe` aos PCs dos clientes

Workflow: `.github/workflows/rustdesk-deskrudder-windows.yml`

## Servidor embutido

| Campo | Valor |
|-------|--------|
| ID Server / Relay | `31.97.160.79` |
| Key (pública) | `kEoYK77jUT92KWnj1XmqYRgIRKv4VkGNMjFjm33HtjI=` |

Fonte: `deploy/rustdesk-client/server.config.json`

## O que o CI faz

1. Clona [rustdesk/rustdesk](https://github.com/rustdesk/rustdesk) (tag escolhida)
2. Aplica `deploy/rustdesk-client/scripts/apply_branding.py` (nome DeskRudder, ícones, host/chave)
3. Compila o cliente Windows (UI Sciter + instalador portable)
4. Publica o artefacto `DeskRudder-AcessoRemoto-*.exe`

## Pasta no repo

| Caminho | Função |
|---------|--------|
| `deploy/rustdesk-client/server.config.json` | Host e chave |
| `deploy/rustdesk-client/branding/` | `icon.ico` e PNGs |
| `deploy/rustdesk-client/scripts/apply_branding.py` | Patch no clone |
| `deploy/rustdesk-client/scripts/encode_config.py` | Gera/decodifica string de import (debug) |
| `.github/workflows/rustdesk-deskrudder-windows.yml` | Build do `.exe` |

## Licença

RustDesk é **AGPL-3.0**. Ao distribuir o binário modificado, mantenham o código/diff disponível (este repo + tag do upstream já documentam o processo).

## Fora do v1

- macOS / Linux / Android  
- Assinatura Authenticode (pode entrar depois)  
- UI Flutter moderna (o CI atual usa o build Sciter, estável no Actions)  
- Publicar automaticamente no painel SaaS  

## Referências

- [Client configuration](https://rustdesk.com/docs/en/self-host/client-configuration/)  
- [Build Windows](https://rustdesk.com/docs/en/dev/build/windows/)  
- Frota no painel: issue `#1184` / tela Acesso remoto  
