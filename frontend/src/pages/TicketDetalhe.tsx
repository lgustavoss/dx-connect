import { useState, useEffect, useMemo } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ApiError,
  tickets,
  notificacoes,
  statusTicket,
  atendentes,
  setores,
  whatsappChats,
  type StatusTicket,
  type Atendentes,
  type Setores,
  type Tickets,
  type WhatsappChats,
} from '../api/client'
import { coletarTodasPaginas } from '../api/collectPages'
import { Card } from '../components/ui/Card'
import { Select } from '../components/ui/Select'
import { Button } from '../components/ui/Button'
import { useToast } from '../components/ui/Toast'
import { useAuth } from '../contexts/AuthContext'
import { useVoltarAnterior } from '../hooks/useVoltarAnterior'
import { refetchPendenciasResumo } from '../hooks/useAlertaFilaSemResponsavel'
import { SemPermissao } from './SemPermissao'
import { interpretarFalhaCarregamento } from '../api/errorMessage'
import { CarregamentoFalhou } from '../components/ui/CarregamentoFalhou'

const ROTULO_CAMPO: Record<string, string> = {
  status_id: 'Status',
  setor_id: 'Setor',
  atendente_id: 'Responsável',
  assunto: 'Assunto',
  descricao: 'Descrição',
}

function resolverValorHistorico(
  campo: string,
  valor: string | null | undefined,
  maps: {
    status: Map<number, string>
    setor: Map<number, string>
    atendente: Map<number, string>
  },
): string {
  if (valor == null || valor === '') return '—'
  if (campo === 'status_id' || campo === 'setor_id' || campo === 'atendente_id') {
    const id = Number(valor)
    if (Number.isNaN(id)) return valor
    const m =
      campo === 'status_id' ? maps.status : campo === 'setor_id' ? maps.setor : maps.atendente
    return m.get(id) ?? `#${id}`
  }
  const t = (valor || '').trim()
  return t || '—'
}

function tituloTipoMensagem(tipo: string): string {
  if (tipo === 'abertura') return 'Solicitação inicial'
  if (tipo === 'publico') return 'Mensagem da equipe'
  if (tipo === 'interno') return 'Comentário interno'
  return tipo
}

/** Mesmo nome de setor = mesmo “setor lógico” (vários IDs no banco). */
function idsSetoresMesmoNome(setoresList: Setores.Setor[], setorId: number): Set<number> {
  const alvo = setoresList.find((x) => x.id === setorId)
  if (!alvo) return new Set([setorId])
  const nome = alvo.nome.trim().toLowerCase()
  return new Set(setoresList.filter((x) => x.nome.trim().toLowerCase() === nome).map((x) => x.id))
}

/** Duplicatas com o mesmo nome (ex.: @exemplo.org + @dxconnect.test no seed). */
function preferAtendenteParaDedup(a: Atendentes.Atendente, b: Atendentes.Atendente): Atendentes.Atendente {
  const rank = (x: Atendentes.Atendente) => {
    const e = x.email.toLowerCase()
    if (e.endsWith('@exemplo.org')) return 3
    if (e.endsWith('@email.com')) return 2
    if (e.includes('.test')) return 0
    return 1
  }
  const ra = rank(a)
  const rb = rank(b)
  if (ra !== rb) return ra > rb ? a : b
  return a.id <= b.id ? a : b
}

function dedupeAtendentesMesmoNome(
  list: Atendentes.Atendente[],
  priorizarIdAtual: number | null,
): Atendentes.Atendente[] {
  const m = new Map<string, Atendentes.Atendente>()
  for (const a of list) {
    const k = a.nome.trim().toLowerCase()
    const cur = m.get(k)
    m.set(k, cur ? preferAtendenteParaDedup(a, cur) : a)
  }
  if (priorizarIdAtual != null) {
    const alvo = list.find((x) => x.id === priorizarIdAtual)
    if (alvo) m.set(alvo.nome.trim().toLowerCase(), alvo)
  }
  return [...m.values()].sort((x, y) => x.nome.localeCompare(y.nome, 'pt-BR'))
}

export function TicketDetalhe() {
  const { id } = useParams<{ id: string }>()
  const voltarAnterior = useVoltarAnterior('/tickets')
  const toast = useToast()
  const { isAdmin, user } = useAuth()
  const [atribuindo, setAtribuindo] = useState(false)
  const [fechando, setFechando] = useState(false)

  const [loading, setLoading] = useState(true)
  const [carregamentoFalhou, setCarregamentoFalhou] = useState<{ titulo: string; detalhe?: string } | null>(null)
  const [forbidden, setForbidden] = useState(false)
  const [ticket, setTicket] = useState<Tickets.Ticket | null>(null)
  const [historico, setHistorico] = useState<Tickets.Historico[]>([])
  const [mensagens, setMensagens] = useState<Tickets.Mensagem[]>([])
  const [statusList, setStatusList] = useState<StatusTicket.Status[]>([])
  const [atendentesList, setAtendentesList] = useState<Atendentes.Atendente[]>([])
  /** Atendentes elegíveis no modal (carga direta por setor no backend). */
  const [atendentesModal, setAtendentesModal] = useState<Atendentes.Atendente[]>([])
  const [atendentesModalLoading, setAtendentesModalLoading] = useState(false)
  const [setoresList, setSetoresList] = useState<Setores.Setor[]>([])
  const [chatsWhatsapp, setChatsWhatsapp] = useState<WhatsappChats.Chat[]>([])

  const [editSetor, setEditSetor] = useState<number | ''>('')
  const [editStatus, setEditStatus] = useState<number | ''>('')
  const [editAtendente, setEditAtendente] = useState<number | ''>('')
  const [saving, setSaving] = useState(false)
  const [novaMensagemTexto, setNovaMensagemTexto] = useState('')
  const [tipoNovaMensagem, setTipoNovaMensagem] = useState<'publico' | 'interno'>('publico')
  const [enviandoMensagem, setEnviandoMensagem] = useState(false)
  const [modalGerirAberto, setModalGerirAberto] = useState(false)
  /** Qual bloco do modal recebe destaque ao abrir (chips no cabeçalho). */
  const [modalGerirFoco, setModalGerirFoco] = useState<'geral' | 'setor' | 'status' | 'atendente'>('geral')
  const [historicoAberto, setHistoricoAberto] = useState(false)

  const setoresParaSelect = useMemo(() => {
    const ativos = setoresList.filter((s) => s.ativo)
    let base = ativos
    if (ticket) {
      const cur = setoresList.find((s) => s.id === ticket.setor_id)
      if (cur && !base.some((s) => s.id === cur.id)) {
        base = [...base, cur]
      }
    }
    return [...base].sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'))
  }, [setoresList, ticket])

  /** Setor em edição no modal (ou do ticket); usado para priorizar atendentes vinculados a esse setor. */
  const setorAlvoModal = useMemo(() => {
    if (editSetor !== '' && editSetor !== undefined) return Number(editSetor)
    return ticket?.setor_id ?? null
  }, [editSetor, ticket?.setor_id])

  const opcoesResponsavelModal = useMemo(() => {
    if (!modalGerirAberto) return []
    const tid = ticket?.atendente_id
    const idN = tid != null ? Number(tid) : null

    const seen = new Set<number>()
    const opts: { value: number; label: string }[] = []

    function addOption(id: number, label: string) {
      if (seen.has(id)) return
      seen.add(id)
      opts.push({ value: id, label })
    }

    const modalUnicos = dedupeAtendentesMesmoNome(atendentesModal, idN)
    for (const a of modalUnicos) {
      addOption(a.id, `${a.nome}${!a.ativo ? ' (inativo)' : ''}`)
    }

    if (idN != null && !seen.has(idN)) {
      const a =
        atendentesModal.find((x) => x.id === idN) ?? atendentesList.find((x) => x.id === idN)
      if (a) {
        addOption(idN, `${a.nome}${!a.ativo ? ' (inativo)' : ''}`)
      } else if (ticket?.atendente_nome?.trim()) {
        addOption(idN, `${ticket.atendente_nome} (cadastro indisponível)`)
      } else {
        addOption(idN, `Atendente #${idN} (cadastro indisponível)`)
      }
    }

    return opts.sort((a, b) => a.label.localeCompare(b.label, 'pt-BR'))
  }, [modalGerirAberto, atendentesModal, atendentesList, ticket?.atendente_id, ticket?.atendente_nome])

  const statusParaSelect = useMemo(() => {
    const ativos = statusList.filter((s) => s.ativo)
    if (!ticket) return ativos
    if (ativos.some((s) => s.id === ticket.status_id)) return ativos
    return [
      ...ativos,
      {
        id: ticket.status_id,
        nome: ticket.status_nome ?? `Status #${ticket.status_id}`,
        slug: '',
        ordem: 999,
        ativo: false,
      },
    ]
  }, [statusList, ticket])

  const statusFechado = useMemo(() => {
    return statusList.find((s) => (s.slug || '').toLowerCase() === 'fechado') ?? null
  }, [statusList])

  /** Mensagem “da equipe” (público no fluxo): admin, responsável ou ticket ainda sem responsável. */
  const podeMensagemPublica = useMemo(() => {
    if (!ticket || !user) return false
    if (isAdmin) return true
    if (ticket.atendente_id == null) return true
    return ticket.atendente_id === user.id
  }, [ticket, user, isAdmin])

  const mapsHistorico = useMemo(() => {
    const status = new Map<number, string>()
    statusList.forEach((s) => status.set(s.id, s.nome))
    const setor = new Map<number, string>()
    setoresList.forEach((s) => setor.set(s.id, s.nome))
    const atendente = new Map<number, string>()
    atendentesList.forEach((a) => atendente.set(a.id, a.nome))
    if (ticket?.status_nome) status.set(ticket.status_id, ticket.status_nome)
    if (ticket?.setor_nome) setor.set(ticket.setor_id, ticket.setor_nome)
    if (ticket?.atendente_nome && ticket.atendente_id != null) {
      atendente.set(ticket.atendente_id, ticket.atendente_nome)
    }
    return { status, setor, atendente }
  }, [statusList, setoresList, atendentesList, ticket])

  useEffect(() => {
    coletarTodasPaginas<StatusTicket.Status>((o, l) =>
      statusTicket.list({ incluir_inativos: false, offset: o, limit: l }),
    )
      .then(setStatusList)
      .catch((err) => {
        const msg =
          err instanceof ApiError && err.status === 403
            ? 'Você não tem permissão para listar status de ticket.'
            : err instanceof Error
              ? err.message
              : 'Erro ao carregar status'
        toast.showWarning(msg)
        setStatusList([])
      })
    coletarTodasPaginas<Setores.Setor>((o, l) =>
      setores.list({ incluir_inativos: true, offset: o, limit: l }),
    )
      .then(setSetoresList)
      .catch((err) => {
        const msg =
          err instanceof ApiError && err.status === 403
            ? 'Você não tem permissão para listar setores.'
            : err instanceof Error
              ? err.message
              : 'Erro ao carregar setores'
        toast.showWarning(msg)
        setSetoresList([])
      })
  }, [])

  /** Só administradores podem listar atendentes; depende de `user` para não rodar antes do /me. */
  useEffect(() => {
    if (user?.role !== 'admin') {
      setAtendentesList([])
      return
    }
    let cancelled = false
    coletarTodasPaginas<Atendentes.Atendente>((o, l) =>
      atendentes.list({ incluir_inativos: true, offset: o, limit: l }),
    )
      .then((list) => {
        if (!cancelled) setAtendentesList(list)
      })
      .catch(() => {
        if (!cancelled) setAtendentesList([])
      })
    return () => {
      cancelled = true
    }
  }, [user?.id, user?.role])

  /** No modal: lista de responsáveis vem do backend por setor (join real; não depende da listagem paginada de admin). */
  useEffect(() => {
    if (!modalGerirAberto) {
      setAtendentesModal([])
      setAtendentesModalLoading(false)
      return
    }
    const sid = setorAlvoModal
    if (sid == null) {
      setAtendentesModal([])
      return
    }
    let cancelled = false
    setAtendentesModalLoading(true)
    atendentes
      .listPorSetor(sid, { incluir_inativos: true })
      .then((list) => {
        if (!cancelled) setAtendentesModal(list)
      })
      .catch(() => {
        if (!cancelled) setAtendentesModal([])
      })
      .finally(() => {
        if (!cancelled) setAtendentesModalLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [modalGerirAberto, setorAlvoModal])

  useEffect(() => {
    if (!id) {
      setLoading(false)
      return
    }
    const numId = Number(id)
    if (Number.isNaN(numId)) {
      setCarregamentoFalhou({
        titulo: 'Ticket não encontrado.',
        detalhe: 'O identificador na URL é inválido.',
      })
      setLoading(false)
      return
    }
    let cancelled = false
    setLoading(true)
    setCarregamentoFalhou(null)
    setForbidden(false)
    Promise.all([tickets.get(numId), tickets.getHistorico(numId), tickets.listMensagens(numId)])
      .then(([t, h, m]) => {
        if (cancelled) return
        setTicket(t)
        setHistorico(h)
        setMensagens(m)
        setEditSetor(t.setor_id)
        setEditStatus(t.status_id)
        setEditAtendente(t.atendente_id ?? '')
        void notificacoes
          .marcarVisto(numId)
          .then(() => refetchPendenciasResumo())
          .catch(() => {})
      })
      .catch((err) => {
        if (!cancelled) {
          if (err instanceof ApiError && err.status === 403) {
            setForbidden(true)
            toast.showWarning(err.message || 'Sem permissão para este ticket.')
            setCarregamentoFalhou(null)
            return
          }
          setTicket(null)
          setHistorico([])
          setMensagens([])
          setCarregamentoFalhou(interpretarFalhaCarregamento(err, 'Ticket não encontrado.'))
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [id])

  useEffect(() => {
    if (!ticket?.id) {
      setChatsWhatsapp([])
      return
    }
    let cancelled = false
    whatsappChats
      .porTicket(ticket.id)
      .then((rows) => {
        if (!cancelled) setChatsWhatsapp(rows)
      })
      .catch(() => {
        if (!cancelled) setChatsWhatsapp([])
      })
    return () => {
      cancelled = true
    }
  }, [ticket?.id])

  useEffect(() => {
    if (!modalGerirAberto || !ticket) return
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setModalGerirAberto(false)
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [modalGerirAberto, ticket])

  /** Ao mudar o setor no modal, responsável que não atende o novo setor some da seleção (a API limparia na gravação). */
  useEffect(() => {
    if (!modalGerirAberto || editSetor === '' || editAtendente === '' || setoresList.length === 0) return
    const grupo = idsSetoresMesmoNome(setoresList, Number(editSetor))
    const aid = Number(editAtendente)
    const fromApi = atendentesList.find((a) => a.id === aid)
    if (!fromApi) return
    if (!(fromApi.setor_ids ?? []).some((id) => grupo.has(id))) {
      setEditAtendente('')
    }
  }, [modalGerirAberto, editSetor, editAtendente, atendentesList, setoresList])

  function abrirModalGerir(foco: 'geral' | 'setor' | 'status' | 'atendente' = 'geral') {
    if (!ticket) return
    setEditSetor(ticket.setor_id)
    setEditStatus(ticket.status_id)
    setEditAtendente(ticket.atendente_id ?? '')
    setModalGerirFoco(foco)
    setModalGerirAberto(true)
  }

  const modalApenasUmCampo = modalGerirFoco !== 'geral'

  async function handleSalvar() {
    if (!ticket) return
    const patch: Tickets.Update = {}
    if (editSetor !== '' && Number(editSetor) !== ticket.setor_id) patch.setor_id = Number(editSetor)
    if (editStatus !== '' && Number(editStatus) !== ticket.status_id) patch.status_id = Number(editStatus)
    const atendAtual = ticket.atendente_id
    const atendNovo = editAtendente === '' ? null : Number(editAtendente)
    if (atendNovo !== atendAtual) patch.atendente_id = atendNovo

    if (Object.keys(patch).length === 0) {
      toast.showWarning('Nenhuma alteração para salvar.')
      return
    }

    setSaving(true)
    try {
      const updated = await tickets.update(ticket.id, patch)
      setTicket(updated)
      const hist = await tickets.getHistorico(ticket.id)
      setHistorico(hist)
      setEditSetor(updated.setor_id)
      setEditStatus(updated.status_id)
      setEditAtendente(updated.atendente_id ?? '')
      setModalGerirAberto(false)
      if (patch.setor_id != null && patch.setor_id !== ticket.setor_id) {
        toast.showSuccess('Ticket transferido e salvo.')
      } else {
        toast.showSuccess('Alterações aplicadas.')
      }
    } catch (err) {
      toast.showWarning(err instanceof Error ? err.message : 'Erro ao salvar')
    } finally {
      setSaving(false)
    }
  }

  // Se o usuário conseguiu carregar o ticket, o backend já validou o escopo de setor.
  // Aqui só bloqueamos o botão quando já existe responsável.
  const podeAtribuirAMim = !!ticket && !ticket.atendente_id && !!user

  async function handleAtribuirAMim() {
    if (!ticket || !user || !podeAtribuirAMim) return
    const emAt = statusList.find((s) => s.slug === 'em_atendimento' && s.ativo)
    const patch: Tickets.Update = { atendente_id: user.id }
    if (emAt && ticket.status_id !== emAt.id) patch.status_id = emAt.id
    setAtribuindo(true)
    try {
      const updated = await tickets.update(ticket.id, patch)
      setTicket(updated)
      const hist = await tickets.getHistorico(ticket.id)
      setHistorico(hist)
      setEditAtendente(updated.atendente_id ?? '')
      setEditStatus(updated.status_id)
      toast.showSuccess('Ticket atribuído a você.')
    } catch (err) {
      toast.showWarning(err instanceof Error ? err.message : 'Não foi possível atribuir.')
    } finally {
      setAtribuindo(false)
    }
  }

  useEffect(() => {
    if (!podeMensagemPublica && tipoNovaMensagem === 'publico') {
      setTipoNovaMensagem('interno')
    }
  }, [podeMensagemPublica, tipoNovaMensagem])

  async function handleEnviarMensagem() {
    if (!ticket) return
    if (ticket.fechado_em) {
      toast.showWarning('Ticket fechado. Apenas admin pode reabrir para enviar mensagens.')
      return
    }
    const texto = novaMensagemTexto.trim()
    if (!texto) {
      toast.showWarning('Escreva uma mensagem antes de enviar.')
      return
    }
    const tipo = podeMensagemPublica ? tipoNovaMensagem : 'interno'
    setEnviandoMensagem(true)
    try {
      await tickets.addMensagem(ticket.id, { corpo: texto, tipo })
      const m = await tickets.listMensagens(ticket.id)
      setMensagens(m)
      setNovaMensagemTexto('')
      toast.showSuccess(tipo === 'interno' ? 'Comentário interno registrado.' : 'Mensagem enviada.')
    } catch (err) {
      toast.showWarning(err instanceof Error ? err.message : 'Erro ao enviar')
    } finally {
      setEnviandoMensagem(false)
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center text-slate-500 dark:text-slate-400">
        Carregando ticket…
      </div>
    )
  }

  if (forbidden) {
    return (
      <div className="mx-auto max-w-6xl space-y-6 pb-10">
        <SemPermissao
          title="Você não tem permissão para acessar este ticket."
          detail="Este chamado pertence a um setor fora do seu escopo. Se precisar, peça ao administrador para ajustar seus vínculos de setor."
          voltarPara="/tickets"
          voltarLabel="Voltar para Tickets"
        />
      </div>
    )
  }

  if (carregamentoFalhou) {
    return (
      <CarregamentoFalhou titulo={carregamentoFalhou.titulo} detalhe={carregamentoFalhou.detalhe} onVoltar={voltarAnterior} />
    )
  }

  if (!ticket) {
    return null
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6 pb-10">
      <nav aria-label="breadcrumb" className="flex flex-wrap items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
        <button
          type="button"
          onClick={voltarAnterior}
          className="font-medium text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100"
        >
          ← Voltar
        </button>
        <span aria-hidden className="text-slate-300 dark:text-slate-600">
          /
        </span>
        <span className="font-semibold text-slate-800 dark:text-slate-100">#{ticket.protocolo}</span>
      </nav>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400 dark:text-slate-500">Assunto</p>
          <h1 className="mt-0.5 text-xl font-semibold tracking-tight text-slate-900 dark:text-slate-100 sm:text-2xl">
            {ticket.assunto}
          </h1>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
            <span className="font-medium text-slate-800 dark:text-slate-200">
              {ticket.empresa_nome ?? `Empresa #${ticket.empresa_id}`}
            </span>
          </p>
          {podeAtribuirAMim && (
            <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
              Este ticket está na fila do setor sem responsável. Atribua a você para dar andamento.
            </p>
          )}
          <div className="mt-3 flex flex-wrap gap-2" role="group" aria-label="Ações rápidas do ticket">
            <button
              type="button"
              onClick={() => {
                if (ticket.fechado_em && !isAdmin) {
                  toast.showWarning('Ticket fechado — apenas admin pode alterar.')
                  return
                }
                abrirModalGerir('setor')
              }}
              className="inline-flex max-w-full items-center gap-2 rounded-full border border-slate-200/90 bg-slate-50/80 px-3 py-1.5 text-left text-xs shadow-sm transition-colors hover:border-slate-300 hover:bg-slate-100/90 dark:border-slate-600 dark:bg-slate-800/70 dark:hover:border-slate-500 dark:hover:bg-slate-800"
            >
              <span className="shrink-0 font-medium text-slate-500 dark:text-slate-400">Setor</span>
              <span className="min-w-0 truncate font-semibold text-slate-800 dark:text-slate-100">
                {ticket.setor_nome ?? `Setor #${ticket.setor_id}`}
              </span>
            </button>
            <button
              type="button"
              onClick={() => {
                if (ticket.fechado_em && !isAdmin) {
                  toast.showWarning('Ticket fechado — apenas admin pode alterar.')
                  return
                }
                abrirModalGerir('status')
              }}
              className="inline-flex max-w-full items-center gap-2 rounded-full border border-slate-200/90 bg-slate-50/80 px-3 py-1.5 text-left text-xs shadow-sm transition-colors hover:border-slate-300 hover:bg-slate-100/90 dark:border-slate-600 dark:bg-slate-800/70 dark:hover:border-slate-500 dark:hover:bg-slate-800"
            >
              <span className="shrink-0 font-medium text-slate-500 dark:text-slate-400">Status</span>
              <span className="min-w-0 truncate font-semibold text-slate-800 dark:text-slate-100">
                {ticket.status_nome ?? String(ticket.status_id)}
              </span>
            </button>
            <button
              type="button"
              onClick={() => {
                if (ticket.fechado_em && !isAdmin) {
                  toast.showWarning('Ticket fechado — apenas admin pode alterar.')
                  return
                }
                abrirModalGerir('atendente')
              }}
              className="inline-flex max-w-full items-center gap-2 rounded-full border border-slate-200/90 bg-slate-50/80 px-3 py-1.5 text-left text-xs shadow-sm transition-colors hover:border-slate-300 hover:bg-slate-100/90 dark:border-slate-600 dark:bg-slate-800/70 dark:hover:border-slate-500 dark:hover:bg-slate-800"
            >
              <span className="shrink-0 font-medium text-slate-500 dark:text-slate-400">Responsável</span>
              <span className="min-w-0 truncate font-semibold text-slate-800 dark:text-slate-100">
                {ticket.atendente_nome ?? '—'}
              </span>
            </button>
          </div>
          <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500 dark:text-slate-400">
            <span>
              Aberto em {ticket.created_at ? new Date(ticket.created_at).toLocaleString('pt-BR') : '—'}
            </span>
            {ticket.fechado_em && (
              <span className="font-medium text-emerald-700 dark:text-emerald-400">
                Fechado em {new Date(ticket.fechado_em).toLocaleString('pt-BR')}
              </span>
            )}
          </div>
          {chatsWhatsapp.length > 0 && (
            <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-2 dark:border-slate-700 dark:bg-slate-900/40">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                Chats WhatsApp vinculados
              </p>
              <ul className="mt-2 flex flex-wrap gap-2">
                {chatsWhatsapp.map((c) => (
                  <li key={c.id}>
                    <Link
                      to={`/whatsapp/c/${c.id}`}
                      className="text-sm font-medium text-cyan-700 underline hover:text-cyan-900 dark:text-cyan-400 dark:hover:text-cyan-300"
                    >
                      {c.protocolo}
                      {c.estado === 'encerrado' ? ' (encerrado)' : ''}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          {isAdmin && ticket.fechado_em && (
            <Button
              type="button"
              onClick={async () => {
                try {
                  const updated = await tickets.reabrir(ticket.id)
                  setTicket(updated)
                  setEditStatus(updated.status_id)
                  setEditAtendente(updated.atendente_id ?? '')
                  const hist = await tickets.getHistorico(updated.id)
                  setHistorico(hist)
                  toast.showSuccess('Ticket reaberto.')
                } catch (err) {
                  toast.showWarning(err instanceof Error ? err.message : 'Não foi possível reabrir.')
                }
              }}
            >
              Reabrir
            </Button>
          )}
          {podeAtribuirAMim && !ticket.fechado_em && (
            <Button type="button" onClick={handleAtribuirAMim} loading={atribuindo}>
              Atribuir a mim
            </Button>
          )}
          {!ticket.fechado_em && (
            <Button
              type="button"
              variant="secondary"
              loading={fechando}
              onClick={async () => {
                if (!ticket) return
                if (!statusFechado) {
                  toast.showWarning('Não existe um status com slug "fechado". Cadastre/ajuste em Status de ticket.')
                  return
                }
                if (!confirm('Fechar este ticket? Ele sairá da lista de abertos e não permitirá novas mensagens.')) return
                setFechando(true)
                try {
                  const updated = await tickets.update(ticket.id, { status_id: statusFechado.id })
                  setTicket(updated)
                  setEditStatus(updated.status_id)
                  setEditAtendente(updated.atendente_id ?? '')
                  const hist = await tickets.getHistorico(updated.id)
                  setHistorico(hist)
                  toast.showSuccess('Ticket fechado.')
                  void refetchPendenciasResumo()
                } catch (err) {
                  toast.showWarning(err instanceof Error ? err.message : 'Não foi possível fechar.')
                } finally {
                  setFechando(false)
                }
              }}
            >
              Fechar ticket
            </Button>
          )}
          <Button
            type="button"
            variant="secondary"
            disabled={Boolean(ticket.fechado_em) && !isAdmin}
            onClick={() => {
              if (ticket.fechado_em && !isAdmin) {
                toast.showWarning('Ticket fechado — apenas admin pode alterar.')
                return
              }
              abrirModalGerir('geral')
            }}
          >
            Gerir ticket
          </Button>
          <Button variant="secondary" onClick={voltarAnterior}>
            Voltar
          </Button>
        </div>
      </div>

      <Card title="Conversa">
        <p className="mb-4 text-sm text-slate-500 dark:text-slate-400">
          Mensagens da equipe para o andamento; comentários internos só para atendentes.
          {!podeMensagemPublica && (
            <span className="mt-1 block text-amber-800/90 dark:text-amber-200/90">
              Você não é o responsável por este chamado: pode registrar apenas comentários internos para colaborar com o
              setor.
            </span>
          )}
        </p>
        <div className="space-y-4">
          {mensagens.length === 0 ? (
            <p className="text-sm text-slate-500 dark:text-slate-400">Nenhuma mensagem ainda.</p>
          ) : (
            <ul className="space-y-3">
              {mensagens.map((msg) => {
                const isAbertura = msg.tipo === 'abertura'
                const isInterno = msg.tipo === 'interno'
                const autor =
                  msg.atendente_nome ??
                  (isAbertura ? 'Registro legado / sistema' : '—')
                return (
                  <li
                    key={msg.id}
                    className={`rounded-xl border px-4 py-3 text-sm ${
                      isInterno
                        ? 'border-amber-200/90 bg-amber-50/60 dark:border-amber-800/50 dark:bg-amber-950/25'
                        : isAbertura
                          ? 'border border-slate-200 border-l-4 border-l-slate-500 bg-slate-50/90 dark:border-slate-600 dark:border-l-slate-400 dark:bg-slate-800/50'
                          : 'border border-slate-200/90 bg-white shadow-sm dark:border-slate-600 dark:bg-slate-800/45 dark:shadow-none'
                    }`}
                  >
                    <div
                      className={`flex flex-wrap items-center justify-between gap-2 border-b pb-2 text-xs dark:border-slate-600/80 ${
                        isInterno ? 'border-amber-200/50 dark:border-amber-800/40' : 'border-slate-200/60'
                      }`}
                    >
                      <span className="font-semibold text-slate-800 dark:text-slate-100">
                        {tituloTipoMensagem(msg.tipo)}
                      </span>
                      {isInterno && (
                        <span className="rounded-md bg-amber-100/90 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-amber-900 dark:bg-amber-900/50 dark:text-amber-100">
                          Só equipe interna
                        </span>
                      )}
                    </div>
                    <p className="mt-2 whitespace-pre-wrap text-slate-800 dark:text-slate-200">{msg.corpo}</p>
                    <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                      {autor}
                      <span className="text-slate-400 dark:text-slate-500"> · </span>
                      {new Date(msg.created_at).toLocaleString('pt-BR')}
                    </p>
                  </li>
                )
              })}
            </ul>
          )}

          <div className="border-t border-slate-200 pt-4 dark:border-slate-700/90">
            <p className="mb-2 text-sm font-medium text-slate-700 dark:text-slate-300">Nova mensagem</p>
            {ticket.fechado_em ? (
              <div className="rounded-xl border border-emerald-200 bg-emerald-50/70 px-4 py-3 text-sm text-emerald-900 dark:border-emerald-800/60 dark:bg-emerald-950/25 dark:text-emerald-100">
                Ticket fechado — não é possível enviar novas mensagens.
                {isAdmin ? (
                  <span className="mt-1 block text-xs text-emerald-800/80 dark:text-emerald-200/80">
                    Use o botão <span className="font-semibold">Reabrir</span> acima para voltar a responder.
                  </span>
                ) : (
                  <span className="mt-1 block text-xs text-emerald-800/80 dark:text-emerald-200/80">
                    Apenas um administrador pode reabrir este ticket.
                  </span>
                )}
              </div>
            ) : null}
            <div className="mb-3 inline-flex rounded-xl bg-slate-100 p-1 ring-1 ring-slate-200/80 dark:bg-slate-800/90 dark:ring-slate-600/80">
              {podeMensagemPublica && (
                <button
                  type="button"
                  onClick={() => setTipoNovaMensagem('publico')}
                  className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                    tipoNovaMensagem === 'publico'
                      ? 'bg-white text-slate-900 shadow-sm dark:bg-slate-700 dark:text-slate-100 dark:shadow-none dark:ring-1 dark:ring-slate-500/30'
                      : 'text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200'
                  }`}
                >
                  Mensagem da equipe
                </button>
              )}
              <button
                type="button"
                onClick={() => setTipoNovaMensagem('interno')}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                  tipoNovaMensagem === 'interno' || !podeMensagemPublica
                    ? 'bg-white text-amber-950 shadow-sm dark:bg-amber-950/55 dark:text-amber-100 dark:shadow-none dark:ring-1 dark:ring-amber-700/40'
                    : 'text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200'
                }`}
              >
                Comentário interno
              </button>
            </div>
            <textarea
              value={novaMensagemTexto}
              onChange={(e) => setNovaMensagemTexto(e.target.value)}
              spellCheck={false}
              rows={4}
              disabled={Boolean(ticket.fechado_em)}
              placeholder={
                tipoNovaMensagem === 'interno'
                  ? 'Anotação visível apenas para atendentes…'
                  : 'Descreva o que foi feito, testado ou o que falta…'
              }
              className="w-full rounded-xl border-0 bg-slate-50 px-3 py-2 text-sm text-slate-900 shadow-inner ring-1 ring-slate-200/90 placeholder:text-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-slate-400/35 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-slate-900/80 dark:text-slate-100 dark:ring-slate-600 dark:placeholder:text-slate-500 dark:focus:bg-slate-900 dark:focus:ring-slate-500/50"
            />
            <div className="mt-2">
              <Button type="button" onClick={handleEnviarMensagem} loading={enviandoMensagem} disabled={Boolean(ticket.fechado_em)}>
                Enviar
              </Button>
            </div>
          </div>
        </div>
      </Card>

      {historico.length > 0 && (
        <div className="rounded-xl border border-slate-200/90 bg-white shadow-sm dark:border-slate-700/80 dark:bg-slate-900/70 dark:shadow-none dark:ring-1 dark:ring-white/5">
          <button
            type="button"
            onClick={() => setHistoricoAberto((o) => !o)}
            className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50/80 dark:text-slate-200 dark:hover:bg-slate-800/60 sm:px-5"
            aria-expanded={historicoAberto}
          >
            <span>
              Histórico técnico
              <span className="ml-2 font-normal text-slate-400 dark:text-slate-500">({historico.length})</span>
            </span>
            <span className="text-slate-400 dark:text-slate-500" aria-hidden>
              {historicoAberto ? '▴' : '▾'}
            </span>
          </button>
          {historicoAberto && (
            <ul className="space-y-2 border-t border-slate-100 px-4 py-3 text-sm dark:border-slate-700/80 sm:px-5">
              {historico.map((h) => (
                <li
                  key={h.id}
                  className="rounded-lg border border-slate-100 bg-slate-50/60 px-3 py-2 dark:border-slate-700 dark:bg-slate-800/40"
                >
                  <div className="font-medium text-slate-800 dark:text-slate-100">
                    {ROTULO_CAMPO[h.campo] ?? h.campo}
                  </div>
                  <div className="mt-1 text-slate-600 dark:text-slate-300">
                    <span className="text-slate-500 dark:text-slate-400">
                      {resolverValorHistorico(h.campo, h.valor_antigo, mapsHistorico)}
                    </span>
                    <span className="mx-2 text-slate-400 dark:text-slate-500">→</span>
                    <span>{resolverValorHistorico(h.campo, h.valor_novo, mapsHistorico)}</span>
                  </div>
                  <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                    {new Date(h.created_at).toLocaleString('pt-BR')}
                    {h.atendente_nome ? ` · ${h.atendente_nome}` : ''}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {modalGerirAberto && (
        <div
          className="fixed inset-0 z-[500] flex items-end justify-center bg-slate-950/60 p-4 backdrop-blur-[2px] sm:items-center dark:bg-slate-950/70"
          role="presentation"
          onClick={() => setModalGerirAberto(false)}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="ticket-gerir-titulo"
            className="max-h-[90vh] w-full max-w-md overflow-y-auto rounded-2xl border border-slate-200 bg-white p-5 shadow-xl dark:border-slate-600 dark:bg-slate-900 dark:shadow-2xl dark:ring-1 dark:ring-white/10"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 id="ticket-gerir-titulo" className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              {modalGerirFoco === 'setor'
                ? 'Transferir de setor'
                : modalGerirFoco === 'status'
                  ? 'Alterar status'
                  : modalGerirFoco === 'atendente'
                    ? 'Transferir responsável'
                    : 'Gerir ticket'}
            </h2>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              {modalGerirFoco === 'geral' && 'Transfira de setor, altere o status ou atribua a outro atendente.'}
              {modalGerirFoco === 'setor' && 'Escolha o setor que passará a tratar este ticket.'}
              {modalGerirFoco === 'status' && 'Atualize o status conforme o andamento do atendimento.'}
              {modalGerirFoco === 'atendente' && 'Defina quem é o responsável pelo ticket (ou deixe sem responsável).'}
            </p>
            <div className="mt-5 space-y-4">
              {(modalGerirFoco === 'geral' || modalGerirFoco === 'setor') && (
                <>
                  <Select
                    label="Setor"
                    value={editSetor}
                    onChange={(v) => setEditSetor(v === '' ? '' : Number(v))}
                    options={setoresParaSelect.map((s) => ({
                      value: s.id,
                      label: `${s.nome}${!s.ativo ? ' (inativo)' : ''} · ${s.slug}`,
                    }))}
                    placeholder="Setor"
                  />
                  {!isAdmin && setoresParaSelect.length === 0 && (
                    <p className="text-xs text-amber-700 dark:text-amber-400">Nenhum setor vinculado ao seu usuário.</p>
                  )}
                </>
              )}
              {(modalGerirFoco === 'geral' || modalGerirFoco === 'status') && (
                <Select
                  label="Status"
                  value={editStatus}
                  onChange={(v) => setEditStatus(v === '' ? '' : Number(v))}
                  options={statusParaSelect.map((s) => ({
                    value: s.id,
                    label: `${s.nome}${!s.ativo ? ' (inativo)' : ''}`,
                  }))}
                  placeholder="Status"
                />
              )}
              {(modalGerirFoco === 'geral' || modalGerirFoco === 'atendente') && (
                <div>
                  <Select
                    label="Responsável"
                    value={editAtendente}
                    onChange={(v) => setEditAtendente(v === '' ? '' : Number(v))}
                    options={opcoesResponsavelModal}
                    includeEmpty
                    emptyLabel="— Nenhum —"
                    placeholder="Selecione o responsável"
                    disabled={atendentesModalLoading}
                  />
                  {atendentesModalLoading && (
                    <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Carregando atendentes do setor…</p>
                  )}
                  {!atendentesModalLoading && opcoesResponsavelModal.length === 0 && (
                    <p className="mt-1 text-xs text-amber-800 dark:text-amber-200/90">
                      Nenhum atendente vinculado a este setor. Configure vínculos em Configurações → Atendentes.
                    </p>
                  )}
                </div>
              )}
            </div>
            {(modalGerirFoco === 'geral' || modalGerirFoco === 'status') && (
              <p className="mt-4 text-xs text-slate-500 dark:text-slate-400">
                Status com slug{' '}
                <code className="rounded bg-slate-100 px-1 dark:bg-slate-800 dark:text-slate-300">fechado</code> registra a
                data de fechamento.
              </p>
            )}
            <div className="mt-6 flex flex-wrap justify-end gap-2">
              <Button type="button" variant="secondary" onClick={() => setModalGerirAberto(false)}>
                Cancelar
              </Button>
              <Button type="button" onClick={handleSalvar} loading={saving}>
                {modalApenasUmCampo ? 'Salvar' : 'Aplicar'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
