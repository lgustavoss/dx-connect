import { useEffect, useState } from 'react'
import { atendentes } from '../../api/client'
import { Button } from '../ui/Button'
import { Card } from '../ui/Card'
import { Select } from '../ui/Select'
import { useToast } from '../ui/Toast'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { rotuloResponsavelChat } from '../../lib/whatsappChatMeta'

type ChatResumo = {
  atendente_id?: number | null
  atendente_nome?: string | null
  setor_nome?: string | null
  estado: string
}

type Props = {
  open: boolean
  chat: ChatResumo | null
  usuarioId?: number | null
  setoresList: Array<{ id: number; nome: string }>
  onClose: () => void
  onTransferir: (setorId: number, atendenteId: number | null) => Promise<void>
  loading?: boolean
}

export function ChatTransferModal({
  open,
  chat,
  usuarioId,
  setoresList,
  onClose,
  onTransferir,
  loading = false,
}: Props) {
  const toast = useToast()
  const [transferSetorId, setTransferSetorId] = useState<number | ''>('')
  const [transferAtendenteId, setTransferAtendenteId] = useState<number | ''>('')
  const [atendentesDestino, setAtendentesDestino] = useState<Array<{ id: number; nome: string }>>([])
  const [erroAtendentesDestino, setErroAtendentesDestino] = useState<string | null>(null)

  useEffect(() => {
    if (!open) {
      setTransferSetorId('')
      setTransferAtendenteId('')
      setAtendentesDestino([])
      setErroAtendentesDestino(null)
    }
  }, [open])

  useEffect(() => {
    if (!open || !transferSetorId) {
      setAtendentesDestino([])
      setErroAtendentesDestino(null)
      return
    }
    atendentes
      .listPorSetor(Number(transferSetorId))
      .then((rows) => {
        setAtendentesDestino(rows.map((a) => ({ id: a.id, nome: a.nome })))
        setErroAtendentesDestino(null)
      })
      .catch((err) => {
        setAtendentesDestino([])
        setErroAtendentesDestino(mensagemFalhaParaToast(err))
      })
  }, [open, transferSetorId])

  if (!open) return null

  async function confirmar() {
    if (!transferSetorId) {
      toast.showWarning('Selecione o setor de destino.')
      return
    }
    await onTransferir(Number(transferSetorId), transferAtendenteId ? Number(transferAtendenteId) : null)
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-900/50 backdrop-blur-sm">
      <Card className="w-full max-w-lg p-6">
        <h3 className="text-lg font-bold">Transferir Atendimento</h3>
        {chat && (
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Responsável atual: <strong>{rotuloResponsavelChat(chat, usuarioId)}</strong>
            {chat.setor_nome ? ` • Setor ${chat.setor_nome}` : ''}
          </p>
        )}

        <div className="mt-4 space-y-4">
          <Select
            value={transferSetorId === '' ? '' : transferSetorId}
            onChange={(v) => {
              const n = v === '' ? '' : Number(v)
              setTransferSetorId(n)
              setTransferAtendenteId('')
            }}
            includeEmpty
            emptyLabel="Selecione o setor"
            options={setoresList.map((s) => ({ value: s.id, label: s.nome }))}
          />

          <Select
            value={transferAtendenteId === '' ? '' : transferAtendenteId}
            onChange={(v) => setTransferAtendenteId(v === '' ? '' : Number(v))}
            includeEmpty
            emptyLabel="Deixar na fila"
            disabled={!transferSetorId || atendentesDestino.length === 0}
            options={atendentesDestino.map((a) => ({ value: a.id, label: a.nome }))}
          />

          {erroAtendentesDestino && (
            <p className="text-xs text-amber-500">Sem permissão para escolher atendente neste setor.</p>
          )}
        </div>

        <div className="mt-6 flex justify-end gap-2">
          <Button onClick={onClose} variant="secondary" disabled={loading}>
            Cancelar
          </Button>
          <Button onClick={() => void confirmar()} loading={loading}>
            Transferir
          </Button>
        </div>
      </Card>
    </div>
  )
}
