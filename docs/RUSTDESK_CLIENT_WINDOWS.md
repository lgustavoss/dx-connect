# Cliente Windows DeskRudder (acesso remoto)

Há **quatro workflows** no Actions (nomes na UI):

| Workflow | Artefato | Release | Uso |
|----------|----------|---------|-----|
| **Acesso Remoto Cliente (Windows)** | `DeskRudder-AcessoRemoto.exe` | `acesso-remoto-windows` | PC do **posto** — só recebe |
| **Acesso Remoto Atendente (Windows)** | `DeskRudder-AcessoRemoto-Controle.exe` | `acesso-remoto-controle-windows` | Remoto do **atendente** (frota) |
| **App Atendente Setup (Windows)** | `DeskRudder-Setup.exe` | `desktop-windows` | Painel + embute o remoto atendente já publicado |
| **Acesso Remoto Atendente Flutter (spike)** | `DeskRudder-AcessoRemoto-Controle-Flutter.exe` | `acesso-remoto-controle-flutter-windows` | UI Flutter x64 do atendente — **não** substitui o Sciter |

Assim o Setup do painel fica rápido; o build longo do RustDesk só roda quando o remoto muda.

**Cliente — o que o posto recebe:**  
`DeskRudder-AcessoRemoto-<versão>.exe` com marca DeskRudder e servidor Duplex (`31.97.160.79` + chave).

Cliente e atendente usam o **mesmo** `deploy/rustdesk-client/branding/` (e `kit-1253/` para Flutter). Ao trocar a arte: regenere com `render_remote_icons.py`, suba a versão do canal (`CLIENT_VERSION` no Sciter, `CLIENT_VERSION_FLUTTER` no Flutter) e rode os workflows de remoto.

## Versão (importante)

Há **três** números envolvidos:

| O quê | Onde | Muda quando |
|-------|------|-------------|
| **Sciter (produção)** (`CLIENT_VERSION`, linha **1.x.x**, ex.: `1.0.14`) | UI, instalação e update dos Releases `acesso-remoto-windows` e `acesso-remoto-controle-windows` | A equipe sobe o número em `deploy/rustdesk-client/CLIENT_VERSION` e gera o build Sciter |
| **Flutter (spike atendente)** (`CLIENT_VERSION_FLUTTER`, linha **2.x.x**, ex.: `2.0.1`) | UI Flutter e update do Release `acesso-remoto-controle-flutter-windows` | A equipe sobe o número em `deploy/rustdesk-client/CLIENT_VERSION_FLUTTER` e gera o spike Flutter |
| **Tag RustDesk** (ex.: `1.5.0`) | `Cargo.toml` → `crate::VERSION` anunciada ao peer (protocolo / modo de teclado) | Só quando escolhemos uma tag mais nova do upstream no Actions |

A linha **1.x.x fica no Sciter**; o Flutter **não** reutiliza esse número — começa em **2.0.0** para não misturar instalador nem canal de update. A tag `1.5.0` **não sobe sozinha** a cada build — é a base do RustDesk.

Importante: **não** gravar `CLIENT_VERSION` no `Cargo.toml` principal. Se o peer anunciar `1.0.x` (abaixo de 1.2.0), o modo mapa de teclado some e atalhos do PDV (ex. tecla **D**) deixam de funcionar.

Canal de atualização: o Release publica `version.json`; o cliente compara e mostra o banner **Atualização disponível**.

Ao clicar em **Atualizar agora** (versão DeskRudder **1.0.9+**):

1. Baixa o `.exe` estável para a pasta temporária  
2. **Preferência silenciosa (postos instalados):** grava o caminho em `%PUBLIC%\DeskRudder\pending_update.txt`; o serviço Windows (`--service`, SYSTEM) aplica com `--update` **sem UAC** — necessário em PDV sem monitor/operador  
3. Se o serviço não estiver rodando, cai no UAC (`runas`) como antes  
4. Substitui os arquivos em `DeskRudder\Acesso Remoto` e **reabre** o app (e a bandeja)  

A sessão remota **pode cair** durante a troca de arquivos — o banner avisa.

### Transferência de arquivo

No posto, `enable-file-transfer` fica **Y** por padrão; no atendente, `enable-file-copy-paste` também. Para copiar arquivos com mais estabilidade, use o menu **Transferir arquivo** da sessão (janela própria), em vez de só colar pelo clipboard — em alguns PCs o copy-paste de arquivo pode derrubar a conexão.

## Como obter o `.exe` (equipe)

1. O workflow precisa estar na branch padrão (`main`) — após o merge deste PR, ele aparece em Actions.
2. No GitHub: **Actions** → escolha o workflow da tabela acima  
3. **Run workflow** — tag RustDesk **`1.5.0`** (nos builds de remoto)  
4. Remoto: ~40–90 min na 1.ª vez; Setup Electron: poucos minutos  
5. **Posto:** `/acesso-remoto/download`. **Atendente:** primeiro «Acesso Remoto Atendente», depois «App Atendente Setup» → `/app/download` — ver [`DESKTOP_ELECTRON.md`](DESKTOP_ELECTRON.md)

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
2. Aplica `deploy/rustdesk-client/scripts/apply_branding.py` (nome DeskRudder no exe, marca **DeskRemote** na UI, host/chave em `RENDEZVOUS_SERVERS` + `PROD_RENDEZVOUS_SERVER`, ícones e PNG do Sciter em `get_icon()`, modo só-recebe no posto / só-controla no atendente)
3. Compila o cliente Windows (UI Sciter), renomeia o binário para `DeskRudder.exe` (necessário para o Windows reconhecer a instalação) e empacota o portable
4. Publica o artefato `DeskRudder-AcessoRemoto-*.exe` e atualiza o Release `acesso-remoto-windows` (link do painel)

## Comportamento do cliente (postos)

O instalador é pensado para o PC que **vai ser acessado** (PDV / posto):

- Painel esquerdo com ID e senha; barra inferior de status (ex.: Pronto)
- Painel direito só com a logo DeskRudder (sem «Controle um computador remoto»)
- Conexões de saída bloqueadas (`is_incoming_only`)
- Atalho na Área de Trabalho / menu Iniciar: **DeskRemote** (o `.exe` instalado continua `DeskRudder.exe`)
- Uma só janela principal: segundo clique no atalho foca a janela já aberta (mutex de sessão Windows)
- Pasta de instalação: `C:\Program Files (x86)\DeskRudder\Acesso Remoto` (mantida por compatibilidade; outros apps DeskRudder podem ficar em pastas irmãs)
- Link «Desenvolvido por DeskRudder» → https://deskrudder.com.br/
- No Flutter, a marca fica no **rodapé** do painel esquerdo, com a versão DeskRudder (`CLIENT_VERSION_FLUTTER`, linha 2.x.x) abaixo; no Sciter a posição segue o upstream
- Flutter (2.0.1+): ícone da barra e da janela usam a arte oficial (D + atendente); Sobre o **DeskRemote** (site DeskRudder, copyright DeskRudder, sem privacidade do RustDesk); Rede mostra o servidor Duplex mesmo com os campos custom vazios; a aba da sessão usa o vínculo (ou usuário@host), não o ID numérico
- Tema escuro segue o Windows (conteúdo + barra de título) se a opção não foi fixada no menu (⋮ → Tema escuro)
- Logo do painel usa arte em alta resolução com fundo transparente (`ui-logo-512.png`) — sem placa opaca no tema escuro nem no claro; tamanho acompanha a janela
- Janela inicial ~760×720 (antes de instalar) para o botão **Instalar** do cartão UAC ficar visível

### Senha (uso único × permanente)

Por padrão o app usa **senha de uso único** (muda se alguém clicar no ícone de atualizar). **Não há senha permanente pré-configurada.**

Para acesso estável no posto:

1. Clique no lápis ao lado da senha
2. **Definir senha permanente** e escolha uma senha da equipe
3. Em **Usar senha permanente** (ou «ambas»), o refresh da senha de uso único deixa de impedir o acesso

## Comportamento do cliente (atendente)

O instalador de **controle** (`DeskRudder-AcessoRemoto-Controle.exe`, embutido no Setup do painel) é o PC que **inicia** a sessão:

- Painel para controlar outro computador (ID do posto + Conectar)
- Sem ID/senha deste PC — o atendente não é acessado e **não se registra** no servidor (`is_outgoing_only`)
- Por isso o notebook do atendente **não aparece** na frota como computador sem vínculo
- Quem já se registrou com o build antigo fica offline na frota — exclua na tela Acesso remoto
- Atalho e pasta iguais ao do posto (`DeskRemote` / `DeskRudder\Acesso Remoto`)
- Uma só janela principal no atalho; reconectar no mesmo ID remoto foca a sessão já aberta (ainda sem abas — ver #1248)

No spike **Flutter**, a home do atendente mostra a logo DeskRemote no topo do painel, o texto de edição personalizada, só a aba **Sessões recentes** (10 últimas) e o **nome do vínculo** (o `name=` do `deskrudder://`) no cartão — sem o ID numérico.

## Pasta no repo

| Caminho | Função |
|---------|--------|
| `deploy/rustdesk-client/server.config.json` | Host e chave |
| `deploy/rustdesk-client/CLIENT_VERSION` | Versão Sciter (produção, **1.x.x**) |
| `deploy/rustdesk-client/CLIENT_VERSION_FLUTTER` | Versão Flutter do atendente (**2.x.x**) |
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
- UI Flutter moderna / sessões em abas (#1248; o CI atual usa o build Sciter x86, estável no Actions)  
- Hospedar o `.exe` fora do GitHub (CDN próprio), se o Release deixar de bastar

## Referências

- [Client configuration](https://rustdesk.com/docs/en/self-host/client-configuration/)  
- [Build Windows](https://rustdesk.com/docs/en/dev/build/windows/)  
- Frota no painel: issue `#1184` / tela Acesso remoto  
