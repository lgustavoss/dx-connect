# Cliente Windows DeskRudder (acesso remoto)

**O que o usuário final recebe:** um único arquivo  
`DeskRudder-AcessoRemoto-<versão>.exe`  
Já tem a marca DeskRudder e o servidor da Duplex (`31.97.160.79` + chave).  
Não precisa de colar string nem de rodar comandos.

## Como obter o `.exe` (equipe)

1. O workflow precisa estar na branch padrão (`main`) — após o merge deste PR, ele aparece em Actions.
2. No GitHub: **Actions** → workflow **«RustDesk DeskRudder Windows»**
3. **Run workflow** — deixe a tag **`1.5.0`** (não existe `1.5.1` no upstream; tag inválida falha no checkout)
4. Esperar o job (~40–90 min na 1.ª vez)
5. Em **Artifacts**, baixar `DeskRudder-AcessoRemoto-windows` (ou usar o Release abaixo)
6. O workflow também publica (ou atualiza) o Release **`acesso-remoto-windows`** com o arquivo estável `DeskRudder-AcessoRemoto.exe`
7. No painel, a tela **Acesso remoto** tem o botão **Baixar instalador Windows** apontando para esse Release

URL estável (pública):

`https://github.com/lgustavoss/dx-connect/releases/download/acesso-remoto-windows/DeskRudder-AcessoRemoto.exe`

Workflow: `.github/workflows/rustdesk-deskrudder-windows.yml`

## Servidor embutido

| Campo | Valor |
|-------|--------|
| ID Server / Relay | `31.97.160.79` |
| Key (pública) | `kEoYK77jUT92KWnj1XmqYRgIRKv4VkGNMjFjm33HtjI=` |

Fonte: `deploy/rustdesk-client/server.config.json`

## O que o CI faz

1. Clona [rustdesk/rustdesk](https://github.com/rustdesk/rustdesk) (tag escolhida)
2. Aplica `deploy/rustdesk-client/scripts/apply_branding.py` (nome DeskRudder, host/chave em `RENDEZVOUS_SERVERS` + `PROD_RENDEZVOUS_SERVER`, ícones e PNG do Sciter em `get_icon()`)
3. Compila o cliente Windows (UI Sciter), renomeia o binário para `DeskRudder.exe` (necessário para o Windows reconhecer a instalação) e empacota o portable
4. Publica o artefato `DeskRudder-AcessoRemoto-*.exe` e atualiza o Release `acesso-remoto-windows` (link do painel)

## Pasta no repo

| Caminho | Função |
|---------|--------|
| `deploy/rustdesk-client/server.config.json` | Host e chave |
| `deploy/rustdesk-client/branding/` | Arte oficial + `icon.ico`/tray/PNGs — regenerar com `scripts/render_remote_icons.py` |
| `deploy/rustdesk-client/scripts/apply_branding.py` | Patch no clone |
| `deploy/rustdesk-client/scripts/encode_config.py` | Gera/decodifica string de import (debug) |
| `.github/workflows/rustdesk-deskrudder-windows.yml` | Build do `.exe` |

## Licença

RustDesk é **AGPL-3.0**. Ao distribuir o binário modificado, mantenham o código/diff disponível (este repo + tag do upstream já documentam o processo).

## Atualizar um PC que já instalou a versão antiga

Builds antigos gravavam `rustdesk.exe` em `Program Files (x86)\DeskRudder` e o app continuava pedindo instalação. Nesse caso:

1. Desinstalar pelo atalho **Uninstall DeskRudder** (ou Apps e recursos)
2. Apagar a pasta `C:\Program Files (x86)\DeskRudder` se sobrar
3. Baixar o artefato novo do Actions e instalar de novo — a pasta deve ter `DeskRudder.exe`

## Fora do v1

- macOS / Linux / Android  
- Assinatura Authenticode (pode entrar depois)  
- UI Flutter moderna (o CI atual usa o build Sciter x86, estável no Actions)  
- Hospedar o `.exe` fora do GitHub (CDN próprio), se o Release deixar de bastar

## Referências

- [Client configuration](https://rustdesk.com/docs/en/self-host/client-configuration/)  
- [Build Windows](https://rustdesk.com/docs/en/dev/build/windows/)  
- Frota no painel: issue `#1184` / tela Acesso remoto  
