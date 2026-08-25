import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  empresas,
  setores,
  whatsappChats,
  type Empresas,
  type Setores,
  type WhatsappChats,
} from '../../api/client'
import { coletarTodasPaginas } from '../../api/collectPages'
import { TicketBuscaPicker } from '../../components/TicketBuscaPicker'
import {
  TicketClassificacaoFields,
  type ClassificacaoFormValue,
} from '../../components/tickets/TicketClassificacaoFields'
import { Card } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { Select } from '../../components/ui/Select'
import { SelectComPesquisa } from '../../components/ui/SelectComPesquisa'
import { useToast } from '../../components/ui/Toast'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { exibirProtocolo } from '../../lib/exibirProtocolo'
import { marcarTicketAtivo, TICKETS_PATH } from '../../lib/ticketAtivo'

type Modo = 'vincular' | 'abrir'

type Props = {
  chat: WhatsappChats.Chat
  open: boolean
  onClose: () => void
  onSuccess: (chat: WhatsappChats.Chat) => void
}

export function WhatsappTicketsModal({ chat, open, onClose, onSuccess }: Props) {
  const toast = useToast()
  const [modo, setModo] = useState<Modo>('vincular')
  const [salvando, setSalvando] = useState(false)

  const [empresasList, setEmpresasList] = useState<Empresas.EmpresaListaItem[]>([])
  const [setoresList, setSetoresList] = useState<Setores.Setor[]>([])
  const [catalogoLoading, setCatalogoLoading] = useState(false)

  const [empresaId, setEmpresaId] = useState<number | ''>('')
  const [setorId, setSetorId] = useState<number | ''>(chat.setor_id ?? '')
  const [assunto, setAssunto] = useState('')
  const [descricao, setDescricao] = useState('')
  const [classificacao, setClassificacao] = useState<ClassificacaoFormValue>({
    naturezaId: '',
    motivoId: '',
    motivoOutroTexto: '',
  })

  const empresaItems = useMemo(
    () => empresasList.map((e) => ({ id: e.id, label: e.nome })),
    [empresasList],
  )

  const setoresAtivos = useMemo(
    () => [...setoresList.filter((s) => s.ativo)].sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR')),
    [setoresList],
  )

  useEffect(() => {
    if (!open) return
    setModo('vincular')
    setAssunto(`Atendimento WhatsApp — ${chat.cliente_nome?.trim() || chat.wa_id}`)
    setDescricao('')
    setClassificacao({ naturezaId: '', motivoId: '', motivoOutroTexto: '' })
    setSetorId(chat.setor_id ?? '')
    setEmpresaId('')
    setCatalogoLoading(true)
    Promise.all([
      coletarTodasPaginas<Empresas.EmpresaListaItem>((o, l) => empresas.list({ offset: o, limit: l })),
      coletarTodasPaginas<Setores.Setor>((o, l) => setores.list({ incluir_inativos: true, offset: o, limit: l })),
    ])
      .then(([emps, sets]) => {
        setEmpresasList(emps)
        setSetoresList(sets)
      })
      .catch((err) => {
        toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível carregar empresas e setores.'))
      })
      .finally(() => setCatalogoLoading(false))
  }, [chat.cliente_nome, chat.setor_id, chat.wa_id, open, toast])

  if (!open) return null

  async function vincular(ticketId: number) {
    setSalvando(true)
    try {
      const atualizado = await whatsappChats.vincularTicket(chat.id, ticketId)
      toast.showSuccess('Ticket vinculado ao chat.')
      onSuccess(atualizado)
      onClose()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível vincular o ticket.'))
    } finally {
      setSalvando(false)
    }
  }

  async function abrir() {
    if (empresaId === '' || setorId === '' || !assunto.trim()) {
      toast.showWarning('Preencha empresa, setor e assunto.')
      return
    }
    if (classificacao.naturezaId === '') {
      toast.showWarning('Selecione a natureza da demanda escalada.')
      return
    }
    setSalvando(true)
    try {
      const atualizado = await whatsappChats.abrirTicket(chat.id, {
        empresa_id: Number(empresaId),
        setor_id: Number(setorId),
        assunto: assunto.trim(),
        descricao: descricao.trim() || null,
        natureza_id: Number(classificacao.naturezaId),
        motivo_id: classificacao.motivoId === '' ? null : Number(classificacao.motivoId),
      })
      const novoId = atualizado.ticket_ids.find((tid) => !chat.ticket_ids.includes(tid))
      toast.showSuccess(
        novoId
          ? `Ticket criado e vinculado.`
          : 'Ticket criado e vinculado ao chat.',
      )
      onSuccess(atualizado)
      onClose()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível abrir o ticket.'))
    } finally {
      setSalvando(false)
    }
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-end justify-center bg-slate-900/50 p-0 backdrop-blur-sm md:items-center md:p-4">
      <Card className="flex max-h-[min(92dvh,var(--vv-height,92dvh))] w-full max-w-lg flex-col overflow-hidden rounded-b-none p-0 animate-in zoom-in-95 md:rounded-2xl">
        <div className="border-b border-slate-100 px-6 py-4 dark:border-slate-800">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">Tickets</h3>
              <p className="mt-1 text-sm text-slate-500">
                Chat {exibirProtocolo(chat.protocolo)} · vincule ou abra um chamado
              </p>
            </div>
            <button
              type="button"
              className="text-2xl leading-none text-slate-400 hover:text-slate-700 dark:hover:text-slate-200"
              onClick={onClose}
              aria-label="Fechar"
            >
              &times;
            </button>
          </div>

          {chat.ticket_ids.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {chat.ticket_ids.map((tid) => (
                <Link
                  key={tid}
                  to={TICKETS_PATH}
                  className="inline-flex rounded-full border border-cyan-200 bg-cyan-50 px-2.5 py-0.5 text-xs font-medium text-cyan-800 dark:border-cyan-800 dark:bg-cyan-950/40 dark:text-cyan-300"
                  onClick={() => {
                    marcarTicketAtivo(tid)
                    onClose()
                  }}
                >
                  Ticket #{tid}
                </Link>
              ))}
            </div>
          )}

          <div
            className="mt-4 inline-flex w-full rounded-xl bg-slate-100/90 p-1 ring-1 ring-slate-200/60 dark:bg-slate-800/60 dark:ring-slate-700/80"
            role="group"
            aria-label="Ação de ticket"
          >
            {(
              [
                { id: 'vincular' as const, label: 'Vincular existente' },
                { id: 'abrir' as const, label: 'Abrir novo' },
              ] as const
            ).map(({ id, label }) => (
              <button
                key={id}
                type="button"
                onClick={() => setModo(id)}
                className={`min-h-[2.25rem] flex-1 rounded-lg px-3 py-2 text-center text-xs font-medium transition-all sm:text-sm ${
                  modo === id
                    ? 'bg-white text-slate-900 shadow-sm ring-1 ring-slate-200/80 dark:bg-slate-700 dark:text-slate-50'
                    : 'text-slate-500 hover:text-slate-800 dark:text-slate-400'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="overflow-y-auto px-6 py-4">
          {modo === 'vincular' ? (
            <TicketBuscaPicker
              excluirIds={chat.ticket_ids}
              label="Buscar ticket em aberto"
              hint="Selecione um ticket para vincular a este chat. Protocolos de chat e ticket permanecem distintos."
              disabled={salvando}
              loadingExterno={salvando}
              onSelecionar={(t) => void vincular(t.id)}
            />
          ) : catalogoLoading ? (
            <p className="py-8 text-center text-sm text-slate-500">Carregando formulário…</p>
          ) : (
            <div className="space-y-4">
              <SelectComPesquisa
                label="Empresa"
                value={empresaId}
                onChange={(id) => setEmpresaId(id)}
                items={empresaItems}
                placeholder="Selecione a empresa"
                disabled={salvando}
                required
                menuPlacement="inline"
              />
              <Select
                label="Setor"
                value={setorId}
                onChange={(v) => setSetorId(v === '' ? '' : Number(v))}
                options={setoresAtivos.map((s) => ({ value: s.id, label: s.nome }))}
                placeholder="Selecione o setor"
                includeEmpty
                emptyLabel="Selecione o setor"
                disabled={salvando}
              />
              <Input
                label="Assunto"
                value={assunto}
                onChange={(e) => setAssunto(e.target.value)}
                disabled={salvando}
              />
              <TicketClassificacaoFields
                value={classificacao}
                onChange={setClassificacao}
                disabled={salvando}
                motivoLabel="Motivo (opcional)"
              />
              <label className="block">
                <span className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">Descrição</span>
                <textarea
                  value={descricao}
                  onChange={(e) => setDescricao(e.target.value)}
                  rows={4}
                  disabled={salvando}
                  placeholder="Detalhes do problema (opcional). O vínculo com o chat será registrado automaticamente."
                  className="w-full rounded-xl border-0 bg-white px-3 py-2 text-sm shadow-sm ring-1 ring-slate-200/90 focus:outline-none focus:ring-2 focus:ring-slate-400/35 dark:bg-slate-900/80 dark:text-slate-100 dark:ring-slate-600/90"
                />
              </label>
            </div>
          )}
        </div>

        {modo === 'abrir' && !catalogoLoading && (
          <div className="flex justify-end gap-2 border-t border-slate-100 px-6 py-4 dark:border-slate-800">
            <Button type="button" variant="cancel" onClick={onClose} disabled={salvando}>
              Cancelar
            </Button>
            <Button type="button" onClick={() => void abrir()} loading={salvando}>
              Abrir ticket
            </Button>
          </div>
        )}

        {modo === 'vincular' && (
          <div className="border-t border-slate-100 px-6 py-3 dark:border-slate-800">
            <Button type="button" variant="secondary" className="w-full sm:w-auto" onClick={onClose} disabled={salvando}>
              Fechar
            </Button>
          </div>
        )}
      </Card>
    </div>
  )
}
