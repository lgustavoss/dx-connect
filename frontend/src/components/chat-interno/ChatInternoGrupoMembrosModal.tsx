import { useEffect, useMemo, useState } from 'react'
import { atendentes, chatInterno, type ChatInterno } from '../../api/client'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { useAuth } from '../../contexts/AuthContext'
import { Button } from '../ui/Button'
import { useToast } from '../ui/Toast'
import { MODAL_OVERLAY, MODAL_PANEL_SCROLLABLE } from '../../lib/modalPanel'

type Props = {
  open: boolean
  conversaId: number
  tituloGrupo?: string
  participantes: ChatInterno.ParticipanteGrupo[]
  souAdmin?: boolean
  onClose: () => void
  onAtualizado: (conversa: ChatInterno.Conversa) => void
}

function MembroItem({
  participante,
  souAdmin,
  salvando,
  userId,
  onPromover,
  onRebaixar,
  onRemover,
}: {
  participante: ChatInterno.ParticipanteGrupo
  souAdmin: boolean
  salvando: boolean
  userId?: number
  onPromover: (id: number) => void
  onRebaixar: (id: number) => void
  onRemover: (id: number) => void
}) {
  const isAdmin = participante.papel === 'admin'
  const isSelf = participante.atendente_id === userId

  return (
    <li
      className={`flex items-center justify-between gap-2 rounded-lg border px-3 py-2.5 text-sm ${
        isAdmin
          ? 'border-violet-200 bg-violet-50/80 dark:border-violet-800 dark:bg-violet-950/30'
          : 'border-slate-200 dark:border-slate-700'
      }`}
    >
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="truncate font-medium text-slate-900 dark:text-slate-100">{participante.nome}</span>
          {isSelf && <span className="text-xs text-slate-500">(você)</span>}
          {isAdmin && (
            <span className="shrink-0 rounded-full bg-violet-600 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white">
              Admin
            </span>
          )}
        </div>
      </div>
      {souAdmin && (
        <div className="flex shrink-0 gap-1">
          {!isAdmin && (
            <button
              type="button"
              disabled={salvando}
              className="text-xs text-violet-600 hover:underline dark:text-violet-400"
              onClick={() => onPromover(participante.atendente_id)}
            >
              Tornar admin
            </button>
          )}
          {isAdmin && !isSelf && (
            <button
              type="button"
              disabled={salvando}
              className="text-xs text-slate-500 hover:underline"
              onClick={() => onRebaixar(participante.atendente_id)}
            >
              Rebaixar
            </button>
          )}
          {!isSelf && (
            <button
              type="button"
              disabled={salvando}
              className="text-xs text-rose-600 hover:underline"
              onClick={() => onRemover(participante.atendente_id)}
            >
              Remover
            </button>
          )}
        </div>
      )}
    </li>
  )
}

function SecaoMembros({
  titulo,
  membros,
  souAdmin,
  salvando,
  userId,
  onPromover,
  onRebaixar,
  onRemover,
}: {
  titulo: string
  membros: ChatInterno.ParticipanteGrupo[]
  souAdmin: boolean
  salvando: boolean
  userId?: number
  onPromover: (id: number) => void
  onRebaixar: (id: number) => void
  onRemover: (id: number) => void
}) {
  if (membros.length === 0) return null

  return (
    <div className="mt-4">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">{titulo}</h3>
      <ul className="mt-2 space-y-1.5">
        {membros.map((p) => (
          <MembroItem
            key={p.atendente_id}
            participante={p}
            souAdmin={souAdmin}
            salvando={salvando}
            userId={userId}
            onPromover={onPromover}
            onRebaixar={onRebaixar}
            onRemover={onRemover}
          />
        ))}
      </ul>
    </div>
  )
}

export function ChatInternoGrupoMembrosModal({
  open,
  conversaId,
  tituloGrupo,
  participantes,
  souAdmin = false,
  onClose,
  onAtualizado,
}: Props) {
  const toast = useToast()
  const { user } = useAuth()
  const [lista, setLista] = useState(participantes)
  const [busca, setBusca] = useState('')
  const [resultados, setResultados] = useState<Awaited<ReturnType<typeof atendentes.list>>['items']>([])
  const [salvando, setSalvando] = useState(false)

  useEffect(() => {
    if (open) setLista(participantes)
  }, [open, participantes])

  useEffect(() => {
    if (!open || !souAdmin) {
      setBusca('')
      setResultados([])
      return
    }
    const q = busca.trim()
    if (q.length < 2) {
      setResultados([])
      return
    }
    const timer = setTimeout(async () => {
      try {
        const { items } = await atendentes.list({ busca: q, limit: 15, incluir_inativos: false })
        const ids = new Set(lista.map((p) => p.atendente_id))
        setResultados(items.filter((a) => a.id !== user?.id && !ids.has(a.id)))
      } catch {
        setResultados([])
      }
    }, 300)
    return () => clearTimeout(timer)
  }, [busca, open, lista, user?.id, souAdmin])

  const { admins, membros } = useMemo(() => {
    const adminList = lista.filter((p) => p.papel === 'admin')
    const membroList = lista.filter((p) => p.papel !== 'admin')
    return { admins: adminList, membros: membroList }
  }, [lista])

  async function aplicar(patch: Parameters<typeof chatInterno.atualizarParticipantesGrupo>[1]) {
    setSalvando(true)
    try {
      const conv = await chatInterno.atualizarParticipantesGrupo(conversaId, patch)
      setLista(conv.participantes ?? [])
      onAtualizado(conv)
      toast.showSuccess('Membros atualizados.')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível atualizar os membros.'))
    } finally {
      setSalvando(false)
    }
  }

  if (!open) return null

  return (
    <div className={MODAL_OVERLAY} role="dialog" aria-modal="true" aria-labelledby="grupo-membros-titulo" onClick={onClose}>
      <div className={MODAL_PANEL_SCROLLABLE} onClick={(e) => e.stopPropagation()}>
        <h2 id="grupo-membros-titulo" className="text-lg font-bold text-slate-900 dark:text-white">
          {tituloGrupo ?? 'Grupo'}
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          {lista.length} {lista.length === 1 ? 'participante' : 'participantes'}
        </p>

        <SecaoMembros
          titulo="Administradores do grupo"
          membros={admins}
          souAdmin={souAdmin}
          salvando={salvando}
          userId={user?.id}
          onPromover={(id) => void aplicar({ promover_admin: [id] })}
          onRebaixar={(id) => void aplicar({ rebaixar_admin: [id] })}
          onRemover={(id) => void aplicar({ remover: [id] })}
        />
        <SecaoMembros
          titulo="Participantes"
          membros={membros}
          souAdmin={souAdmin}
          salvando={salvando}
          userId={user?.id}
          onPromover={(id) => void aplicar({ promover_admin: [id] })}
          onRebaixar={(id) => void aplicar({ rebaixar_admin: [id] })}
          onRemover={(id) => void aplicar({ remover: [id] })}
        />

        {souAdmin && (
          <>
            <h3 className="mt-5 text-xs font-semibold uppercase tracking-wide text-slate-500">Adicionar membro</h3>
            <input
              type="search"
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              placeholder="Buscar atendente para adicionar…"
              className="mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900"
            />
            <ul className="mt-2 max-h-32 space-y-1 overflow-y-auto">
              {resultados.map((a) => (
                <li key={a.id}>
                  <button
                    type="button"
                    disabled={salvando}
                    className="w-full rounded-lg px-3 py-2 text-left text-sm hover:bg-slate-100 dark:hover:bg-slate-800"
                    onClick={() => void aplicar({ adicionar: [a.id] })}
                  >
                    {a.nome}
                  </button>
                </li>
              ))}
            </ul>
          </>
        )}

        <div className="mt-5 flex justify-end">
          <Button type="button" variant="secondary" onClick={onClose}>
            Fechar
          </Button>
        </div>
      </div>
    </div>
  )
}
