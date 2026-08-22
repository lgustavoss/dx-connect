import { useEffect, useState } from 'react'
import { ApiError, tickets, type Tickets } from '../api/client'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { Button } from './ui/Button'
import { TEXTAREA_FIELD_CLASS } from './ui/Input'
import { useToast } from './ui/Toast'
import {
  mensagemEmFilaEmail,
  rotuloStatusEmail,
  segundosAteEnvio,
  textoContagemEnvio,
} from '../lib/ticketMensagemEmailOutbox'

type Props = {
  ticketId: number
  msg: Tickets.Mensagem
  podeGerir: boolean
  onAtualizado: () => void | Promise<void>
}

export function TicketMensagemEmailOutbox({ ticketId, msg, podeGerir, onAtualizado }: Props) {
  const toast = useToast()
  const [tick, setTick] = useState(0)
  const [busy, setBusy] = useState(false)
  const [editando, setEditando] = useState(false)
  const [editCorpo, setEditCorpo] = useState(msg.corpo)
  const [lockToken, setLockToken] = useState<string | null>(null)

  const status = msg.status
  const rotulo = rotuloStatusEmail(status)
  const seg = segundosAteEnvio(msg.scheduled_at)
  const contagem = status === 'pendente_envio' ? textoContagemEnvio(seg) : ''

  useEffect(() => {
    if (!mensagemEmFilaEmail(status)) return
    const id = window.setInterval(() => setTick((n) => n + 1), 1000)
    return () => window.clearInterval(id)
  }, [status, msg.scheduled_at])

  void tick

  if (!rotulo) return null

  async function recarregar() {
    await onAtualizado()
  }

  async function iniciarEdicao() {
    setBusy(true)
    try {
      const r = await tickets.startEditMensagem(ticketId, msg.id)
      setLockToken(r.edit_lock_token)
      setEditCorpo(r.mensagem.corpo)
      setEditando(true)
      await recarregar()
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível iniciar a edição.'))
    } finally {
      setBusy(false)
    }
  }

  async function salvarEdicao() {
    if (!lockToken) return
    const texto = editCorpo.trim()
    if (!texto) {
      toast.showWarning('A mensagem não pode ficar vazia.')
      return
    }
    setBusy(true)
    try {
      await tickets.updateMensagem(ticketId, msg.id, { corpo: texto, edit_lock_token: lockToken })
      setEditando(false)
      setLockToken(null)
      toast.showSuccess('Mensagem atualizada; o envio por e-mail foi reagendado.')
      await recarregar()
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível salvar.'))
    } finally {
      setBusy(false)
    }
  }

  async function cancelarEdicaoLocal() {
    setEditando(false)
    setLockToken(null)
    setEditCorpo(msg.corpo)
    await recarregar()
  }

  async function cancelarEnvio() {
    if (!confirm('Cancelar o envio desta mensagem por e-mail ao cliente?')) return
    setBusy(true)
    try {
      await tickets.cancelMensagemEmail(ticketId, msg.id)
      toast.showSuccess('Envio por e-mail cancelado.')
      await recarregar()
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível cancelar.'))
    } finally {
      setBusy(false)
    }
  }

  async function enviarAgora() {
    setBusy(true)
    try {
      await tickets.sendNowMensagemEmail(ticketId, msg.id)
      toast.showSuccess('E-mail enviado ao cliente.')
      await recarregar()
    } catch (err) {
      const det =
        err instanceof ApiError && typeof err.body === 'object' && err.body && 'detail' in err.body
          ? String((err.body as { detail: unknown }).detail)
          : null
      toast.showWarning(det || mensagemFalhaParaToast(err, 'Não foi possível enviar agora.'))
    } finally {
      setBusy(false)
    }
  }

  const emFila = mensagemEmFilaEmail(status)
  const badgeClass =
    status === 'cancelada'
      ? 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300'
      : status === 'enviada' || msg.cliente_notificado_por_email
        ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-200'
        : 'bg-sky-100 text-sky-800 dark:bg-sky-950/40 dark:text-sky-200'

  return (
    <div className="mt-3 rounded-lg border border-sky-200/80 bg-sky-50/50 px-3 py-2 dark:border-sky-800/50 dark:bg-sky-950/20">
      <div className="flex flex-wrap items-center gap-2">
        <span className={`rounded-md px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ${badgeClass}`}>
          {rotulo}
          {contagem ? ` · ${contagem}` : ''}
        </span>
      </div>

      {editando ? (
        <div className="mt-2 space-y-2">
          <textarea
            value={editCorpo}
            onChange={(e) => setEditCorpo(e.target.value)}
            rows={4}
            className={TEXTAREA_FIELD_CLASS}
            disabled={busy}
          />
          <div className="flex flex-wrap gap-2">
            <Button type="button" onClick={() => void salvarEdicao()} disabled={busy}>
              Salvar e reagendar envio
            </Button>
            <Button type="button" variant="secondary" onClick={() => void cancelarEdicaoLocal()} disabled={busy}>
              Desistir
            </Button>
          </div>
        </div>
      ) : (
        emFila &&
        podeGerir && (
          <div className="mt-2 flex flex-wrap gap-2">
            {status === 'pendente_envio' && (
              <>
                <Button type="button" variant="secondary" onClick={() => void iniciarEdicao()} disabled={busy}>
                  Editar
                </Button>
                <Button type="button" variant="cancel" onClick={() => void cancelarEnvio()} disabled={busy}>
                  Cancelar e-mail
                </Button>
                <Button type="button" onClick={() => void enviarAgora()} disabled={busy}>
                  Enviar agora
                </Button>
              </>
            )}
            {status === 'em_edicao' && (
              <p className="text-xs text-sky-800 dark:text-sky-200">Outra sessão pode estar a editar. Atualize ou inicie edição.</p>
            )}
          </div>
        )
      )}
    </div>
  )
}
