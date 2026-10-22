import { ApiError, empresaPdvs } from '../api/client'
import { conectarRemotoPreferindoDesktop } from './deskrudderDesktop'
import { urlConexaoDeskRudder } from './acessoRemotoUrl.mjs'

export { urlConexaoDeskRudder }

type ToastMin = {
  showSuccess: (msg: string) => void
  showWarning: (msg: string) => void
}

export function abrirClienteRustdesk(id: string, senha?: string | null) {
  const url = urlConexaoDeskRudder(id, senha)
  // Chrome/Edge ignoram clique sintético em <a> para protocolo customizado
  // (e rel=noreferrer também bloqueia). Navegação de topo usa o gesto do usuário.
  window.location.assign(url)
}

/** Abre o cliente de acesso remoto (app DeskRudder no desktop, ou protocolo no navegador). */
export async function conectarAcessoRemoto(
  rustdeskId: string,
  senha: string | null,
  toast: ToastMin,
  avisou = false,
): Promise<void> {
  const viaDesktop = await conectarRemotoPreferindoDesktop(rustdeskId, senha)
  if (viaDesktop) {
    if (!viaDesktop.ok) {
      toast.showWarning(viaDesktop.erro || 'Não foi possível abrir o acesso remoto neste computador.')
      return
    }
    if (viaDesktop.modo === 'protocolo' || viaDesktop.modo === 'protocolo-fallback') {
      const status = await window.deskrudderDesktop?.remotoStatus()
      if (status && !status.instalado) {
        toast.showWarning(
          'O DeskRemote não está instalado neste PC. Reinstale o app DeskRudder (Baixar app Windows em Sobre) ou peça o instalador de controle à equipe.',
        )
        return
      }
    }
  } else {
    abrirClienteRustdesk(rustdeskId, senha)
  }
  if (!avisou) {
    toast.showSuccess(
      senha
        ? 'Acesso remoto aberto com o ID e a senha do cadastro (janela DeskRemote).'
        : 'Acesso remoto aberto com este ID (janela DeskRemote).',
    )
  }
}

/** Tenta a senha do PDV; 404 = sem senha cadastrada (não avisa). */
export async function senhaDoPdv(
  empresaId: number,
  pdvId: number,
  toast: ToastMin,
): Promise<{ senha: string | null; avisou: boolean }> {
  return senhaDoAcesso(empresaId, pdvId, null, toast)
}

/** Tenta a senha de um acesso remoto; 404 = sem senha cadastrada (não avisa). */
export async function senhaDoAcesso(
  empresaId: number,
  pdvId: number,
  acessoId: number | null,
  toast: ToastMin,
): Promise<{ senha: string | null; avisou: boolean }> {
  try {
    const credencial =
      acessoId != null
        ? await empresaPdvs.revelarCredencialAcesso(empresaId, pdvId, acessoId)
        : await empresaPdvs.revelarCredencial(empresaId, pdvId)
    return { senha: credencial.acesso_remoto_senha?.trim() || null, avisou: false }
  } catch (err) {
    if (!(err instanceof ApiError) || err.status !== 404) {
      toast.showWarning('A senha do cadastro não foi usada. O acesso remoto pode pedi-la.')
      return { senha: null, avisou: true }
    }
    return { senha: null, avisou: false }
  }
}
