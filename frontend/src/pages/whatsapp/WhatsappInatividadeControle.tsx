import { useEffect, useMemo, useState } from 'react'
import { whatsappChats, whatsappSettings, type WhatsappChats } from '../../api/client'
import { Button } from '../../components/ui/Button'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { useToast } from '../../components/ui/Toast'

type Props = {
  chat: WhatsappChats.Chat
  msgs: WhatsappChats.Mensagem[]
  isResponsavel: boolean
  onChatUpdate: (c: WhatsappChats.Chat) => void
}

function formatMmSs(totalSec: number): string {
  const s = Math.max(0, Math.floor(totalSec))
  const mm = String(Math.floor(s / 60)).padStart(2, '0')
  const ss = String(s % 60).padStart(2, '0')
  return `${mm}:${ss}`
}

/** Controlo de inatividade: countdown + pausar/retomar (#577). */
export function WhatsappInatividadeControle({ chat, msgs, isResponsavel, onChatUpdate }: Props) {
  const toast = useToast()
  const [avisoMin, setAvisoMin] = useState(15)
  const [ativa, setAtiva] = useState(false)
  const [busy, setBusy] = useState(false)
  const [tick, setTick] = useState(0)

  useEffect(() => {
    let cancelled = false
    void whatsappSettings
      .get()
      .then((r) => {
        if (cancelled) return
        setAtiva(Boolean(r.inativ_encerramento_ativa))
        setAvisoMin(Math.max(1, Number(r.inativ_aviso_minutos ?? 15)))
      })
      .catch(() => {
        /* settings indisponíveis — esconde controlo */
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (!ativa || chat.estado !== 'em_atendimento') return
    const id = window.setInterval(() => setTick((t) => t + 1), 1000)
    return () => window.clearInterval(id)
  }, [ativa, chat.estado])

  const restanteSec = useMemo(() => {
    void tick
    if (!ativa || chat.estado !== 'em_atendimento') return null
    if (chat.inatividade_pausada) return avisoMin * 60

    const relevant = msgs.filter(
      (m) =>
        m.evento_sistema !== 'comentario_interno' &&
        (m.direcao === 'inbound' ||
          (m.direcao === 'outbound' && !m.evento_sistema)),
    )
    const last = relevant[relevant.length - 1]
    const candidatos: number[] = []
    if (last?.created_at) candidatos.push(new Date(last.created_at).getTime())
    if (chat.inatividade_retomada_em) candidatos.push(new Date(chat.inatividade_retomada_em).getTime())
    if (candidatos.length === 0) return avisoMin * 60

    const refMs = Math.max(...candidatos)
    const elapsed = (Date.now() - refMs) / 1000
    return Math.max(0, avisoMin * 60 - elapsed)
  }, [ativa, chat, msgs, avisoMin, tick])

  if (!ativa || chat.estado !== 'em_atendimento' || !isResponsavel || restanteSec == null) {
    return null
  }

  async function toggle() {
    setBusy(true)
    try {
      const next = chat.inatividade_pausada
        ? await whatsappChats.retomarInatividade(chat.id)
        : await whatsappChats.pausarInatividade(chat.id)
      onChatUpdate(next)
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível alterar a pausa de inatividade.'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex items-center gap-1.5">
      <span
        className={`tabular-nums text-xs font-semibold ${
          chat.inatividade_pausada
            ? 'text-amber-600 dark:text-amber-300'
            : restanteSec <= 60
              ? 'text-rose-600 dark:text-rose-300'
              : 'text-slate-500 dark:text-slate-400'
        }`}
        title={
          chat.inatividade_pausada
            ? 'Inatividade pausada — prazo reiniciado'
            : 'Tempo até o aviso de inatividade'
        }
      >
        {formatMmSs(restanteSec)}
      </span>
      <Button
        type="button"
        variant="ghost"
        className="h-8 px-2 text-xs"
        loading={busy}
        onClick={() => void toggle()}
      >
        {chat.inatividade_pausada ? 'Retomar' : 'Pausar'}
      </Button>
    </div>
  )
}
