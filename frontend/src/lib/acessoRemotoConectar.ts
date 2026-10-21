import { ApiError, empresaPdvs } from '../api/client'
import { conectarRemotoPreferindoDesktop } from './deskrudderDesktop'

type ToastMin = {
  showSuccess: (msg: string) => void
  showWarning: (msg: string) => void
}

export function abrirClienteRustdesk(id: string, senha?: string | null) {
  const digitos = id.replace(/\s+/g, '')
  const params = new URLSearchParams()
  if (senha?.trim()) params.set('password', senha.trim())
  const consulta = params.toString()
  const link = document.createElement('a')
  link.href = `rustdesk://connection/new/${digitos}${consulta ? `?${consulta}` : ''}`
  link.rel = 'noreferrer'
  document.body.appendChild(link)
  link.click()
  link.remove()
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
          'O DeskRudder Acesso Remoto não está instalado neste PC. Reinstale o app DeskRudder (Baixar app Windows em Sobre) ou peça o instalador de controle à equipe.',
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
        ? 'Acesso remoto aberto com o ID e a senha do cadastro (janela DeskRudder - Acesso Remoto).'
        : 'Acesso remoto aberto com este ID (janela DeskRudder - Acesso Remoto).',
    )
  }
}

/** Tenta a senha do PDV; 404 = sem senha cadastrada (não avisa). */
export async function senhaDoPdv(
  empresaId: number,
  pdvId: number,
  toast: ToastMin,
): Promise<{ senha: string | null; avisou: boolean }> {
  try {
    const credencial = await empresaPdvs.revelarCredencial(empresaId, pdvId)
    return { senha: credencial.acesso_remoto_senha?.trim() || null, avisou: false }
  } catch (err) {
    if (!(err instanceof ApiError) || err.status !== 404) {
      toast.showWarning('A senha do cadastro não foi usada. O acesso remoto pode pedi-la.')
      return { senha: null, avisou: true }
    }
    return { senha: null, avisou: false }
  }
}
