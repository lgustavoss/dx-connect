; Pasta padrao: C:\Program Files (x86)\DeskRudder\Painel
; (irma de DeskRudder\Acesso Remoto). $PROGRAMFILES32 = Program Files (x86).

!macro preInit
  SetRegView 64
  WriteRegExpandStr HKLM "${INSTALL_REGISTRY_KEY}" InstallLocation "$PROGRAMFILES32\DeskRudder\Painel"
  WriteRegExpandStr HKCU "${INSTALL_REGISTRY_KEY}" InstallLocation "$PROGRAMFILES32\DeskRudder\Painel"
  SetRegView 32
  WriteRegExpandStr HKLM "${INSTALL_REGISTRY_KEY}" InstallLocation "$PROGRAMFILES32\DeskRudder\Painel"
  WriteRegExpandStr HKCU "${INSTALL_REGISTRY_KEY}" InstallLocation "$PROGRAMFILES32\DeskRudder\Painel"
!macroend

; Apos instalar o painel, instala o Acesso Remoto (controle)
; empacotado em resources\remoto-controle\ (requer elevacao — perMachine + allowElevation).

!macro customInstall
  DetailPrint "Instalando DeskRudder Acesso Remoto (controle)..."
  StrCpy $0 "$INSTDIR\resources\remoto-controle\DeskRudder-AcessoRemoto-Controle.exe"
  IfFileExists "$0" 0 remoto_ausente
  ; Preferir instalacao silenciosa (ja estamos elevados no perMachine).
  ExecWait '"$0" --silent-install' $1
  DetailPrint "silent-install encerrou com codigo $1"
  ; Se o packer nao aceitar silent (ou falhar), abre o assistente normal.
  IntCmp $1 0 remoto_fim remoto_ui remoto_ui
remoto_ui:
  DetailPrint "Tentando instalador com interface..."
  ExecWait '"$0"' $1
  DetailPrint "Instalador Acesso Remoto encerrou com codigo $1"
  Goto remoto_fim
remoto_ausente:
  DetailPrint "Aviso: instalador do Acesso Remoto nao encontrado em $0"
  MessageBox MB_OK|MB_ICONEXCLAMATION "O painel foi instalado, mas o Acesso Remoto nao veio no pacote.$\r$\nBaixe o DeskRudder-AcessoRemoto-Controle.exe no Release acesso-remoto-controle-windows ou rode o script desktop/scripts/baixar-remoto-controle.ps1 antes do npm run dist."
remoto_fim:
!macroend
