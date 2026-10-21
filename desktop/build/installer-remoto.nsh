; Pasta padrao: C:\Program Files (x86)\DeskRudder\Painel
; (irma de DeskRudder\Acesso Remoto). $PROGRAMFILES32 = Program Files (x86).

!include "nsDialogs.nsh"
!include "LogicLib.nsh"

!macro preInit
  SetRegView 64
  WriteRegExpandStr HKLM "${INSTALL_REGISTRY_KEY}" InstallLocation "$PROGRAMFILES32\DeskRudder\Painel"
  WriteRegExpandStr HKCU "${INSTALL_REGISTRY_KEY}" InstallLocation "$PROGRAMFILES32\DeskRudder\Painel"
  SetRegView 32
  WriteRegExpandStr HKLM "${INSTALL_REGISTRY_KEY}" InstallLocation "$PROGRAMFILES32\DeskRudder\Painel"
  WriteRegExpandStr HKCU "${INSTALL_REGISTRY_KEY}" InstallLocation "$PROGRAMFILES32\DeskRudder\Painel"
!macroend

; Macro sempre definida (electron-builder faz !ifdef); Page so no instalador.
!macro customPageAfterChangeDir
  !ifndef BUILD_UNINSTALLER
    Page custom deskRudderPreferenciasCreate deskRudderPreferenciasLeave
  !endif
!macroend

!ifndef BUILD_UNINSTALLER
Var DeskRudderPrefsDialog
Var DeskRudderChkAutostart
Var DeskRudderChkBandeja
Var DeskRudderPrefAutostart
Var DeskRudderPrefBandeja

Function deskRudderPreferenciasCreate
  nsDialogs::Create 1018
  Pop $DeskRudderPrefsDialog
  ${If} $DeskRudderPrefsDialog == error
    Abort
  ${EndIf}

  ${NSD_CreateLabel} 0 0 100% 36u "Escolha como o DeskRudder (painel) deve se comportar neste computador:"
  Pop $0

  ${NSD_CreateCheckbox} 0 40u 100% 16u "Iniciar o DeskRudder com o Windows"
  Pop $DeskRudderChkAutostart
  ${NSD_Check} $DeskRudderChkAutostart

  ${NSD_CreateCheckbox} 0 64u 100% 36u "Manter na bandeja e alertar com o painel fechado (icone perto do relogio)"
  Pop $DeskRudderChkBandeja
  ${NSD_Check} $DeskRudderChkBandeja

  StrCpy $DeskRudderPrefAutostart 1
  StrCpy $DeskRudderPrefBandeja 1

  nsDialogs::Show
FunctionEnd

Function deskRudderPreferenciasLeave
  ${NSD_GetState} $DeskRudderChkAutostart $DeskRudderPrefAutostart
  ${NSD_GetState} $DeskRudderChkBandeja $DeskRudderPrefBandeja
FunctionEnd
!endif

!macro customInstall
  !ifndef BUILD_UNINSTALLER
    ${If} $DeskRudderPrefAutostart == ""
      StrCpy $DeskRudderPrefAutostart 1
    ${EndIf}
    ${If} $DeskRudderPrefBandeja == ""
      StrCpy $DeskRudderPrefBandeja 1
    ${EndIf}

    DetailPrint "Gravando preferencias do instalador..."
    FileOpen $9 "$INSTDIR\installer-prefs.json" w
    ${If} $9 != ""
      FileWrite $9 "{"
      ${If} $DeskRudderPrefAutostart == 1
        FileWrite $9 '"iniciarComWindows":true,'
      ${Else}
        FileWrite $9 '"iniciarComWindows":false,'
      ${EndIf}
      ${If} $DeskRudderPrefBandeja == 1
        FileWrite $9 '"alertasNaBandeja":true'
      ${Else}
        FileWrite $9 '"alertasNaBandeja":false'
      ${EndIf}
      FileWrite $9 "}"
      FileClose $9
    ${EndIf}

    DetailPrint "Criando atalho DeskRudder na area de trabalho..."
    SetShellVarContext all
    CreateShortCut "$DESKTOP\DeskRudder.lnk" "$INSTDIR\DeskRudder.exe" "" "$INSTDIR\DeskRudder.exe" 0
    SetShellVarContext current
    CreateShortCut "$DESKTOP\DeskRudder.lnk" "$INSTDIR\DeskRudder.exe" "" "$INSTDIR\DeskRudder.exe" 0
  !endif

  DetailPrint "Instalando DeskRudder Acesso Remoto (controle)..."
  StrCpy $0 "$INSTDIR\resources\remoto-controle\DeskRudder-AcessoRemoto-Controle.exe"
  IfFileExists "$0" 0 remoto_ausente
  ExecWait '"$0" --silent-install' $1
  DetailPrint "silent-install encerrou com codigo $1"
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
