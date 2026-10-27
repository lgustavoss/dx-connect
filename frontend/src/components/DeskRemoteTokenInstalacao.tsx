import { useState } from 'react'
import { QRCodeSVG } from 'qrcode.react'
import { ApiError, empresaPdvs, type EmpresaPdv } from '../api/client'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { useToast } from './ui/Toast'
import { Button } from './ui/Button'
import { IconCopy } from './ui/IconCopy'

type Props = {
  empresaId: number
  pdvId: number
  acesso: EmpresaPdv.Acesso
}

export function DeskRemoteTokenInstalacao({ empresaId, pdvId, acesso }: Props) {
  const toast = useToast()
  const [gerando, setGerando] = useState(false)
  const [criado, setCriado] = useState<EmpresaPdv.TokenInstalacao | null>(null)

  async function gerar() {
    setGerando(true)
    try {
      const r = await empresaPdvs.gerarTokenDeskRemote(
        empresaId,
        pdvId,
        acesso.id > 0 ? acesso.id : undefined,
      )
      setCriado(r)
      toast.showSuccess('Link de instalação gerado. Cole no DeskRemote deste computador.')
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível gerar o link de instalação.'))
      if (err instanceof ApiError && err.status === 400) setCriado(null)
    } finally {
      setGerando(false)
    }
  }

  async function copiar() {
    if (!criado?.url) return
    try {
      await navigator.clipboard.writeText(criado.url)
      toast.showSuccess('Link copiado.')
    } catch {
      toast.showWarning('Não foi possível copiar. Selecione o link e copie na mão.')
    }
  }

  return (
    <div className="mt-3 space-y-3 rounded-lg border border-cyan-200/80 bg-cyan-50/60 p-3 dark:border-cyan-900/50 dark:bg-cyan-950/30">
      <p className="text-sm font-medium text-slate-800 dark:text-slate-100">Instalar o DeskRemote neste PDV</p>
      <p className="text-xs text-slate-600 dark:text-slate-400">
        Gera um link de uso único. No computador, cole no DeskRemote. A senha cadastrada aqui vai junto — não aparece no
        QR.
      </p>
      {criado ? (
        <div className="space-y-3">
          <div className="flex justify-center rounded-lg bg-white p-3">
            <QRCodeSVG value={criado.url} size={180} level="M" />
          </div>
          <p className="break-all text-xs text-slate-600 dark:text-slate-300">{criado.url}</p>
          <div className="flex flex-wrap gap-2">
            <Button type="button" variant="secondary" onClick={() => void copiar()}>
              <IconCopy className="size-4" />
              Copiar link
            </Button>
            <Button type="button" variant="ghost" onClick={() => void gerar()} disabled={gerando}>
              Gerar de novo
            </Button>
          </div>
          <p className="text-xs text-slate-500">
            Válido até {new Date(criado.expira_em).toLocaleString('pt-BR')}. Cada instalação pede um link novo.
          </p>
        </div>
      ) : (
        <Button type="button" onClick={() => void gerar()} disabled={gerando || !acesso.tem_senha_remota}>
          {gerando ? 'Gerando…' : 'Gerar QR e link'}
        </Button>
      )}
      {!acesso.tem_senha_remota ? (
        <p className="text-xs text-amber-800 dark:text-amber-200">Cadastre a senha deste acesso antes de gerar o link.</p>
      ) : null}
    </div>
  )
}
