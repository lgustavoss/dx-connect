# Cliente Windows DeskRudder (acesso remoto)

**Vocabulário:** **atendente** = quem inicia a sessão; **cliente** = PC atendido. «Posto» é só um tipo de cliente do piloto DuplexSoft.

Há **cinco workflows** no Actions (nomes na UI):

| Workflow | Artefato | Release | Uso |
|----------|----------|---------|-----|
| **DeskRemote Cliente v1** | `DeskRudder-AcessoRemoto.exe` | `acesso-remoto-windows` | Sciter **congelado em 1.0.14** (32-bit / fallback) |
| **DeskRemote Atendente v1** | `DeskRudder-AcessoRemoto-Controle.exe` | `acesso-remoto-controle-windows` | Sciter **congelado em 1.0.14** (32-bit / fallback) |
| **DeskRudder Painel v1** | `DeskRudder-Setup.exe` | `desktop-windows` | Painel + embute o DeskRemote Atendente **v2** |
| **DeskRemote Atendente v2** | `DeskRudder-AcessoRemoto-Controle-Flutter.exe` | `acesso-remoto-controle-flutter-windows` | Remoto Flutter do atendente (embutido no Setup) |
| **DeskRemote Cliente v2** | `DeskRudder-AcessoRemoto-Flutter.exe` | `acesso-remoto-windows-flutter` | PC do **cliente** — `/acesso-remoto/download` |

Assim o Setup do painel fica rápido; o build longo do RustDesk só roda quando o remoto muda.

**Cliente Flutter 2.0 — o que o PC atendido recebe:**  
instalador genérico (`DeskRudder-AcessoRemoto-Flutter.exe`). Servidor e senha vêm do token de instalação (QR/link no PDV), não do binário.

Cliente e atendente usam o **mesmo** `deploy/rustdesk-client/branding/` (e `kit-1253/` para Flutter). Ao trocar a arte: regenere com `render_remote_icons.py`, suba a versão do canal (`CLIENT_VERSION` no Sciter, `CLIENT_VERSION_FLUTTER` no Flutter do atendente, `CLIENT_VERSION_FLUTTER_CLIENTE` no Flutter do cliente) e rode os workflows de remoto.

## Versão (importante)

Há **quatro** números envolvidos:

| O quê | Onde | Muda quando |
|-------|------|-------------|
| **Sciter (congelado)** (`CLIENT_VERSION` = **1.0.14**) | Releases v1 `acesso-remoto-windows` e `acesso-remoto-controle-windows` | Sem builds novos. Hotfix 32-bit: Actions v1 com `confirmar=gerar-sciter` |
| **Flutter (atendente v2)** (`CLIENT_VERSION_FLUTTER`, linha **2.x.x**, ex.: `2.3.0`) | UI Flutter e update do Release `acesso-remoto-controle-flutter-windows` | A equipe sobe o número em `deploy/rustdesk-client/CLIENT_VERSION_FLUTTER` e gera o **DeskRemote Atendente v2** |
| **Flutter (cliente v2)** (`CLIENT_VERSION_FLUTTER_CLIENTE`, linha **2.x.x**, ex.: `2.0.1`) | UI Flutter e update do Release `acesso-remoto-windows-flutter` | A equipe sobe o número em `deploy/rustdesk-client/CLIENT_VERSION_FLUTTER_CLIENTE` e gera o **DeskRemote Cliente v2** |
| **Tag RustDesk** (ex.: `1.5.0`) | `Cargo.toml` → `crate::VERSION` anunciada ao peer (protocolo / modo de teclado) | Só quando escolhemos uma tag mais nova do upstream no Actions |

A linha **1.x.x fica no Sciter (congelada em 1.0.14)**; o Flutter **não** reutiliza esse número — começa em **2.0.0** para não misturar instalador nem canal de update. A tag `1.5.0` **não sobe sozinha** a cada build — é a base do RustDesk.

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

Subir `CLIENT_VERSION_FLUTTER` no git **não** publica o instalador. Depois do merge na `main`:

1. **DeskRemote Cliente v2** — **Publicar Release** ligado (tag RustDesk `1.5.0`, ~40–90 min) — só se o cliente Flutter mudou
2. **DeskRemote Atendente v2** — **Publicar Release** ligado (gera o **2.3.0** deste lote)
3. **DeskRudder Painel v1** — embute o atendente v2 em `/app/download`
4. Só então o deploy do painel (`/release-staging`)

O workflow precisa estar na branch padrão (`main`). **Cliente (PC atendido):** `/acesso-remoto/download`. Detalhe do Setup: [`DESKTOP_ELECTRON.md`](DESKTOP_ELECTRON.md).

URL curta na instância (sem login — Nginx redireciona; o SPA também cobre se o Nginx ainda não tiver a regra):

`https://{cliente}.deskrudder.com.br/acesso-remoto/download`

Exemplo Duplex: `https://duplexsoft.deskrudder.com.br/acesso-remoto/download`

URL do arquivo no GitHub (destino do redirect):

`https://github.com/lgustavoss/dx-connect/releases/download/acesso-remoto-windows-flutter/DeskRudder-AcessoRemoto-Flutter.exe`

Workflow do download: `.github/workflows/acesso-remoto-cliente-flutter-windows.yml`

## Servidor

O **Sciter 1.0.14** e o `server.config.json` ainda embutem o hbbs da Duplex (`31.97.160.79` + chave pública). Isso vale só para o canal v1 congelado.

No **Flutter 2.x** o binário **não** nasce com esse host:

- **Cliente:** o token de instalação devolve o servidor da instância (`RUSTDESK_*` no `.env`).
- **Atendente (2.3.0+):** depois do login (ou da sessão herdada do Electron), o app chama `GET /v1/rustdesk/configuracao` (`rustdesk.monitorar`) e grava ID/relay/chave. `--connect` / `deskrudder://` aplica o servidor se houver sessão; senão, reusa o último gravado neste PC. Primeira conexão pelo Chrome sem nunca ter entrado no DeskRemote: abrir o app e entrar uma vez.

Fonte Sciter: `deploy/rustdesk-client/server.config.json`.

## O que o CI faz

1. Clona [rustdesk/rustdesk](https://github.com/rustdesk/rustdesk) (tag escolhida)
2. Aplica `deploy/rustdesk-client/scripts/apply_branding.py` (marca **DeskRemote**, ícones, modo só-recebe no cliente / só-controla no atendente). No **Sciter**, embute o hbbs da Duplex. No **Flutter**, o binário fica genérico (`deskremote.invalid`) e o app puxa o servidor da instância
3. Compila o Windows (Sciter v1 congelado, ou Flutter 2.x), renomeia o binário para `DeskRudder.exe` e empacota o portable
4. Publica o artefato e atualiza o Release do canal (`acesso-remoto-windows-flutter` no cliente 2.x; `acesso-remoto-controle-flutter-windows` no atendente 2.x)

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
- Flutter (2.0.2+): o nome **DeskRemote** aparece na barra de título (tema claro e escuro) e abaixo da logo do painel; ao conectar pelo painel ou pelo ID já conhecido, a aba da sessão usa o rótulo do vínculo; ícone da barra de tarefas e da barra de título tem contorno branco **só no Flutter** (o Sciter do posto continua na arte 1.0.14); logo do painel maior e mais nítida; Sobre o **DeskRemote** (site DeskRudder, copyright DeskRudder, sem privacidade do RustDesk). A partir da **2.3.0** (atendente), Rede mostra o servidor da conta após o login — não o da Duplex compilado
- Tema escuro segue o Windows (conteúdo + barra de título) se a opção não foi fixada no menu (⋮ → Tema escuro)
- Logo do painel usa arte em alta resolução com fundo transparente (`ui-logo-512.png`) — sem placa opaca no tema escuro nem no claro; tamanho acompanha a janela
- Janela inicial ~760×720 (antes de instalar) para o botão **Instalar** do cartão UAC ficar visível

### Senha (uso único × permanente)

No **Sciter 1.0.14 (congelado)**, o app usa **senha de uso único** por padrão (muda se alguém clicar no ícone de atualizar). **Não há senha permanente pré-configurada.**

Para acesso estável no posto (Sciter):

1. Clique no lápis ao lado da senha
2. **Definir senha permanente** e escolha uma senha da equipe
3. Em **Usar senha permanente** (ou «ambas»), o refresh da senha de uso único deixa de impedir o acesso

No **DeskRemote Cliente v2**, a senha permanente **vem do painel**. Não dá para editar no app: quem tem `empresas.editar` gera um QR/link na ficha do PDV; o DeskRemote resgata o token, aplica o servidor da instância e a senha cadastrada, e devolve o ID. Se a senha mudar no cadastro, o PC aplica sozinho na próxima consulta (cerca de 2 minutos, ou ao ligar).

### Token de instalação (cliente Flutter)

1. Cadastre o PDV com senha DeskRemote.
2. Na ficha do PDV, **Gerar QR e link** (uso único, ~72 h). A senha **não** vai no QR.
3. No PC, instale `DeskRudder-AcessoRemoto-Flutter.exe` (Release `acesso-remoto-windows-flutter`) e cole o link.
4. O app chama `POST /v1/deskremote/enroll` na API da instância (`api-{slug}.deskrudder.com.br`), grava a credencial em `%APPDATA%\DeskRudder\deskremote-dispositivo.json` e confirma o ID.
5. Gerar de novo no mesmo PDV invalida o link anterior; o próximo resgate substitui o computador vinculado.

## Comportamento do cliente (atendente)

O instalador de **controle** (`DeskRudder-AcessoRemoto-Controle.exe`, embutido no Setup do painel) é o PC que **inicia** a sessão:

- Painel para controlar outro computador (ID do posto + Conectar)
- Sem ID/senha deste PC — o atendente não é acessado e **não se registra** no servidor (`is_outgoing_only`)
- Por isso o notebook do atendente **não aparece** na frota como computador sem vínculo
- Quem já se registrou com o build antigo fica offline na frota — exclua na tela Acesso remoto
- Atalho e pasta iguais ao do posto (`DeskRemote` / `DeskRudder\Acesso Remoto`)
- Uma só janela principal no atalho; reconectar no mesmo ID remoto foca a sessão já aberta (Sciter v1 não tem abas)

No **DeskRemote Atendente v2**, a home mostra a logo DeskRemote no topo do painel, o texto de edição personalizada, as abas **Sessões recentes** (10 últimas) e **Vinculados** (frota do sistema) e o **nome do vínculo** no cartão — sem o ID numérico. A partir da **2.3.0**, o servidor de acesso remoto vem da conta (não do instalador).

A partir da **2.1.0**, Recentes e o campo de ID exigem login com a **mesma conta do DeskRudder** (identificador + e-mail + senha). Quem já entrou no app Electron neste PC **com “lembrar-me”** não precisa digitar de novo: a sessão fica em `%APPDATA%\DeskRudder\deskremote-sessao.json` (o mesmo JWT do `localStorage` do painel). Login só nesta sessão do navegador/Electron **não** grava o arquivo. Herdar a sessão exige um Setup do painel que já grave esse arquivo — Setup antigo não herda. Conectar pelo painel (`--connect` / `deskrudder://`) **não** pede login de propósito: a sessão remota abre direto, como hoje. **Sair** no DeskRemote apaga o arquivo: a próxima abertura pede login de novo (mesmo que o DeskRudder ainda esteja aberto). **Sair** no DeskRudder também apaga. A permissão continua `rustdesk.monitorar`. O Sciter **1.0.14 está congelado**. A partir da **2.2.0**, a aba **Vinculados** lista os computadores com PDV ligado (`GET /v1/rustdesk/peers?filtro=vinculado`): rótulo, Online/Offline e clique para conectar (tenta a senha do cadastro se a conta tiver `pdv.acessos.ver` ou `empresas.editar`). A busca é da própria aba (a do RustDesk some nela). Se o mesmo ID estiver em vários PDVs, o item usa o hostname e lista os vínculos — não inventa um rótulo único.

A partir da **2.1.1**, a aba da sessão usa o rótulo do vínculo (ex. `Auto Posto Expresso Medalha · SERVIDOR 001`, **nome da empresa** + equipamento) nesta ordem: `name=` / `--title` do painel; senão, busca na frota (`GET /v1/rustdesk/peers`) com a sessão DeskRudder; senão, usuário@host. O painel em produção antigo ainda não manda `name=` — por isso a busca na API. Sem sessão e sem `name=`, o ID pode aparecer até o hostname chegar.

## Pasta no repo

| Caminho | Função |
|---------|--------|
| `deploy/rustdesk-client/server.config.json` | Host e chave |
| `deploy/rustdesk-client/CLIENT_VERSION` | Versão Sciter (**congelada em 1.0.14**) |
| `deploy/rustdesk-client/CLIENT_VERSION_FLUTTER` | Versão Flutter do atendente (**2.x.x**) |
| `deploy/rustdesk-client/CLIENT_VERSION_FLUTTER_CLIENTE` | Versão Flutter do cliente (**2.x.x**, começa em 2.0.0) |
| `deploy/rustdesk-client/branding/` | Arte oficial + `icon.ico`/tray/PNGs — regenerar com `scripts/render_remote_icons.py` |
| `deploy/rustdesk-client/scripts/apply_branding.py` | Patch no clone |
| `deploy/rustdesk-client/flutter-overlay/` | Login do atendente + token/sync do cliente (copiado para o clone Flutter) |
| `deploy/rustdesk-client/scripts/encode_config.py` | Gera/decodifica string de import (debug) |
| `.github/workflows/rustdesk-deskrudder-windows.yml` | Build Sciter do cliente (**congelado**; hotfix: `confirmar=gerar-sciter`) |
| `.github/workflows/acesso-remoto-atendente-windows.yml` | Build Sciter do atendente (**congelado**) |
| `.github/workflows/acesso-remoto-cliente-flutter-windows.yml` | Flutter do cliente (token + instalador genérico) |

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
- PCs 32-bit no Flutter (ficam no Sciter 1.0.14 congelado)  
- Hospedar o `.exe` fora do GitHub (CDN próprio), se o Release deixar de bastar

## Referências

- [Client configuration](https://rustdesk.com/docs/en/self-host/client-configuration/)  
- [Build Windows](https://rustdesk.com/docs/en/dev/build/windows/)  
- Frota no painel: issue `#1184` / tela Acesso remoto  
