# Cliente Windows DeskRudder (acesso remoto)

Há **dois perfis** de build (mesmo workflow, input `profile`):

| Perfil | Artefato | Release GitHub | Uso |
|--------|----------|----------------|-----|
| **posto** (padrão) | `DeskRudder-AcessoRemoto-*.exe` | `acesso-remoto-windows` | PC do posto — **só recebe** conexão; vínculo a PDV no painel |
| **controle** | `DeskRudder-AcessoRemoto-Controle-*.exe` | `acesso-remoto-controle-windows` | PC do **atendente** — inicia sessão a partir da frota; embutido no Setup Electron |

**Posto — o que o usuário final recebe:** um único arquivo  
`DeskRudder-AcessoRemoto-<versão-DeskRudder>.exe`  
Já tem a marca DeskRudder e o servidor da Duplex (`31.97.160.79` + chave).  
Não precisa de colar string nem de rodar comandos.

O perfil **controle** usa o **mesmo** `branding/` e servidor, **sem** forçar `incoming_only` (UI completa do RustDesk + canal de update próprio). Fluxo oficial do atendente: frota do painel → um clique (senha do cadastro). Máquinas fora do servidor DeskRudder: RustDesk padrão.

Ao trocar a arte em `deploy/rustdesk-client/branding/`: regenere os ICO/PNG, suba `CLIENT_VERSION` e rode o workflow **duas vezes** (`posto` e `controle`) para os dois Releases receberem a mesma marca.

## Versão (importante)

Há **duas** versões envolvidas:

| O quê | Onde | Muda quando |
|-------|------|-------------|
| **Versão DeskRudder** (`CLIENT_VERSION`, ex.: `1.0.0`) | Aparece no app, na instalação e no aviso de update | A equipe sobe o número em `deploy/rustdesk-client/CLIENT_VERSION` e gera um build novo |
| **Tag RustDesk** (ex.: `1.5.0`) | Base do código open-source no workflow | Só quando escolhemos uma tag mais nova do upstream no Actions |

A tag `1.5.0` **não sobe sozinha** a cada build — é a base do RustDesk. O que o posto precisa olhar é a **versão DeskRudder**.

Canal de atualização: o Release publica `version.json`; o cliente compara e mostra o banner **Atualização disponível**.

Ao clicar em **Atualizar agora**:

1. Baixa o `.exe` estável para a pasta temporária  
2. Pede elevação (UAC) e roda com `--update`  
3. Substitui os arquivos em `DeskRudder\Acesso Remoto` e **reabre** o app (e a bandeja)

## Como obter o `.exe` (equipe)

1. O workflow precisa estar na branch padrão (`main`) — após o merge deste PR, ele aparece em Actions.
2. No GitHub: **Actions** → workflow **«RustDesk DeskRudder Windows»**
3. **Run workflow** — tag **`1.5.0`** e **profile** `posto` ou `controle`
4. Esperar o job (~40–90 min na 1.ª vez)
5. Em **Artifacts**, baixar `DeskRudder-AcessoRemoto-posto-windows` ou `…-controle-windows`
6. O workflow publica o Release correspondente (`acesso-remoto-windows` ou `acesso-remoto-controle-windows`) com o `.exe` estável + `version.json`
7. **Posto:** no painel, tela **Acesso remoto** → **Baixar instalador Windows** / link curto. **Controle:** embutir no Setup do atendente (`desktop/scripts/baixar-remoto-controle.ps1`) — ver [`DESKTOP_ELECTRON.md`](DESKTOP_ELECTRON.md)

URL curta na instância (sem login — Nginx redireciona; o SPA também cobre se o Nginx ainda não tiver a regra):

`https://{cliente}.deskrudder.com.br/acesso-remoto/download`

Exemplo Duplex: `https://duplexsoft.deskrudder.com.br/acesso-remoto/download`

URL do arquivo no GitHub (destino do redirect):

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
2. Aplica `deploy/rustdesk-client/scripts/apply_branding.py` (nome DeskRudder, host/chave em `RENDEZVOUS_SERVERS` + `PROD_RENDEZVOUS_SERVER`, ícones e PNG do Sciter em `get_icon()`, modo só-recebe, UI com logo e atalho **DeskRudder - Acesso Remoto**)
3. Compila o cliente Windows (UI Sciter), renomeia o binário para `DeskRudder.exe` (necessário para o Windows reconhecer a instalação) e empacota o portable
4. Publica o artefato `DeskRudder-AcessoRemoto-*.exe` e atualiza o Release `acesso-remoto-windows` (link do painel)

## Comportamento do cliente (postos)

O instalador é pensado para o PC que **vai ser acessado** (PDV / posto):

- Painel esquerdo com ID e senha; barra inferior de status (ex.: Pronto)
- Painel direito só com a logo DeskRudder (sem «Controle um computador remoto»)
- Conexões de saída bloqueadas (`is_incoming_only`)
- Atalho na Área de Trabalho / menu Iniciar: **DeskRudder - Acesso Remoto** (o `.exe` instalado continua `DeskRudder.exe`)
- Pasta de instalação: `C:\Program Files (x86)\DeskRudder\Acesso Remoto` (outros apps DeskRudder podem ficar em pastas irmãs)
- Link «Desenvolvido por DeskRudder» → https://deskrudder.com.br/
- Tema escuro segue o Windows (conteúdo + barra de título) se a opção não foi fixada no menu (⋮ → Tema escuro)
- Logo do painel usa arte em alta resolução (`ui-logo-512.png`)

### Senha (uso único × permanente)

Por padrão o app usa **senha de uso único** (muda se alguém clicar no ícone de atualizar). **Não há senha permanente pré-configurada.**

Para acesso estável no posto:

1. Clique no lápis ao lado da senha
2. **Definir senha permanente** e escolha uma senha da equipe
3. Em **Usar senha permanente** (ou «ambas»), o refresh da senha de uso único deixa de impedir o acesso

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
