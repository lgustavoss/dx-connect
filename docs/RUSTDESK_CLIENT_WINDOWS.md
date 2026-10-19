# Cliente Windows DeskRudder (RustDesk personalizado)

Instalador / build do **acesso remoto** com marca DeskRudder e servidor OSS da Duplex (`hbbs`/`hbbr`).

Escopo v1: **somente Windows**. Relacionado à frota no painel (`#1184`, tela Acesso remoto).

## Servidor (já validado)

| Campo | Valor |
|-------|--------|
| ID Server / Relay | `31.97.160.79` |
| Key (pública) | `kEoYK77jUT92KWnj1XmqYRgIRKv4VkGNMjFjm33HtjI=` |
| Portas | `21115`–`21117` |

Fonte no repo: `deploy/rustdesk-client/server.config.json`.

String de importação (Settings → Network → Import / `rustdesk.exe --config`):

```text
9JiI6ISawFmIsISPJpGdINzMtpmRq1kTHtmV0Y3SSl0ZSlVcthVMq52VLJTOUVla3czSZ9WRrJiOikXZrJCLikzNuAjNx4yN54SMzIiOikXYsVmciwiI5cjLwYTMucTOuEzMiojI0N3boJye
```

Regenerar / decodificar:

```bash
python3 deploy/rustdesk-client/scripts/encode_config.py
python3 deploy/rustdesk-client/scripts/encode_config.py --decode '…'
```

## Duas fases

### Fase 0 — config no RustDesk oficial (rápido)

Script: `deploy/rustdesk-client/windows/Install-DeskRudderRemote.ps1`

1. Baixe o `.exe` Windows em [releases do RustDesk](https://github.com/rustdesk/rustdesk/releases).
2. No PowerShell:

```powershell
cd deploy\rustdesk-client\windows
.\Install-DeskRudderRemote.ps1 -InstallerPath C:\Temp\rustdesk-….exe
```

Aplica `--config` com o servidor Duplex. **Não** altera nome/logo do aplicativo.

### Fase 1 — `.exe` DeskRudder (nome + logo + servidor embutidos)

Build a partir do código open source ([docs oficiais Windows](https://rustdesk.com/docs/en/dev/build/windows/)).

**Máquina de build:** Windows com VS C++, Rust, vcpkg, LLVM, Flutter (versões recentes do RustDesk usam Flutter — confira o `README` do tag pinado).

```bash
git clone --recurse-submodules https://github.com/rustdesk/rustdesk.git
# opcional: git checkout <tag estável>
bash deploy/rustdesk-client/scripts/apply_branding.sh /caminho/para/rustdesk
```

O script:

- Copia ícones de `deploy/rustdesk-client/branding/`
- Ajusta `Cargo.toml` (`deskrudder` / DeskRudder)
- Em `libs/hbb_common/src/config.rs`: `APP_NAME`, `RENDEZVOUS_SERVERS`, `RS_PUB_KEY`

Depois, no clone (Git Bash), siga o guia de build e, tipicamente:

```bash
python build.py --portable --flutter --feature IddDriver hwcodec
```

Artefacto esperado: instalador / portable Windows com marca DeskRudder apontando só ao servidor Duplex.

## Licença

RustDesk é **AGPL-3.0**. Ao distribuir um binário modificado, é obrigatório disponibilizar o código correspondente (fork ou diff + instruções).

## O que ainda não fazemos neste lote

- macOS / Linux / Android
- RustDesk Server Pro / Custom Client Generator
- Assinatura Authenticode (pode entrar depois)
- Publicar o `.exe` automaticamente no painel SaaS

## Referências

- [Client configuration](https://rustdesk.com/docs/en/self-host/client-configuration/)
- [Build Windows](https://rustdesk.com/docs/en/dev/build/windows/)
- Agente da frota no VPS: `scripts/rustdesk_hbbs_agent.py`
