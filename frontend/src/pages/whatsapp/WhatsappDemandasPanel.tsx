import { useCallback, useEffect, useState } from 'react'
import { whatsappChats, type WhatsappChats } from '../../api/client'
import { Button } from '../../components/ui/Button'
import { ConfirmDialog } from '../../components/ui/ConfirmDialog'
import { useToast } from '../../components/ui/Toast'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { useAuth } from '../../contexts/AuthContext'
import { formatarHoraDemanda, rotuloDemanda } from '../../lib/whatsappDemandaUtils'
import {
  DEMANDA_FORM_VAZIO,
  WhatsappDemandaFormFields,
  demandaFormFromDemanda,
  demandaFormPayload,
  type DemandaFormValues,
} from './WhatsappDemandaFormFields'

type Props = {
  chatId: number
  podeRegistrar: boolean
  onDemandasChange?: (count: number) => void
}

const DESFECHO_ROTULO: Record<string, string> = {
  resolvido_sessao: 'Resolvido na sessão',
  escalado_ticket: 'Escalado para ticket',
}

export function WhatsappDemandasPanel({ chatId, podeRegistrar, onDemandasChange }: Props) {
  const toast = useToast()
  const { user } = useAuth()
  const [demandas, setDemandas] = useState<WhatsappChats.Demanda[]>([])
  const [loading, setLoading] = useState(true)
  const [form, setForm] = useState<DemandaFormValues>(DEMANDA_FORM_VAZIO)
  const [salvando, setSalvando] = useState(false)
  const [expandido, setExpandido] = useState(false)
  const [editandoId, setEditandoId] = useState<number | null>(null)
  const [excluirId, setExcluirId] = useState<number | null>(null)

  const carregar = useCallback(async () => {
    try {
      const rows = await whatsappChats.demandas(chatId)
      setDemandas(rows)
      onDemandasChange?.(rows.length)
    } catch {
      setDemandas([])
      onDemandasChange?.(0)
    }
  }, [chatId, onDemandasChange])

  useEffect(() => {
    setLoading(true)
    void carregar().finally(() => setLoading(false))
  }, [carregar])

  function resetFormulario() {
    setForm(DEMANDA_FORM_VAZIO)
    setEditandoId(null)
    setExpandido(false)
  }

  async function salvar() {
    if (form.naturezaId === '') {
      toast.showWarning('Selecione a natureza da demanda.')
      return
    }
    setSalvando(true)
    try {
      const payload = demandaFormPayload(form)
      if (editandoId != null) {
        const row = await whatsappChats.atualizarDemanda(chatId, editandoId, payload)
        setDemandas((prev) => prev.map((d) => (d.id === editandoId ? row : d)))
        toast.showSuccess('Demanda atualizada.')
      } else {
        const row = await whatsappChats.registrarDemanda(chatId, payload)
        setDemandas((prev) => {
          const next = [...prev, row]
          onDemandasChange?.(next.length)
          return next
        })
        toast.showSuccess('Demanda registrada.')
      }
      resetFormulario()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível salvar a demanda.'))
    } finally {
      setSalvando(false)
    }
  }

  async function confirmarExclusao() {
    if (excluirId == null) return
    try {
      await whatsappChats.excluirDemanda(chatId, excluirId)
      setDemandas((prev) => {
        const next = prev.filter((d) => d.id !== excluirId)
        onDemandasChange?.(next.length)
        return next
      })
      if (editandoId === excluirId) resetFormulario()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível excluir a demanda.'))
    } finally {
      setExcluirId(null)
    }
  }

  function iniciarEdicao(d: WhatsappChats.Demanda) {
    setEditandoId(d.id)
    setForm(demandaFormFromDemanda(d))
    setExpandido(true)
  }

  if (loading) {
    return (
      <div className="border-b border-slate-100 px-4 py-2 text-xs text-slate-400 dark:border-slate-800">
        Carregando demandas…
      </div>
    )
  }

  return (
    <>
      <div className="border-b border-slate-100 bg-slate-50/80 px-4 py-2 dark:border-slate-800 dark:bg-slate-900/40">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
              Demandas ({demandas.length})
            </span>
            {demandas.slice(0, 3).map((d) => (
              <span
                key={d.id}
                className="inline-flex max-w-[12rem] truncate rounded-full border border-slate-200 bg-white px-2 py-0.5 text-[10px] text-slate-700 dark:border-slate-800 dark:bg-slate-800 dark:text-slate-200"
                title={d.descricao_curta ?? rotuloDemanda(d)}
              >
                {d.natureza_nome}
                {d.motivo_nome ? ` · ${d.motivo_nome}` : ''}
              </span>
            ))}
            {demandas.length > 3 && (
              <span className="text-[10px] text-slate-400">+{demandas.length - 3}</span>
            )}
          </div>
          {podeRegistrar && (
            <Button
              type="button"
              variant="ghost"
              className="h-7 px-2 text-[10px]"
              onClick={() => {
                if (expandido && editandoId == null) {
                  resetFormulario()
                } else {
                  setEditandoId(null)
                  setForm(DEMANDA_FORM_VAZIO)
                  setExpandido(true)
                }
              }}
            >
              {expandido ? 'Cancelar' : '+ Registrar demanda'}
            </Button>
          )}
        </div>

        {expandido && podeRegistrar && (
          <div className="mt-2 space-y-3 rounded-xl border border-slate-200 bg-white p-3 dark:border-slate-800 dark:bg-slate-900">
            <p className="text-xs font-medium text-slate-600 dark:text-slate-300">
              {editandoId != null ? 'Editar demanda' : 'Nova demanda'}
            </p>
            <WhatsappDemandaFormFields values={form} onChange={setForm} disabled={salvando} idPrefix="panel" />
            <Button type="button" className="h-9 shrink-0" onClick={() => void salvar()} loading={salvando}>
              {editandoId != null ? 'Guardar alterações' : 'Registrar'}
            </Button>
          </div>
        )}

        {demandas.length > 0 && (
          <ul className="mt-2 space-y-1">
            {demandas.map((d) => {
              const podeAlterar =
                podeRegistrar &&
                d.desfecho === 'resolvido_sessao' &&
                (user?.role === 'admin' || (user?.id != null && d.atendente_id === user.id))
              return (
                <li
                  key={d.id}
                  className="flex items-start justify-between gap-2 rounded-lg border border-slate-100 bg-white px-2 py-1.5 text-xs dark:border-slate-800 dark:bg-slate-950/50"
                >
                  <div className="min-w-0">
                    <p className="font-medium text-slate-800 dark:text-slate-100">{rotuloDemanda(d)}</p>
                    <p className="text-[10px] text-slate-500">
                      {DESFECHO_ROTULO[d.desfecho] ?? d.desfecho}
                      {d.atendente_nome ? ` · ${d.atendente_nome}` : ''}
                      {' · '}
                      {formatarHoraDemanda(d.created_at)}
                    </p>
                    {d.descricao_curta && (
                      <p className="mt-0.5 text-[10px] text-slate-500">{d.descricao_curta}</p>
                    )}
                  </div>
                  {podeAlterar && (
                    <div className="flex shrink-0 gap-2">
                      <button
                        type="button"
                        className="text-[10px] font-medium text-cyan-600 hover:underline dark:text-cyan-400"
                        onClick={() => iniciarEdicao(d)}
                      >
                        Editar
                      </button>
                      <button
                        type="button"
                        className="text-[10px] font-medium text-red-500 hover:underline"
                        onClick={() => setExcluirId(d.id)}
                      >
                        Remover
                      </button>
                    </div>
                  )}
                </li>
              )
            })}
          </ul>
        )}
      </div>

      <ConfirmDialog
        open={excluirId != null}
        title="Remover demanda?"
        message="Este registro de demanda será eliminado desta sessão."
        confirmLabel="Remover"
        variant="danger"
        onConfirm={() => void confirmarExclusao()}
        onCancel={() => setExcluirId(null)}
      />
    </>
  )
}
