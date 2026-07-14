import { useEffect, useMemo, useRef, useState } from 'react'
import { ConfirmDialog } from '../ui/ConfirmDialog'
import { Button } from '../ui/Button'
import { CheckboxField } from '../ui/CheckboxField'
import { useToast } from '../ui/Toast'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import type { ChatDemanda, ChatEncerrarApi, ChatMensagemTimeline } from '../../lib/chatDemandasApi'
import {
  analisarDemandaPosRegistro,
  chatEncerramentoPorInatividade,
  formatarHoraDemanda,
  rotuloDemanda,
} from '../../lib/whatsappDemandaUtils'
import {
  DEMANDA_FORM_VAZIO,
  WhatsappDemandaFormFields,
  demandaFormFromDemanda,
  demandaFormPayload,
  type DemandaFormValues,
} from '../../pages/whatsapp/WhatsappDemandaFormFields'

type AcaoEncerramento = 'manter' | 'editar' | 'nova' | 'registrar' | 'sem_demanda'

type Props<TChat extends { estado: string }> = {
  open: boolean
  chatId: number
  chatEstado?: string | null
  msgs: ChatMensagemTimeline[]
  api: ChatEncerrarApi<TChat>
  mensagemIntroPadrao?: string
  onClose: () => void
  onEncerrado: (chat: TChat) => void
  onDemandasChange?: () => void
}

function definirAcaoInicial(
  rows: ChatDemanda[],
  msgs: ChatMensagemTimeline[],
  encerramentoPorInatividade: boolean,
): AcaoEncerramento {
  const pos = analisarDemandaPosRegistro(rows, msgs)
  if (rows.length === 0) {
    return encerramentoPorInatividade ? 'sem_demanda' : 'registrar'
  }
  if (pos) return 'nova'
  return 'manter'
}

export function ChatEncerrarModal<TChat extends { estado: string }>({
  open,
  chatId,
  chatEstado,
  msgs,
  api,
  mensagemIntroPadrao = 'Revise as demandas desta sessão antes de finalizar.',
  onClose,
  onEncerrado,
  onDemandasChange,
}: Props<TChat>) {
  const toast = useToast()
  const [demandas, setDemandas] = useState<ChatDemanda[]>([])
  const [loadingDemandas, setLoadingDemandas] = useState(false)
  const [salvando, setSalvando] = useState(false)
  const [acao, setAcao] = useState<AcaoEncerramento>('manter')
  const [form, setForm] = useState<DemandaFormValues>(DEMANDA_FORM_VAZIO)
  const [confirmarSemDemanda, setConfirmarSemDemanda] = useState(false)
  const acaoEscolhidaRef = useRef(false)

  const encerramentoPorInatividade = useMemo(() => chatEncerramentoPorInatividade(msgs), [msgs])
  const chatJaEncerrado = chatEstado === 'encerrado' || chatEstado === 'aguardando_avaliacao'

  const posRegistro = useMemo(() => analisarDemandaPosRegistro(demandas, msgs), [demandas, msgs])

  const semDemandas = demandas.length === 0
  const demandasResolvidas = demandas.filter((d) => d.desfecho === 'resolvido_sessao')
  const demandaOpcional = encerramentoPorInatividade && semDemandas

  useEffect(() => {
    if (!open) {
      acaoEscolhidaRef.current = false
      setDemandas([])
      setLoadingDemandas(false)
      setConfirmarSemDemanda(false)
      return
    }

    let cancelled = false
    setLoadingDemandas(true)
    void api
      .listarDemandas(chatId)
      .then((rows) => {
        if (cancelled) return
        setDemandas(rows)
        if (!acaoEscolhidaRef.current) {
          setAcao(definirAcaoInicial(rows, msgs, encerramentoPorInatividade))
          setForm(DEMANDA_FORM_VAZIO)
          setConfirmarSemDemanda(false)
        }
      })
      .catch((err) => {
        if (cancelled) return
        toast.showError(mensagemFalhaParaToast(err, 'Não foi possível carregar demandas.'))
        setDemandas([])
      })
      .finally(() => {
        if (!cancelled) setLoadingDemandas(false)
      })

    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- msgs só para ação inicial
  }, [open, chatId, toast, api])

  useEffect(() => {
    if (!open || loadingDemandas || acaoEscolhidaRef.current) return
    setAcao(definirAcaoInicial(demandas, msgs, encerramentoPorInatividade))
  }, [open, loadingDemandas, demandas, msgs, encerramentoPorInatividade])

  useEffect(() => {
    if (acao === 'editar' && posRegistro) {
      setForm(demandaFormFromDemanda(posRegistro.ultimaDemanda))
    } else if (acao === 'nova' || acao === 'registrar') {
      setForm(DEMANDA_FORM_VAZIO)
    }
  }, [acao, posRegistro])

  function selecionarAcao(nova: AcaoEncerramento) {
    acaoEscolhidaRef.current = true
    setAcao(nova)
  }

  async function executarEncerramento() {
    setSalvando(true)
    try {
      if (acao === 'registrar') {
        if (form.naturezaId === '') {
          toast.showWarning('Selecione a natureza da demanda ou marque encerrar sem registar.')
          return
        }
        await api.registrarDemanda(chatId, demandaFormPayload(form))
      } else if (acao === 'sem_demanda') {
        if (!demandaOpcional && !confirmarSemDemanda) {
          toast.showWarning('Confirme que deseja encerrar sem registar demanda.')
          return
        }
      } else if (acao === 'nova') {
        if (form.naturezaId === '') {
          toast.showWarning('Selecione a natureza da nova demanda.')
          return
        }
        await api.registrarDemanda(chatId, demandaFormPayload(form))
      } else if (acao === 'editar' && posRegistro) {
        await api.atualizarDemanda(chatId, posRegistro.ultimaDemanda.id, demandaFormPayload(form))
      }

      const atualizado = await api.encerrar(chatId)
      onDemandasChange?.()
      onEncerrado(atualizado)
      onClose()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível encerrar o atendimento.'))
    } finally {
      setSalvando(false)
    }
  }

  const titulo =
    chatJaEncerrado && encerramentoPorInatividade
      ? 'Atendimento encerrado por inatividade'
      : 'Encerrar atendimento'

  let mensagemIntro = mensagemIntroPadrao

  if (demandaOpcional) {
    mensagemIntro = chatJaEncerrado
      ? 'Este atendimento foi encerrado automaticamente por inatividade do cliente. Registar demanda é opcional.'
      : 'O cliente está inativo. Pode encerrar sem registar demanda ou classificar opcionalmente.'
  } else if (semDemandas) {
    mensagemIntro =
      'Registe o motivo do atendimento antes de encerrar, ou confirme explicitamente o encerramento sem demanda.'
  } else if (posRegistro) {
    mensagemIntro =
      'Houve conversa após o último registo de demanda. Escolha se mantém, corrige ou acrescenta outra demanda.'
  }

  const mostrarForm = acao === 'registrar' || acao === 'nova' || (acao === 'editar' && posRegistro != null)

  const rotuloBotaoEncerrar =
    chatJaEncerrado && encerramentoPorInatividade ? 'Concluir' : 'Encerrar atendimento'

  return (
    <ConfirmDialog
      open={open}
      title={titulo}
      message={loadingDemandas ? 'A carregar demandas…' : mensagemIntro}
      hideActions
      onConfirm={() => {}}
      onCancel={onClose}
    >
      {!loadingDemandas && (
        <div className="space-y-4">
          {demandas.length > 0 && (
            <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-3 dark:border-slate-800 dark:bg-slate-900/40">
              <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                Demandas desta sessão ({demandas.length})
              </p>
              <ul className="mt-2 space-y-2">
                {demandas.map((d) => (
                  <li key={d.id} className="text-xs text-slate-700 dark:text-slate-200">
                    <span className="font-medium">{rotuloDemanda(d)}</span>
                    <span className="text-slate-500"> · {formatarHoraDemanda(d.created_at)}</span>
                    {d.desfecho === 'escalado_ticket' && (
                      <span className="ml-1 text-amber-600 dark:text-amber-400">(ticket)</span>
                    )}
                    {d.descricao_curta && (
                      <p className="mt-0.5 text-[11px] text-slate-500">{d.descricao_curta}</p>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {posRegistro && (
            <div className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-950 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-100">
              <p className="font-semibold">Conversa continuou após a última demanda</p>
              <p className="mt-1">
                «{rotuloDemanda(posRegistro.ultimaDemanda)}» registada às{' '}
                {formatarHoraDemanda(posRegistro.ultimaDemanda.created_at)}.
              </p>
              <p className="mt-1">
                {posRegistro.mensagensApos} mensagem(ns) depois
                {posRegistro.ultimaMensagemAt
                  ? ` (última às ${formatarHoraDemanda(posRegistro.ultimaMensagemAt)})`
                  : ''}
                .
              </p>
            </div>
          )}

          {semDemandas ? (
            <div className="space-y-3">
              {demandaOpcional ? (
                <>
                  <p className="text-xs text-slate-500">
                    Registar demanda é opcional neste encerramento por inatividade.
                  </p>
                  <label className="flex cursor-pointer items-center gap-2 text-sm">
                    <input
                      type="radio"
                      name="acao-encerrar"
                      checked={acao === 'sem_demanda'}
                      onChange={() => selecionarAcao('sem_demanda')}
                    />
                    {chatJaEncerrado ? 'Concluir sem registar demanda' : 'Encerrar sem registar demanda'}
                  </label>
                  <label className="flex cursor-pointer items-center gap-2 text-sm">
                    <input
                      type="radio"
                      name="acao-encerrar"
                      checked={acao === 'registrar'}
                      onChange={() => selecionarAcao('registrar')}
                    />
                    Registar demanda (opcional)
                  </label>
                </>
              ) : (
                <>
                  <label className="flex cursor-pointer items-center gap-2 text-sm">
                    <input
                      type="radio"
                      name="acao-encerrar"
                      checked={acao === 'registrar'}
                      onChange={() => selecionarAcao('registrar')}
                    />
                    Registar demanda e encerrar
                  </label>
                  <label className="flex cursor-pointer items-center gap-2 text-sm">
                    <input
                      type="radio"
                      name="acao-encerrar"
                      checked={acao === 'sem_demanda'}
                      onChange={() => selecionarAcao('sem_demanda')}
                    />
                    Encerrar sem registar demanda
                  </label>
                  {acao === 'sem_demanda' && (
                    <CheckboxField
                      checked={confirmarSemDemanda}
                      onChange={(e) => setConfirmarSemDemanda(e.target.checked)}
                      variant="inline"
                    >
                      Confirmo encerrar sem classificar esta sessão
                    </CheckboxField>
                  )}
                </>
              )}
            </div>
          ) : posRegistro ? (
            <div className="space-y-2 text-sm">
              <label className="flex cursor-pointer items-center gap-2">
                <input
                  type="radio"
                  name="acao-encerrar"
                  checked={acao === 'manter'}
                  onChange={() => selecionarAcao('manter')}
                />
                Manter demandas como estão
              </label>
              {demandasResolvidas.length > 0 && (
                <label className="flex cursor-pointer items-center gap-2">
                  <input
                    type="radio"
                    name="acao-encerrar"
                    checked={acao === 'editar'}
                    onChange={() => selecionarAcao('editar')}
                  />
                  Editar última demanda «{rotuloDemanda(posRegistro.ultimaDemanda)}»
                </label>
              )}
              <label className="flex cursor-pointer items-center gap-2">
                <input
                  type="radio"
                  name="acao-encerrar"
                  checked={acao === 'nova'}
                  onChange={() => selecionarAcao('nova')}
                />
                Registar nova demanda para o restante da conversa
              </label>
            </div>
          ) : (
            <p className="text-xs text-slate-500">
              As demandas registadas cobrem esta sessão. Confirme para encerrar.
            </p>
          )}

          {mostrarForm && (
            <WhatsappDemandaFormFields values={form} onChange={setForm} disabled={salvando} idPrefix="enc" />
          )}

          <div className="flex flex-col-reverse gap-2 border-t border-slate-100 pt-4 dark:border-slate-800 sm:flex-row sm:justify-end">
            <Button variant="secondary" onClick={onClose} disabled={salvando}>
              Cancelar
            </Button>
            <Button variant="danger" onClick={() => void executarEncerramento()} loading={salvando}>
              {rotuloBotaoEncerrar}
            </Button>
          </div>
        </div>
      )}
    </ConfirmDialog>
  )
}
