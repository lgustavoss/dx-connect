import { useRef, useState, useEffect, useMemo } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  ApiError,
  tickets,
  notificacoes,
  statusTicket,
  atendentes,
  setores,
  redes,
  empresas,
  whatsappChats,
  fetchTicketAnexoBlob,
  type StatusTicket,
  type Atendentes,
  type Setores,
  type Redes,
  type Empresas,
  type Tickets,
  type WhatsappChats,
  ticketClassificacao,
  type TicketClassificacao,
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
import { interpretarFalhaCarregamento, mensagemFalhaParaToast } from '../api/errorMessage'
import { CarregamentoFalhou } from '../components/ui/CarregamentoFalhou'
import { exibirProtocolo } from '../lib/exibirProtocolo'
import { MODAL_PANEL_COMPACT, MODAL_PANEL_SCROLLABLE } from '../lib/modalPanel'
import { autorRodapeMensagem, corpoMensagemEmailVisivel } from '../lib/ticketMensagemEmail'
import { mensagemEmFilaEmail } from '../lib/ticketMensagemEmailOutbox'
import { TicketMensagemEmailOutbox } from '../components/TicketMensagemEmailOutbox'
import { RespostasProntasPicker } from '../components/RespostasProntasPicker'
import { CheckboxField } from '../components/ui/CheckboxField'
import { TicketBuscaPicker } from '../components/TicketBuscaPicker'
import { TicketFilhosMassaPanel } from '../components/tickets/TicketFilhosMassaPanel'
import { TicketMetaChip } from '../components/tickets/TicketMetaChip'
import { TicketDetalheSkeleton } from '../components/tickets/TicketDetalheSkeleton'
import {
  TicketClassificacaoFields,
  classificacaoFromTicket,
  patchClassificacaoFromForm,
  type ClassificacaoFormValue,
} from '../components/tickets/TicketClassificacaoFields'
import {
  PRIORIDADE_OPCOES,
  rotuloPrioridade,
  type PrioridadeTicket,
} from '../lib/ticketPrioridade'

const ROTULO_CAMPO: Record<string, string> = {
  status_id: 'Status',
  setor_id: 'Setor',
  atendente_id: 'Responsável',
  empresa_id: 'Empresa',
  assunto: 'Assunto',
  descricao: 'Descrição',
  parent_ticket_id: 'Ticket pai',
  filhos_em_massa: 'Tickets filhos em massa',
  vinculo_ticket: 'Vínculo com ticket',
  prioridade: 'Prioridade',
  motivo_id: 'Motivo',
  motivo_outro_texto: 'Detalhe do motivo',
}

function resolverValorHistorico(
  campo: string,
  valor: string | null | undefined,
  maps: {
    status: Map<number, string>
    setor: Map<number, string>
    atendente: Map<number, string>
    empresa: Map<number, string>
    motivo: Map<number, string>
  },
): string {
  if (valor == null || valor === '') return '—'
  if (campo === 'prioridade') return rotuloPrioridade(valor)
  if (campo === 'motivo_outro_texto') {
    const t = (valor || '').trim()
    return t || '—'
  }
  if (campo === 'status_id' || campo === 'setor_id' || campo === 'atendente_id' || campo === 'empresa_id' || campo === 'motivo_id') {
    const id = Number(valor)
    if (Number.isNaN(id)) return valor
    const m =
      campo === 'status_id'
        ? maps.status
        : campo === 'setor_id'
          ? maps.setor
          : campo === 'empresa_id'
            ? maps.empresa
            : campo === 'motivo_id'
              ? maps.motivo
              : maps.atendente
    return m.get(id) ?? `#${id}`
  }
  const t = (valor || '').trim()
  return t || '—'
}

function tituloTipoMensagem(tipo: string): string {
  if (tipo === 'abertura') return 'Solicitação inicial'
  if (tipo === 'publico') return 'Mensagem da equipe'
  if (tipo === 'interno') return 'Comentário interno'
  if (tipo === 'email_cliente') return 'Resposta do cliente (e-mail)'
  return tipo
}

function isCorpoVazioOuNaoTexto(corpo: string | null | undefined): boolean {
  const t = (corpo ?? '').trim().toLowerCase()
  if (!t) return true
  // Placeholder usado quando o inbound não conseguiu extrair texto do e-mail.
  return (
    t === '(corpo vazio ou não texto)' ||
    t.includes('corpo vazio') ||
    t.includes('não texto') ||
    t.includes('nao texto')
  )
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
  const navigate = useNavigate()
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
  const [anexos, setAnexos] = useState<Tickets.Anexo[]>([])
  const [previewAnexo, setPreviewAnexo] = useState<{
    nome: string
    url: string
    contentType: string
  } | null>(null)
  const [previewAnexoTexto, setPreviewAnexoTexto] = useState<string | null>(null)
  const [corpoExtraidoPorMensagemId, setCorpoExtraidoPorMensagemId] = useState<Record<number, string>>({})
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
  const [editRede, setEditRede] = useState<number | ''>('')
  const [editEmpresa, setEditEmpresa] = useState<number | ''>('')
  const [editPrioridade, setEditPrioridade] = useState<PrioridadeTicket>('normal')
  const [editClassificacao, setEditClassificacao] = useState<ClassificacaoFormValue>({
    naturezaId: '',
    motivoId: '',
    motivoOutroTexto: '',
  })
  const [fecharClassificacao, setFecharClassificacao] = useState<ClassificacaoFormValue>({
    naturezaId: '',
    motivoId: '',
    motivoOutroTexto: '',
  })
  const [vinculoClassificacao, setVinculoClassificacao] = useState<ClassificacaoFormValue>({
    naturezaId: '',
    motivoId: '',
    motivoOutroTexto: '',
  })
  const [motivosHistorico, setMotivosHistorico] = useState<TicketClassificacao.Motivo[]>([])
  const [redesList, setRedesList] = useState<Redes.Rede[]>([])
  const [empresasModalList, setEmpresasModalList] = useState<Empresas.EmpresaListaItem[]>([])
  const [saving, setSaving] = useState(false)
  const [novaMensagemTexto, setNovaMensagemTexto] = useState('')
  const [tipoNovaMensagem, setTipoNovaMensagem] = useState<'publico' | 'interno'>('publico')
  const [notificarClienteEmail, setNotificarClienteEmail] = useState(false)
  const [enviandoMensagem, setEnviandoMensagem] = useState(false)
  const [anexosSelecionados, setAnexosSelecionados] = useState<File[]>([])
  const [enviandoAnexos, setEnviandoAnexos] = useState(false)
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement | null>(null)
  const [modalGerirAberto, setModalGerirAberto] = useState(false)
  const [modalFecharAberto, setModalFecharAberto] = useState(false)
  /** Qual bloco do modal recebe destaque ao abrir (chips no cabeçalho). */
  const [modalGerirFoco, setModalGerirFoco] = useState<
    'geral' | 'setor' | 'status' | 'atendente' | 'hierarquia' | 'relacionados' | 'classificacao'
  >('geral')
  const [historicoAberto, setHistoricoAberto] = useState(false)

  const [tipoVinculoRelacionado, setTipoVinculoRelacionado] = useState<Tickets.TicketVinculoTipo>('relacionado_a')
  const [fecharComoDuplicado, setFecharComoDuplicado] = useState(true)
  const [vinculandoRelacionado, setVinculandoRelacionado] = useState(false)
  const [removendoVinculoId, setRemovendoVinculoId] = useState<number | null>(null)
  const [vinculandoFilho, setVinculandoFilho] = useState(false)
  const [vinculandoPai, setVinculandoPai] = useState(false)
  const [desvinculandoHierarquia, setDesvinculandoHierarquia] = useState(false)

  const idsTicketsExcluirBusca = useMemo(() => {
    if (!ticket) return []
    const ids = new Set<number>([ticket.id])
    if (ticket.parent_ticket_id != null) ids.add(ticket.parent_ticket_id)
    for (const c of ticket.children ?? []) ids.add(c.id)
    for (const v of ticket.vinculos ?? []) ids.add(v.outro_ticket.id)
    return [...ids]
  }, [ticket])

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
  }, [modalGerirAberto, atendentesModal, atendentesList, ticket])

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

  const filhosAbertosCount = useMemo(() => {
    const ch = ticket?.children
    if (!ch?.length) return 0
    return ch.filter((c) => !c.fechado_em).length
  }, [ticket?.children])

  const temVinculosHierarquia = useMemo(() => {
    if (!ticket) return false
    const nFilhos = ticket.children?.length ?? 0
    return ticket.parent_ticket_id != null || nFilhos > 0
  }, [ticket])

  const rotuloChipHierarquia = useMemo(() => {
    if (!ticket) return '—'
    const n = ticket.children?.length ?? 0
    const temPai = ticket.parent_ticket_id != null
    if (!temPai && n === 0) return 'Sem vínculos'
    if (temPai && n === 0) return 'Com pai'
    if (!temPai && n > 0) return `${n} filho${n === 1 ? '' : 's'}`
    return `Pai + ${n} filho${n === 1 ? '' : 's'}`
  }, [ticket])

  const rotuloChipRelacionados = useMemo(() => {
    if (!ticket) return '—'
    const n = ticket.vinculos?.length ?? 0
    if (n === 0) return 'Sem vínculos'
    return `${n} relacionado${n === 1 ? '' : 's'}`
  }, [ticket])

  const podeEditarHierarquia = !!ticket && (!ticket.fechado_em || isAdmin)

  /** Mensagem “da equipe” (público no fluxo): admin, responsável ou ticket ainda sem responsável. */
  const podeMensagemPublica = useMemo(() => {
    if (!ticket || !user) return false
    if (isAdmin) return true
    if (ticket.atendente_id == null) return true
    return ticket.atendente_id === user.id
  }, [ticket, user, isAdmin])

  const temMensagemEmailNaFila = useMemo(
    () => mensagens.some((m) => mensagemEmFilaEmail(m.status)),
    [mensagens],
  )

  useEffect(() => {
    if (!ticket || !temMensagemEmailNaFila) return
    let cancelled = false
    const poll = () => {
      tickets
        .listMensagens(ticket.id)
        .then((m) => {
          if (!cancelled) setMensagens(m)
        })
        .catch(() => {})
    }
    const id = window.setInterval(poll, 5000)
    return () => {
      cancelled = true
      window.clearInterval(id)
    }
  }, [ticket?.id, temMensagemEmailNaFila])

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
    const empresa = new Map<number, string>()
    empresasModalList.forEach((e) => empresa.set(e.id, e.nome))
    if (ticket?.empresa_nome && ticket.empresa_id != null) {
      empresa.set(ticket.empresa_id, ticket.empresa_nome)
    }
    const motivo = new Map<number, string>()
    motivosHistorico.forEach((m) => motivo.set(m.id, m.nome))
    if (ticket?.motivo_nome && ticket.motivo_id != null) {
      motivo.set(ticket.motivo_id, ticket.motivo_nome)
    }
    return { status, setor, atendente, empresa, motivo }
  }, [statusList, setoresList, atendentesList, empresasModalList, motivosHistorico, ticket])

  useEffect(() => {
    coletarTodasPaginas<TicketClassificacao.Motivo>((o, l) =>
      ticketClassificacao.listMotivos({ incluir_inativos: true, offset: o, limit: l }),
    )
      .then(setMotivosHistorico)
      .catch(() => setMotivosHistorico([]))
  }, [])

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
    Promise.all([tickets.get(numId), tickets.getHistorico(numId), tickets.listMensagens(numId), tickets.anexosList(numId)])
      .then(([t, h, m, a]) => {
        if (cancelled) return
        setTicket(t)
        setHistorico(h)
        setMensagens(m)
        setAnexos(a)
        setEditSetor(t.setor_id)
        setEditStatus(t.status_id)
        setEditAtendente(t.atendente_id ?? '')
        setEditPrioridade((t.prioridade as PrioridadeTicket) ?? 'normal')
        const classificacao = classificacaoFromTicket(t)
        setEditClassificacao(classificacao)
        setFecharClassificacao(classificacao)
        setVinculoClassificacao(classificacao)
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
          setAnexos([])
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

  async function baixarOuVisualizarAnexo(a: Tickets.Anexo) {
    if (!ticket) return
    try {
      const blob = await fetchTicketAnexoBlob(ticket.id, a.id)
      const fixed = new Blob([blob], { type: a.content_type || 'application/octet-stream' })
      const url = URL.createObjectURL(fixed)
      const viewable = Boolean(
        a.content_type?.startsWith('image/') ||
          a.content_type === 'application/pdf' ||
          a.content_type?.startsWith('text/'),
      )
      if (viewable) {
        // Evita abrir `blob:` em nova aba (pode disparar search/popup blockers). Pré-visualiza no app.
        setPreviewAnexo({
          nome: a.nome_original || `anexo-${a.id}`,
          url,
          contentType: a.content_type || 'application/octet-stream',
        })
        setPreviewAnexoTexto(null)
        if (a.content_type?.startsWith('text/')) {
          try {
            const text = await fixed.text()
            setPreviewAnexoTexto(text)
          } catch {
            setPreviewAnexoTexto(null)
          }
        }
        return
      }
      const link = document.createElement('a')
      link.href = url
      link.download = a.nome_original || `anexo-${a.id}`
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(url)
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível baixar o anexo.'))
    }
  }

  useEffect(() => {
    if (!ticket?.id) return
    if (mensagens.length === 0 || anexos.length === 0) return
    const ticketId = ticket.id
    let cancelled = false

    async function run() {
      const updates: Array<{ msgId: number; text: string }> = []
      for (const msg of mensagens) {
        if (!isCorpoVazioOuNaoTexto(msg.corpo)) continue
        if (corpoExtraidoPorMensagemId[msg.id]) continue
        const anexosDaMsg = anexos.filter((a) => a.mensagem_id === msg.id)
        if (anexosDaMsg.length === 0) continue
        const candidato =
          anexosDaMsg.find((a) => (a.content_type || '').toLowerCase().startsWith('text/plain')) ||
          anexosDaMsg.find((a) => (a.content_type || '').toLowerCase().startsWith('text/html')) ||
          anexosDaMsg.find((a) => (a.content_type || '').toLowerCase().startsWith('text/'))
        if (!candidato) continue
        try {
          const b = await fetchTicketAnexoBlob(ticketId, candidato.id)
          const fixed = new Blob([b], { type: candidato.content_type || 'text/plain' })
          const raw = await fixed.text()
          const ct = (candidato.content_type || '').toLowerCase()
          const extracted =
            ct.startsWith('text/html') && typeof DOMParser !== 'undefined'
              ? (() => {
                  try {
                    const doc = new DOMParser().parseFromString(raw, 'text/html')
                    const text = (doc.body?.innerText ?? '').trim()
                    return text || raw.trim()
                  } catch {
                    return raw.trim()
                  }
                })()
              : raw.trim()
          if (extracted) updates.push({ msgId: msg.id, text: extracted })
        } catch {
          // ignora: mantém placeholder
        }
      }
      if (cancelled) return
      if (updates.length === 0) return
      setCorpoExtraidoPorMensagemId((cur) => {
        const next = { ...cur }
        for (const u of updates) next[u.msgId] = u.text
        return next
      })
    }

    void run()
    return () => {
      cancelled = true
    }
  }, [ticket?.id, mensagens, anexos, corpoExtraidoPorMensagemId])

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

  function abrirModalGerir(
    foco: 'geral' | 'setor' | 'status' | 'atendente' | 'hierarquia' | 'relacionados' | 'classificacao' = 'geral',
  ) {
    if (!ticket) return
    setEditSetor(ticket.setor_id)
    setEditStatus(ticket.status_id)
    setEditAtendente(ticket.atendente_id ?? '')
    setEditRede(ticket.rede_id ?? '')
    setEditEmpresa(ticket.empresa_id ?? '')
    setEditPrioridade((ticket.prioridade as PrioridadeTicket) ?? 'normal')
    setEditClassificacao(classificacaoFromTicket(ticket))
    setModalGerirFoco(foco)
    setModalGerirAberto(true)
  }

  useEffect(() => {
    if (!modalGerirAberto) return
    coletarTodasPaginas<Redes.Rede>((o, l) => redes.list({ incluir_inativos: true, offset: o, limit: l }))
      .then(setRedesList)
      .catch(() => setRedesList([]))
  }, [modalGerirAberto])

  const triagemInbound = ticket?.triagem_inbound
  const empresasVinculoSugeridas = triagemInbound?.empresas_vinculo_sugeridas ?? []
  const requerCadastroFuncionario = triagemInbound?.requer_cadastro_funcionario === true
  const redeTriagemFixa = empresasVinculoSugeridas.length > 0 && ticket?.rede_id != null

  const empresasOpcoesModal = useMemo(() => {
    if (empresasVinculoSugeridas.length > 0) {
      return empresasVinculoSugeridas.map((e) => ({ id: e.id, nome: e.nome, ativo: true, rede_id: ticket?.rede_id ?? 0 }))
    }
    return empresasModalList
  }, [empresasVinculoSugeridas, empresasModalList, ticket?.rede_id])

  const linkCadastroFuncionario = useMemo(() => {
    const em = triagemInbound?.remetente_email?.trim()
    if (!em) return '/funcionarios-rede/novo'
    return `/funcionarios-rede/novo?email=${encodeURIComponent(em)}`
  }, [triagemInbound?.remetente_email])

  useEffect(() => {
    if (!modalGerirAberto) return
    if (empresasVinculoSugeridas.length > 0) return
    if (editRede === '') {
      setEmpresasModalList([])
      return
    }
    coletarTodasPaginas<Empresas.EmpresaListaItem>((o, l) =>
      empresas.list({ rede_id: Number(editRede), incluir_inativos: true, offset: o, limit: l }),
    )
      .then((list) => {
        setEmpresasModalList(list)
        if (editEmpresa !== '' && !list.some((e) => e.id === editEmpresa)) {
          setEditEmpresa('')
        }
      })
      .catch(() => setEmpresasModalList([]))
  }, [modalGerirAberto, editRede, editEmpresa, empresasVinculoSugeridas.length])

  const modalApenasUmCampo =
    modalGerirFoco !== 'geral' &&
    modalGerirFoco !== 'hierarquia' &&
    modalGerirFoco !== 'relacionados' &&
    modalGerirFoco !== 'classificacao'

  async function handleSalvar() {
    if (!ticket) return
    const patch: Tickets.Update = {}
    if (editSetor !== '' && Number(editSetor) !== ticket.setor_id) patch.setor_id = Number(editSetor)
    if (editStatus !== '' && Number(editStatus) !== ticket.status_id) patch.status_id = Number(editStatus)
    const atendAtual = ticket.atendente_id
    const atendNovo = editAtendente === '' ? null : Number(editAtendente)
    if (atendNovo !== atendAtual) patch.atendente_id = atendNovo
    if (modalGerirFoco === 'geral' && editEmpresa !== '') {
      const novoEmpresa = Number(editEmpresa)
      if (novoEmpresa !== ticket.empresa_id) patch.empresa_id = novoEmpresa
    }
    if (
      (modalGerirFoco === 'geral' || modalGerirFoco === 'classificacao') &&
      editPrioridade !== (ticket.prioridade ?? 'normal')
    ) {
      patch.prioridade = editPrioridade
    }
    if (modalGerirFoco === 'geral' || modalGerirFoco === 'classificacao') {
      const classPatch = patchClassificacaoFromForm(editClassificacao)
      const atualMotivo = ticket.motivo_id ?? null
      const novoMotivo = classPatch?.motivo_id ?? null
      const outroAtual = ticket.motivo_outro_texto ?? ''
      const outroNovo = classPatch?.motivo_outro_texto ?? ''
      if (classPatch && (novoMotivo !== atualMotivo || outroNovo !== outroAtual)) {
        patch.motivo_id = classPatch.motivo_id
        patch.motivo_outro_texto = classPatch.motivo_outro_texto ?? null
      }
    }

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
      toast.showWarning(mensagemFalhaParaToast(err, 'Erro ao salvar.'))
    } finally {
      setSaving(false)
    }
  }

  async function fecharTicketConfirmado() {
    if (!ticket) return
    if (!statusFechado) {
      toast.showWarning('Não existe um status com slug "fechado". Cadastre/ajuste em Status de ticket.')
      return
    }
    const classPatch = patchClassificacaoFromForm(fecharClassificacao)
    if (!classPatch && !ticket.motivo_id) {
      toast.showWarning('Informe natureza e motivo para encerrar o ticket.')
      return
    }
    setFechando(true)
    try {
      const updated = await tickets.update(ticket.id, {
        status_id: statusFechado.id,
        ...(classPatch ?? {}),
      })
      setTicket(updated)
      setEditStatus(updated.status_id)
      setEditAtendente(updated.atendente_id ?? '')
      const hist = await tickets.getHistorico(updated.id)
      setHistorico(hist)
      toast.showSuccess('Ticket fechado.')
      void refetchPendenciasResumo()
      setModalFecharAberto(false)
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível fechar.'))
    } finally {
      setFechando(false)
    }
  }

  async function handleVincularFilhoExistente(alvo: Tickets.Ticket) {
    if (!ticket || alvo.id === ticket.id) return
    setVinculandoFilho(true)
    try {
      await tickets.update(alvo.id, { parent_ticket_id: ticket.id })
      const atualizado = await tickets.get(ticket.id)
      setTicket(atualizado)
      toast.showSuccess(`Ticket ${exibirProtocolo(alvo.protocolo)} vinculado como filho.`)
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível vincular o ticket.'))
    } finally {
      setVinculandoFilho(false)
    }
  }

  async function handleVincularAoPai(alvo: Tickets.Ticket) {
    if (!ticket || alvo.id === ticket.id) return
    setVinculandoPai(true)
    try {
      const atualizado = await tickets.update(ticket.id, { parent_ticket_id: alvo.id })
      setTicket(atualizado)
      toast.showSuccess(`Vinculado ao ticket ${exibirProtocolo(alvo.protocolo)}.`)
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível vincular ao ticket pai.'))
    } finally {
      setVinculandoPai(false)
    }
  }

  async function recarregarTicketAtual() {
    if (!ticket) return
    const atualizado = await tickets.get(ticket.id)
    setTicket(atualizado)
  }

  async function handleDesvincularDoPai() {
    if (!ticket?.parent_ticket_id) return
    setDesvinculandoHierarquia(true)
    try {
      const atualizado = await tickets.update(ticket.id, { parent_ticket_id: null })
      setTicket(atualizado)
      toast.showSuccess('Vínculo com o ticket pai removido.')
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível desvincular do pai.'))
    } finally {
      setDesvinculandoHierarquia(false)
    }
  }

  async function handleDesvincularFilho(childId: number) {
    if (!ticket) return
    setDesvinculandoHierarquia(true)
    try {
      await tickets.update(childId, { parent_ticket_id: null })
      const atualizado = await tickets.get(ticket.id)
      setTicket(atualizado)
      toast.showSuccess('Filho desvinculado.')
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível desvincular o filho.'))
    } finally {
      setDesvinculandoHierarquia(false)
    }
  }

  async function handleAdicionarVinculoRelacionado(alvo: Tickets.Ticket) {
    if (!ticket || alvo.id === ticket.id) return
    setVinculandoRelacionado(true)
    try {
      const fechar =
        tipoVinculoRelacionado === 'duplicado_de' ? fecharComoDuplicado : false
      const classPatch =
        fechar && !ticket.fechado_em ? patchClassificacaoFromForm(vinculoClassificacao) : null
      if (fechar && !ticket.fechado_em && !classPatch && !ticket.motivo_id) {
        toast.showWarning('Informe natureza e motivo para encerrar o ticket duplicado.')
        return
      }
      const resultado = await tickets.addVinculo(ticket.id, {
        related_ticket_id: alvo.id,
        tipo: tipoVinculoRelacionado,
        fechar_como_duplicado: fechar,
        ...(classPatch ?? {}),
      })
      const [atualizado, mensagensAtualizadas, historicoAtualizado] = await Promise.all([
        tickets.get(ticket.id),
        tickets.listMensagens(ticket.id),
        tickets.getHistorico(ticket.id),
      ])
      setTicket(atualizado)
      setMensagens(mensagensAtualizadas)
      setHistorico(historicoAtualizado)
      setEditStatus(atualizado.status_id)
      if (resultado.duplicado_fechado) {
        void refetchPendenciasResumo()
        toast.showSuccess(
          `Ticket fechado como duplicado de ${exibirProtocolo(alvo.protocolo)}. O atendimento continua no original.`,
        )
        setModalGerirAberto(false)
      } else if (tipoVinculoRelacionado === 'duplicado_de') {
        toast.showSuccess(`Vínculo de duplicado com ${exibirProtocolo(alvo.protocolo)} registrado (ticket mantido aberto).`)
      } else {
        toast.showSuccess(`Vínculo com ${exibirProtocolo(alvo.protocolo)} adicionado.`)
      }
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível adicionar o vínculo.'))
    } finally {
      setVinculandoRelacionado(false)
    }
  }

  async function handleRemoverVinculoRelacionado(vinculoId: number) {
    if (!ticket) return
    setRemovendoVinculoId(vinculoId)
    try {
      await tickets.removeVinculo(ticket.id, vinculoId)
      const atualizado = await tickets.get(ticket.id)
      setTicket(atualizado)
      toast.showSuccess('Vínculo removido.')
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível remover o vínculo.'))
    } finally {
      setRemovendoVinculoId(null)
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
    if (!ticket || !user) return
    // Regra de UX:
    // - Se o ticket está atribuído a mim → default "publico"
    // - Caso contrário → default "interno" (evita enviar mensagem pública sem querer)
    if (ticket.atendente_id != null && ticket.atendente_id === user.id) {
      setTipoNovaMensagem('publico')
      return
    }
    setTipoNovaMensagem('interno')
  }, [ticket?.id, ticket?.atendente_id, user?.id])

  useEffect(() => {
    if (tipoNovaMensagem === 'interno') setNotificarClienteEmail(false)
  }, [tipoNovaMensagem])

  async function handleEnviarMensagem() {
    if (!ticket) return
    if (ticket.fechado_em) {
      toast.showWarning('Ticket fechado. Apenas admin pode reabrir para enviar mensagens.')
      return
    }
    const texto = novaMensagemTexto.trim()
    if (!texto && anexosSelecionados.length === 0) {
      toast.showWarning('Escreva uma mensagem ou selecione anexos.')
      return
    }
    const tipo = podeMensagemPublica ? tipoNovaMensagem : 'interno'
    setEnviandoMensagem(true)
    try {
      const payload: Tickets.MensagemCreate = { corpo: texto, tipo }
      if (tipo === 'publico' && notificarClienteEmail) {
        payload.notificar_cliente_por_email = true
      }
      const msg = texto ? await tickets.addMensagem(ticket.id, payload) : null
      if (anexosSelecionados.length > 0) {
        setEnviandoAnexos(true)
        try {
          for (const f of anexosSelecionados) {
            await tickets.uploadAnexo(ticket.id, f, msg?.id ?? null)
          }
        } finally {
          setEnviandoAnexos(false)
        }
      }
      const m = await tickets.listMensagens(ticket.id)
      setMensagens(m)
      const a = await tickets.anexosList(ticket.id)
      setAnexos(a)
      setNovaMensagemTexto('')
      setAnexosSelecionados([])
      setNotificarClienteEmail(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
      if (tipo === 'interno') {
        toast.showSuccess('Comentário interno registrado.')
      } else if (msg?.status === 'pendente_envio') {
        toast.showSuccess(
          'Mensagem registada. O e-mail ao cliente será enviado em breve — pode editar ou cancelar antes do envio.',
        )
      } else if (msg?.cliente_notificado_por_email) {
        toast.showSuccess('Mensagem registada e cliente notificado por e-mail.')
      } else {
        toast.showSuccess('Mensagem enviada.')
      }
    } catch (err) {
      toast.showWarning(err instanceof Error ? err.message : 'Erro ao enviar')
    } finally {
      setEnviandoMensagem(false)
    }
  }

  function handlePasteNoCampoMensagem(e: React.ClipboardEvent<HTMLTextAreaElement>) {
    const items = Array.from(e.clipboardData?.items ?? [])
    const files = items
      .filter((i) => i.kind === 'file')
      .map((i) => i.getAsFile())
      .filter((f): f is File => Boolean(f))

    if (files.length === 0) return

    // Evita colar binário como texto; transforma em anexos e deixa um marcador no texto.
    e.preventDefault()

    setAnexosSelecionados((cur) => [...cur, ...files])

    const ta = textareaRef.current
    if (!ta) return
    const start = ta.selectionStart ?? novaMensagemTexto.length
    const end = ta.selectionEnd ?? novaMensagemTexto.length
    const markers = files
      .map((f) => `[Anexo: ${(f.name || 'imagem').trim() || 'imagem'}]`)
      .join('\n')
    const insert = (novaMensagemTexto ? '\n' : '') + markers + '\n'
    const next = novaMensagemTexto.slice(0, start) + insert + novaMensagemTexto.slice(end)
    setNovaMensagemTexto(next)
    // Move cursor para depois dos marcadores (próximo tick do React).
    setTimeout(() => {
      try {
        const pos = start + insert.length
        ta.setSelectionRange(pos, pos)
      } catch {
        // noop
      }
    }, 0)
  }

  function inserirRespostaPronta(texto: string) {
    const ta = textareaRef.current
    const start = ta?.selectionStart ?? novaMensagemTexto.length
    const end = ta?.selectionEnd ?? novaMensagemTexto.length
    const sep = novaMensagemTexto && !novaMensagemTexto.endsWith('\n') ? '\n\n' : novaMensagemTexto ? '' : ''
    const insert = sep + texto
    const next = novaMensagemTexto.slice(0, start) + insert + novaMensagemTexto.slice(end)
    setNovaMensagemTexto(next)
    setTimeout(() => {
      try {
        const pos = start + insert.length
        ta?.setSelectionRange(pos, pos)
        ta?.focus()
      } catch {
        // noop
      }
    }, 0)
  }

  if (loading) {
    return <TicketDetalheSkeleton />
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

  const ticketAtual = ticket

  function tentarEditarTicket(acao: () => void) {
    if (ticketAtual.fechado_em && !isAdmin) {
      toast.showWarning('Ticket fechado — apenas admin pode alterar.')
      return
    }
    acao()
  }

  const dataAberturaCurta = ticket.created_at
    ? new Date(ticket.created_at).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' })
    : '—'

  const classeBtnAcao = 'h-9 w-full px-3 text-xs lg:w-auto sm:h-auto sm:text-sm'

  const linkVoltar = (
    <button
      type="button"
      onClick={voltarAnterior}
      className="-ml-1 mb-2 inline-flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-sm font-medium text-slate-600 transition-colors hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800/80 dark:hover:text-slate-100"
      aria-label="Voltar"
    >
      <span aria-hidden className="text-base leading-none">
        ←
      </span>
      Voltar
    </button>
  )

  const botoesAcaoTicket = (
    <>
      {isAdmin && ticket.fechado_em && (
        <Button
          type="button"
          variant="secondary"
          className={`${classeBtnAcao} border border-emerald-200 bg-emerald-50 text-emerald-900 hover:bg-emerald-100 dark:border-emerald-800/60 dark:bg-emerald-950/40 dark:text-emerald-100 dark:hover:bg-emerald-950/60`}
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
              if (err instanceof ApiError && err.status === 404) {
                toast.showWarning(
                  'Função de reabrir indisponível no servidor. Atualize a página ou contate o suporte.',
                )
                return
              }
              toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível reabrir.'))
            }
          }}
        >
          Reabrir
        </Button>
      )}
      {podeAtribuirAMim && !ticket.fechado_em && (
        <Button
          type="button"
          className={classeBtnAcao}
          onClick={handleAtribuirAMim}
          loading={atribuindo}
        >
          Atribuir a mim
        </Button>
      )}
      <Button
        type="button"
        variant="secondary"
        className={`${classeBtnAcao} border border-cyan-200/90 bg-cyan-50/90 text-cyan-950 hover:bg-cyan-100 dark:border-cyan-800/70 dark:bg-cyan-950/45 dark:text-cyan-100 dark:hover:bg-cyan-950/70`}
        disabled={Boolean(ticket.fechado_em) && !isAdmin}
        onClick={() => tentarEditarTicket(() => abrirModalGerir('geral'))}
      >
        Gerir
      </Button>
      {!ticket.fechado_em && (
        <>
          <span
            className="hidden h-7 w-px shrink-0 bg-slate-200 dark:bg-slate-700 sm:inline-block"
            aria-hidden
          />
          <Button
            type="button"
            variant="danger"
            className={classeBtnAcao}
            loading={fechando}
            onClick={() => {
              if (!statusFechado) {
                toast.showWarning('Não existe um status com slug "fechado". Cadastre/ajuste em Status de ticket.')
                return
              }
              setModalFecharAberto(true)
            }}
          >
            Fechar
          </Button>
        </>
      )}
    </>
  )

  const barraAcoesDesktop = (
    <div className="hidden shrink-0 items-center gap-2 lg:flex">{botoesAcaoTicket}</div>
  )

  return (
    <>
      <div className="-m-4 flex h-full min-h-0 flex-col overflow-hidden md:-m-6">
        <div className="relative z-20 shrink-0 border-b border-slate-200/70 bg-white shadow-sm dark:border-slate-700/70 dark:bg-slate-950 sm:rounded-b-2xl sm:border sm:border-t-0">
          <div className="mx-auto max-w-6xl px-3 py-2.5 sm:px-5 sm:py-4 lg:py-5">
            {linkVoltar}

            <div className="flex items-start justify-between gap-3 lg:items-center">
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1.5">
                  <span
                    className="font-mono text-xs font-bold tracking-tight text-cyan-800 sm:text-sm lg:text-lg xl:text-xl dark:text-cyan-300"
                    title={exibirProtocolo(ticket.protocolo)}
                  >
                    {exibirProtocolo(ticket.protocolo)}
                  </span>
                  {ticket.fechado_em ? (
                    <span className="inline-flex shrink-0 rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold uppercase text-emerald-800 lg:text-xs dark:bg-emerald-950/50 dark:text-emerald-200">
                      Fechado
                    </span>
                  ) : null}
                </div>
              </div>
              {barraAcoesDesktop}
            </div>

            <h1 className="mt-1.5 line-clamp-2 text-sm font-semibold leading-snug text-slate-900 sm:mt-2 sm:text-base md:text-lg lg:line-clamp-3 lg:text-xl dark:text-slate-100">
              {ticket.assunto}
            </h1>

            {(ticket.coordenacao_rede || (!ticket.empresa_id && ticket.rede_id)) && (
              <span className="mt-1 inline-flex rounded-md bg-violet-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-violet-800 sm:text-[11px] dark:bg-violet-950/50 dark:text-violet-200">
                Coordenação de rede
              </span>
            )}

            {(ticket.empresa_nome || ticket.rede_nome) && (
              <p className="mt-1 truncate text-[11px] text-slate-600 sm:text-xs md:text-sm dark:text-slate-400">
                {ticket.rede_nome &&
                  (ticket.rede_id != null ? (
                    <Link
                      to={`/redes/${ticket.rede_id}`}
                      className="font-medium text-cyan-700 underline decoration-cyan-700/35 underline-offset-2 hover:text-cyan-900 dark:text-cyan-400 dark:decoration-cyan-400/35 dark:hover:text-cyan-300"
                    >
                      {ticket.rede_nome}
                    </Link>
                  ) : (
                    <span className="text-slate-500 dark:text-slate-400">{ticket.rede_nome}</span>
                  ))}
                {ticket.rede_nome && ticket.empresa_nome && (
                  <span className="mx-1 text-slate-400 dark:text-slate-500">·</span>
                )}
                {ticket.empresa_nome &&
                  (ticket.empresa_id != null ? (
                    <Link
                      to={`/empresas/${ticket.empresa_id}`}
                      className="font-medium text-cyan-700 underline decoration-cyan-700/35 underline-offset-2 hover:text-cyan-900 dark:text-cyan-400 dark:decoration-cyan-400/35 dark:hover:text-cyan-300"
                    >
                      {ticket.empresa_nome}
                    </Link>
                  ) : (
                    <span className="font-medium text-slate-800 dark:text-slate-200">{ticket.empresa_nome}</span>
                  ))}
              </p>
            )}

            {triagemInbound && (
              <div
                className={`mt-2 rounded-lg border px-2.5 py-2 text-[11px] sm:px-3 sm:text-xs ${
                  requerCadastroFuncionario
                    ? 'border-amber-200 bg-amber-50 text-amber-950 dark:border-amber-800/60 dark:bg-amber-950/40 dark:text-amber-100'
                    : 'border-sky-200 bg-sky-50 text-sky-950 dark:border-sky-800/60 dark:bg-sky-950/40 dark:text-sky-100'
                }`}
              >
                {requerCadastroFuncionario ? (
                  <>
                    <p className="font-medium">Remetente sem cadastro</p>
                    {isAdmin && (
                      <Link to={linkCadastroFuncionario} className="mt-1 inline-block font-semibold underline underline-offset-2">
                        Cadastrar funcionário
                      </Link>
                    )}
                  </>
                ) : (
                  <>
                    <p className="font-medium">Defina a empresa do ticket</p>
                    <button
                      type="button"
                      onClick={() => abrirModalGerir('geral')}
                      className="mt-1 font-semibold underline underline-offset-2"
                    >
                      Gerir ticket
                    </button>
                  </>
                )}
              </div>
            )}

            {podeAtribuirAMim && (
              <p className="mt-1.5 hidden text-xs text-slate-500 sm:block dark:text-slate-400">
                Na fila sem responsável — atribua a você para dar andamento.
              </p>
            )}

            <div
              className="mt-2 -mx-3 overflow-x-auto overscroll-x-contain px-3 [scrollbar-width:none] sm:mx-0 sm:mt-3 sm:px-0 [&::-webkit-scrollbar]:hidden"
              role="group"
              aria-label="Metadados do ticket"
            >
              <div className="flex w-max flex-nowrap gap-1.5 sm:w-auto sm:max-w-full sm:flex-wrap sm:gap-2">
                <TicketMetaChip
                  label="Setor"
                  value={ticket.setor_nome ?? `#${ticket.setor_id}`}
                  onClick={() => tentarEditarTicket(() => abrirModalGerir('setor'))}
                />
                <TicketMetaChip
                  label="Status"
                  value={ticket.status_nome ?? String(ticket.status_id)}
                  onClick={() => tentarEditarTicket(() => abrirModalGerir('status'))}
                />
                <TicketMetaChip
                  label="Resp."
                  value={ticket.atendente_nome ?? '—'}
                  onClick={() => tentarEditarTicket(() => abrirModalGerir('atendente'))}
                />
                <TicketMetaChip
                  label="Hier."
                  value={rotuloChipHierarquia}
                  onClick={() => tentarEditarTicket(() => abrirModalGerir('hierarquia'))}
                />
                <TicketMetaChip
                  label="Prior."
                  value={rotuloPrioridade(ticket.prioridade)}
                  onClick={() => tentarEditarTicket(() => abrirModalGerir('classificacao'))}
                />
                <TicketMetaChip
                  label="Motivo"
                  value={
                    ticket.motivo_nome
                      ? `${ticket.natureza_nome ? `${ticket.natureza_nome} · ` : ''}${ticket.motivo_nome}`
                      : '—'
                  }
                  onClick={() => tentarEditarTicket(() => abrirModalGerir('classificacao'))}
                />
                <TicketMetaChip
                  label="Relacionados"
                  value={rotuloChipRelacionados}
                  onClick={() => tentarEditarTicket(() => abrirModalGerir('relacionados'))}
                />
              </div>
            </div>

            <p className="mt-1.5 text-[10px] text-slate-500 sm:text-xs dark:text-slate-400">
              <span className="sm:hidden">Aberto {dataAberturaCurta}</span>
              <span className="hidden sm:inline">
                Aberto em {ticket.created_at ? new Date(ticket.created_at).toLocaleString('pt-BR') : '—'}
              </span>
              {ticket.fechado_em ? (
                <span className="ml-2 font-medium text-emerald-700 dark:text-emerald-400">
                  · Fechado {new Date(ticket.fechado_em).toLocaleDateString('pt-BR')}
                </span>
              ) : null}
            </p>

            {chatsWhatsapp.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-2">
                {chatsWhatsapp.map((c) => (
                  <Link
                    key={c.id}
                    to={`/whatsapp/c/${c.id}`}
                    className="inline-flex rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[10px] font-medium text-cyan-700 sm:text-xs dark:border-slate-700 dark:bg-slate-900/40 dark:text-cyan-400"
                  >
                    WA {exibirProtocolo(c.protocolo)}
                  </Link>
                ))}
              </div>
            )}

            <div className="mt-2 border-t border-slate-100 pt-2 sm:pt-3 lg:hidden dark:border-slate-800">
              <div className="grid grid-cols-2 gap-1.5 sm:gap-2">{botoesAcaoTicket}</div>
            </div>
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-x-hidden overflow-y-auto">
          <div className="mx-auto max-w-6xl space-y-4 px-3 pb-8 pt-3 sm:space-y-6 sm:px-5 sm:pb-10 sm:pt-4 md:px-6">
        {temVinculosHierarquia && (
          <div className="rounded-xl border border-slate-200/90 bg-slate-50/50 px-3 py-2.5 text-sm dark:border-slate-700/80 dark:bg-slate-900/35">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0 flex-1 space-y-2 text-slate-700 dark:text-slate-200">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                    Ticket pai
                  </p>
                  {ticket.parent_ticket_id == null ? (
                    <p className="mt-0.5 text-slate-500 dark:text-slate-400">Nenhum.</p>
                  ) : (
                    <Link
                      to={`/tickets/${ticket.parent_ticket_id}`}
                      className="mt-0.5 inline-block font-medium text-cyan-700 underline hover:text-cyan-900 dark:text-cyan-400 dark:hover:text-cyan-300"
                    >
                      {ticket.parent
                        ? `${exibirProtocolo(ticket.parent.protocolo)} — ${ticket.parent.assunto}`
                        : `Ticket #${ticket.parent_ticket_id}`}
                    </Link>
                  )}
                </div>
                {ticket.children && ticket.children.length > 0 && (
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                      Tickets filhos
                    </p>
                    <ul className="mt-1 space-y-1">
                      {ticket.children.map((c) => (
                        <li key={c.id}>
                          <Link
                            to={`/tickets/${c.id}`}
                            className="font-medium text-cyan-700 underline hover:text-cyan-900 dark:text-cyan-400 dark:hover:text-cyan-300"
                          >
                            {exibirProtocolo(c.protocolo)}
                          </Link>
                          <span className="text-slate-600 dark:text-slate-300"> — {c.assunto}</span>
                          <span className="ml-1 text-xs text-slate-500 dark:text-slate-400">
                            ({c.status_nome ?? '—'}
                            {c.fechado_em ? ', fechado' : ', aberto'})
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
              {podeEditarHierarquia && (
                <Button type="button" variant="secondary" className="shrink-0" onClick={() => abrirModalGerir('hierarquia')}>
                  Gerir vínculos
                </Button>
              )}
            </div>
          </div>
        )}

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
          {anexos.some((a) => a.mensagem_id == null) && (
            <div className="rounded-xl border border-slate-200/90 bg-slate-50/70 px-4 py-3 text-sm dark:border-slate-700/70 dark:bg-slate-900/30">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                Anexos do ticket
              </p>
              <ul className="mt-2 space-y-2">
                {anexos
                  .filter((a) => a.mensagem_id == null)
                  .map((a) => (
                    <li key={a.id} className="flex flex-wrap items-center justify-between gap-2">
                      <button
                        type="button"
                        onClick={() => baixarOuVisualizarAnexo(a)}
                        className="text-left text-sm font-medium text-cyan-700 underline hover:text-cyan-900 dark:text-cyan-400 dark:hover:text-cyan-300"
                      >
                        {a.nome_original}
                      </button>
                      <span className="text-xs text-slate-500 dark:text-slate-400">
                        {(a.tamanho_bytes / 1024).toFixed(1)} KB
                      </span>
                    </li>
                  ))}
              </ul>
            </div>
          )}
          {mensagens.length === 0 ? (
            <p className="text-sm text-slate-500 dark:text-slate-400">Nenhuma mensagem ainda.</p>
          ) : (
            <ul className="space-y-3">
              {mensagens.map((msg) => {
                const isAbertura = msg.tipo === 'abertura'
                const isInterno = msg.tipo === 'interno'
                const isEmailCliente = msg.tipo === 'email_cliente'
                const autor = autorRodapeMensagem(msg)
                const anexosDaMsg = anexos.filter((a) => a.mensagem_id === msg.id)
                const podeGerirEmail =
                  Boolean(user) &&
                  (isAdmin || (msg.atendente_id != null && msg.atendente_id === user!.id))
                const corpoBase =
                  isAbertura || isEmailCliente ? corpoMensagemEmailVisivel(msg.corpo) : msg.corpo
                const corpoParaExibir =
                  corpoExtraidoPorMensagemId[msg.id] &&
                  (isCorpoVazioOuNaoTexto(msg.corpo) || !corpoBase.trim())
                    ? corpoExtraidoPorMensagemId[msg.id]
                    : corpoBase || '(corpo vazio ou não texto)'
                return (
                  <li
                    key={msg.id}
                    className={`rounded-xl border px-4 py-3 text-sm ${
                      isInterno
                        ? 'border-amber-200/90 bg-amber-50/60 dark:border-amber-800/50 dark:bg-amber-950/25'
                        : isAbertura
                          ? 'border border-slate-200 border-l-4 border-l-slate-500 bg-slate-50/90 dark:border-slate-600 dark:border-l-slate-400 dark:bg-slate-800/50'
                          : isEmailCliente
                            ? 'border border-slate-200 border-l-4 border-l-cyan-500 bg-cyan-50/40 dark:border-slate-600 dark:border-l-cyan-400 dark:bg-cyan-950/20'
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
                    <p className="mt-2 whitespace-pre-wrap text-slate-800 dark:text-slate-200">{corpoParaExibir}</p>
                    {msg.status && msg.tipo === 'publico' && ticket ? (
                      <TicketMensagemEmailOutbox
                        ticketId={ticket.id}
                        msg={msg}
                        podeGerir={podeGerirEmail}
                        onAtualizado={async () => {
                          const m = await tickets.listMensagens(ticket.id)
                          setMensagens(m)
                        }}
                      />
                    ) : null}
                    {anexosDaMsg.length > 0 && (
                      <div className="mt-3 rounded-lg border border-slate-200/80 bg-slate-50/70 px-3 py-2 dark:border-slate-700/70 dark:bg-slate-900/30">
                        <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                          Anexos
                        </p>
                        <ul className="mt-2 space-y-1">
                          {anexosDaMsg.map((a) => (
                            <li key={a.id} className="flex flex-wrap items-center justify-between gap-2">
                              <button
                                type="button"
                                onClick={() => baixarOuVisualizarAnexo(a)}
                                className="text-left text-xs font-medium text-cyan-700 underline hover:text-cyan-900 dark:text-cyan-400 dark:hover:text-cyan-300"
                              >
                                {a.nome_original}
                              </button>
                              <span className="text-[10px] text-slate-500 dark:text-slate-400">
                                {(a.tamanho_bytes / 1024).toFixed(1)} KB
                              </span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
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
                  Mensagem ao cliente
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
              ref={textareaRef}
              value={novaMensagemTexto}
              onChange={(e) => setNovaMensagemTexto(e.target.value)}
              onPaste={handlePasteNoCampoMensagem}
              spellCheck={false}
              rows={4}
              disabled={Boolean(ticket.fechado_em)}
              placeholder={
                tipoNovaMensagem === 'interno'
                  ? 'Anotação visível apenas para atendentes…'
                  : 'Descreva o que foi feito, testado ou o que falta…'
              }
              className={`w-full rounded-xl border-0 px-3 py-2 text-sm text-slate-900 shadow-inner ring-1 placeholder:text-slate-400 focus:outline-none focus:ring-2 disabled:cursor-not-allowed disabled:opacity-60 dark:text-slate-100 dark:placeholder:text-slate-500 ${
                tipoNovaMensagem === 'interno' || !podeMensagemPublica
                  ? 'bg-amber-50 ring-amber-200/90 focus:bg-amber-50 focus:ring-amber-400/30 dark:bg-amber-950/25 dark:ring-amber-800/60 dark:focus:bg-amber-950/25 dark:focus:ring-amber-700/35'
                  : 'bg-slate-50 ring-slate-200/90 focus:bg-white focus:ring-slate-400/35 dark:bg-slate-900/80 dark:ring-slate-600 dark:focus:bg-slate-900 dark:focus:ring-slate-500/50'
              }`}
            />
            {podeMensagemPublica && tipoNovaMensagem === 'publico' ? (
              <label className="mt-2 flex cursor-pointer items-start gap-2 text-xs text-slate-600 dark:text-slate-400">
                <input
                  type="checkbox"
                  className="mt-0.5 size-4 shrink-0 rounded border-slate-300 text-cyan-600 focus:ring-cyan-500/40 dark:border-slate-600 dark:bg-slate-900"
                  checked={notificarClienteEmail}
                  onChange={(e) => setNotificarClienteEmail(e.target.checked)}
                />
                <span>
                  Enviar também por e-mail ao cliente (último remetente do ticket via encaminhamento; requer envio
                  configurado na plataforma).
                </span>
              </label>
            ) : null}
            <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap items-center gap-2">
                <RespostasProntasPicker
                  setorId={ticket.setor_id}
                  disabled={Boolean(ticket.fechado_em)}
                  onInserir={inserirRespostaPronta}
                />
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  className="hidden"
                  onChange={(e) => {
                    const files = e.target.files ? Array.from(e.target.files) : []
                    setAnexosSelecionados(files)
                  }}
                />
                <Button
                  type="button"
                  variant="secondary"
                  disabled={Boolean(ticket.fechado_em)}
                  onClick={() => fileInputRef.current?.click()}
                  className="inline-flex items-center gap-2"
                >
                  <svg className="size-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"
                    />
                  </svg>
                  Anexar arquivos
                </Button>
                {anexosSelecionados.length > 0 && (
                  <span className="text-xs text-slate-500 dark:text-slate-400">
                    {anexosSelecionados.length} arquivo(s) selecionado(s)
                  </span>
                )}
              </div>
              <Button
                type="button"
                onClick={handleEnviarMensagem}
                loading={enviandoMensagem || enviandoAnexos}
                disabled={Boolean(ticket.fechado_em)}
              >
                Enviar
              </Button>
            </div>
          </div>
        </div>
      </Card>

      {previewAnexo && (
        <div
          className="fixed inset-0 z-[600] flex items-center justify-center bg-slate-950/60 p-4 backdrop-blur-[2px]"
          role="presentation"
          onClick={() => {
            URL.revokeObjectURL(previewAnexo.url)
            setPreviewAnexo(null)
            setPreviewAnexoTexto(null)
          }}
        >
          <div
            role="dialog"
            aria-modal="true"
            className="flex max-h-[90vh] w-full max-w-5xl flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl dark:border-slate-700 dark:bg-slate-950"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between gap-3 border-b border-slate-200 px-4 py-3 dark:border-slate-700">
              <div className="min-w-0">
                <div className="truncate text-sm font-semibold text-slate-900 dark:text-slate-100">
                  {previewAnexo.nome}
                </div>
                <div className="truncate text-xs text-slate-500 dark:text-slate-400">{previewAnexo.contentType}</div>
              </div>
              <Button
                type="button"
                variant="secondary"
                onClick={() => {
                  URL.revokeObjectURL(previewAnexo.url)
                  setPreviewAnexo(null)
                  setPreviewAnexoTexto(null)
                }}
              >
                Fechar
              </Button>
            </div>
            <div className="flex-1 overflow-auto bg-slate-50 p-3 dark:bg-slate-900/40">
              {previewAnexo.contentType.startsWith('image/') ? (
                <img
                  src={previewAnexo.url}
                  alt={previewAnexo.nome}
                  className="mx-auto max-h-[80vh] max-w-full rounded-lg border border-slate-200 dark:border-slate-700"
                />
              ) : previewAnexo.contentType === 'application/pdf' ? (
                <iframe title={previewAnexo.nome} src={previewAnexo.url} className="h-[80vh] w-full rounded-lg" />
              ) : previewAnexo.contentType.startsWith('text/html') ? (
                <iframe
                  title={previewAnexo.nome}
                  sandbox=""
                  srcDoc={previewAnexoTexto ?? ''}
                  className="h-[80vh] w-full rounded-lg bg-white"
                />
              ) : previewAnexo.contentType.startsWith('text/') ? (
                <pre className="h-[80vh] w-full overflow-auto rounded-lg border border-slate-200 bg-white p-3 text-xs text-slate-900 whitespace-pre-wrap dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100">
                  {previewAnexoTexto ?? ''}
                </pre>
              ) : (
                <div className="text-sm text-slate-600 dark:text-slate-300">
                  Pré-visualização indisponível para este tipo. Use o download.
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {historico.length > 0 && (
        <div className="mt-4 rounded-xl border border-slate-200/90 bg-white shadow-sm sm:mt-6 dark:border-slate-700/80 dark:bg-slate-900/70 dark:shadow-none dark:ring-1 dark:ring-white/5">
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

          </div>
        </div>
      </div>

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
            className={MODAL_PANEL_SCROLLABLE}
            onClick={(e) => e.stopPropagation()}
          >
            <h2 id="ticket-gerir-titulo" className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              {modalGerirFoco === 'hierarquia'
                ? 'Hierarquia de tickets'
                : modalGerirFoco === 'relacionados'
                  ? 'Tickets relacionados'
                  : modalGerirFoco === 'setor'
                    ? 'Transferir de setor'
                    : modalGerirFoco === 'status'
                      ? 'Alterar status'
                      : modalGerirFoco === 'atendente'
                        ? 'Transferir responsável'
                        : 'Gerir ticket'}
            </h2>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              {modalGerirFoco === 'hierarquia' &&
                'Crie um filho novo, vincule tickets existentes como filhos ou defina um ticket pai (mesma rede, com acesso).'}
              {modalGerirFoco === 'relacionados' &&
                'Duplicado encerra este ticket e aponta para o original. Relacionado apenas liga assuntos distintos, sem fechar.'}
              {modalGerirFoco === 'geral' &&
                'Vincule rede e empresa, transfira de setor, altere o status ou atribua a outro atendente.'}
              {modalGerirFoco === 'setor' && 'Escolha o setor que passará a tratar este ticket.'}
              {modalGerirFoco === 'status' && 'Atualize o status conforme o andamento do atendimento.'}
              {modalGerirFoco === 'atendente' && 'Defina quem é o responsável pelo ticket (ou deixe sem responsável).'}
            </p>

            {modalGerirFoco === 'hierarquia' && ticket && (
              <div className="mt-4 space-y-4 text-sm text-slate-700 dark:text-slate-200">
                <button
                  type="button"
                  onClick={() => setModalGerirFoco('geral')}
                  className="text-sm font-medium text-cyan-700 underline hover:text-cyan-900 dark:text-cyan-400 dark:hover:text-cyan-300"
                >
                  ← Voltar a setor, status e responsável
                </button>

                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                    Ticket pai
                  </p>
                  {ticket.parent_ticket_id == null ? (
                    <p className="mt-1 text-slate-500 dark:text-slate-400">Nenhum.</p>
                  ) : (
                    <div className="mt-2 flex flex-wrap items-center gap-2">
                      <Link
                        to={`/tickets/${ticket.parent_ticket_id}`}
                        className="font-medium text-cyan-700 underline hover:text-cyan-900 dark:text-cyan-400 dark:hover:text-cyan-300"
                        onClick={() => setModalGerirAberto(false)}
                      >
                        {ticket.parent
                          ? `${exibirProtocolo(ticket.parent.protocolo)} — ${ticket.parent.assunto}`
                          : `Ticket #${ticket.parent_ticket_id}`}
                      </Link>
                      {podeEditarHierarquia && (
                        <Button
                          type="button"
                          variant="secondary"
                          loading={desvinculandoHierarquia}
                          onClick={handleDesvincularDoPai}
                        >
                          Desvincular do pai
                        </Button>
                      )}
                    </div>
                  )}
                </div>

                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                    Tickets filhos
                  </p>
                  {(!ticket.children || ticket.children.length === 0) && (
                    <p className="mt-1 text-slate-500 dark:text-slate-400">Nenhum filho vinculado.</p>
                  )}
                  {ticket.children && ticket.children.length > 0 && (
                    <ul className="mt-2 divide-y divide-slate-200 rounded-lg border border-slate-200 dark:divide-slate-700 dark:border-slate-700">
                      {ticket.children.map((c) => (
                        <li key={c.id} className="flex flex-wrap items-center justify-between gap-2 px-3 py-2">
                          <div className="min-w-0">
                            <Link
                              to={`/tickets/${c.id}`}
                              className="font-medium text-cyan-700 underline hover:text-cyan-900 dark:text-cyan-400 dark:hover:text-cyan-300"
                              onClick={() => setModalGerirAberto(false)}
                            >
                              {exibirProtocolo(c.protocolo)}
                            </Link>
                            <span className="text-slate-600 dark:text-slate-300"> — {c.assunto}</span>
                            <span className="ml-2 text-xs text-slate-500 dark:text-slate-400">
                              {c.status_nome ?? '—'}
                              {c.fechado_em ? ' · fechado' : ' · aberto'}
                            </span>
                          </div>
                          {podeEditarHierarquia && !c.fechado_em && (
                            <Button
                              type="button"
                              variant="secondary"
                              loading={desvinculandoHierarquia}
                              onClick={() => handleDesvincularFilho(c.id)}
                            >
                              Desvincular
                            </Button>
                          )}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>

                {podeEditarHierarquia && (
                  <div className="rounded-lg border border-cyan-200/90 bg-cyan-50/50 p-3 dark:border-cyan-900/40 dark:bg-cyan-950/20">
                    <p className="text-xs font-semibold uppercase tracking-wide text-cyan-800 dark:text-cyan-300">
                      Abrir filhos em massa (por empresa da rede)
                    </p>
                    <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
                      Cria um ticket filho para cada empresa selecionada — útil para rollouts ou tarefas iguais em toda a rede.
                    </p>
                    <div className="mt-3">
                      <TicketFilhosMassaPanel
                        ticketId={ticket.id}
                        disabled={desvinculandoHierarquia || vinculandoFilho || vinculandoPai}
                        onCriados={recarregarTicketAtual}
                      />
                    </div>
                  </div>
                )}

                {podeEditarHierarquia && (
                  <div className="flex flex-wrap gap-2">
                    <Button
                      type="button"
                      variant="secondary"
                      disabled={desvinculandoHierarquia}
                      onClick={() => {
                        navigate(`/tickets/novo?pai=${ticket.id}`)
                        setModalGerirAberto(false)
                      }}
                    >
                      Abrir ticket filho
                    </Button>
                  </div>
                )}

                {podeEditarHierarquia && (
                  <div className="rounded-lg border border-slate-200/90 bg-slate-50/70 p-3 dark:border-slate-700/70 dark:bg-slate-900/30">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                      Vincular ticket existente como filho
                    </p>
                    <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                      Escolha um ticket em aberto na lista; ele passará a ser filho deste.
                    </p>
                    <div className="mt-3">
                      <TicketBuscaPicker
                        ticketAtualId={ticket.id}
                        excluirIds={idsTicketsExcluirBusca}
                        label="Ticket filho"
                        disabled={vinculandoFilho || desvinculandoHierarquia || vinculandoPai}
                        loadingExterno={vinculandoFilho}
                        onSelecionar={(alvo) => void handleVincularFilhoExistente(alvo)}
                      />
                    </div>
                  </div>
                )}

                {podeEditarHierarquia && (
                  <div className="rounded-lg border border-slate-200/90 bg-slate-50/70 p-3 dark:border-slate-700/70 dark:bg-slate-900/30">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                      {ticket.parent_ticket_id != null ? 'Alterar ticket pai' : 'Vincular a um ticket pai'}
                    </p>
                    <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                      Escolha o ticket pai na lista (substitui o vínculo atual, se houver).
                    </p>
                    <div className="mt-3">
                      <TicketBuscaPicker
                        ticketAtualId={ticket.id}
                        excluirIds={idsTicketsExcluirBusca}
                        label="Ticket pai"
                        disabled={vinculandoPai || desvinculandoHierarquia || vinculandoFilho}
                        loadingExterno={vinculandoPai}
                        onSelecionar={(alvo) => void handleVincularAoPai(alvo)}
                      />
                    </div>
                  </div>
                )}
              </div>
            )}

            {modalGerirFoco === 'relacionados' && ticket && (
              <div className="mt-4 space-y-4 text-sm text-slate-700 dark:text-slate-200">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                    Vínculos atuais
                  </p>
                  {(ticket.vinculos?.length ?? 0) === 0 ? (
                    <p className="mt-1 text-slate-500 dark:text-slate-400">Nenhum vínculo lateral.</p>
                  ) : (
                    <ul className="mt-2 divide-y divide-slate-200 rounded-lg border border-slate-200 dark:divide-slate-700 dark:border-slate-700">
                      {(ticket.vinculos ?? []).map((v) => (
                        <li key={v.id} className="flex flex-wrap items-center justify-between gap-2 px-3 py-2">
                          <div className="min-w-0">
                            <span className="text-xs font-medium text-slate-500 dark:text-slate-400">{v.rotulo}</span>
                            <Link
                              to={`/tickets/${v.outro_ticket.id}`}
                              className="ml-2 font-medium text-cyan-700 underline hover:text-cyan-900 dark:text-cyan-400 dark:hover:text-cyan-300"
                              onClick={() => setModalGerirAberto(false)}
                            >
                              {exibirProtocolo(v.outro_ticket.protocolo)} — {v.outro_ticket.assunto}
                            </Link>
                            {v.outro_ticket.status_nome ? (
                              <span className="ml-2 text-xs text-slate-500 dark:text-slate-400">
                                ({v.outro_ticket.status_nome})
                              </span>
                            ) : null}
                          </div>
                          {podeEditarHierarquia && (
                            <Button
                              type="button"
                              variant="secondary"
                              loading={removendoVinculoId === v.id}
                              onClick={() => void handleRemoverVinculoRelacionado(v.id)}
                            >
                              Remover
                            </Button>
                          )}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>

                {podeEditarHierarquia && (
                  <div className="rounded-lg border border-slate-200/90 bg-slate-50/70 p-3 dark:border-slate-700/70 dark:bg-slate-900/30">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                      Adicionar vínculo
                    </p>
                    <div className="mt-3 space-y-3">
                      <Select
                        label="Tipo de vínculo"
                        value={tipoVinculoRelacionado}
                        onChange={(v) => setTipoVinculoRelacionado(v as Tickets.TicketVinculoTipo)}
                        options={[
                          { value: 'relacionado_a', label: 'Relacionado a — assuntos ligados, ambos podem seguir abertos' },
                          { value: 'duplicado_de', label: 'Duplicado de — mesma solicitação; encerra este ticket' },
                        ]}
                      />
                      {tipoVinculoRelacionado === 'duplicado_de' ? (
                        <div className="space-y-2">
                          <p className="text-xs text-slate-600 dark:text-slate-400">
                            Este ticket será tratado como cópia do original na{' '}
                            <strong>mesma rede e empresa</strong>. O atendimento oficial fica no ticket que você
                            escolher abaixo.
                          </p>
                          <CheckboxField
                            checked={fecharComoDuplicado}
                            onChange={(e) => setFecharComoDuplicado(e.target.checked)}
                            disabled={vinculandoRelacionado || Boolean(ticket.fechado_em)}
                          >
                            Fechar este ticket e registrar mensagem pública apontando para o original
                          </CheckboxField>
                          {fecharComoDuplicado && !ticket.fechado_em ? (
                            <TicketClassificacaoFields
                              value={vinculoClassificacao}
                              onChange={setVinculoClassificacao}
                              disabled={vinculandoRelacionado}
                            />
                          ) : null}
                          {ticket.fechado_em ? (
                            <p className="text-xs text-amber-700 dark:text-amber-400">
                              Este ticket já está fechado — apenas o vínculo será registrado.
                            </p>
                          ) : null}
                        </div>
                      ) : (
                        <p className="text-xs text-slate-600 dark:text-slate-400">
                          Use quando os chamados são diferentes, mas você quer mantê-los visíveis um ao outro.
                        </p>
                      )}
                      {tipoVinculoRelacionado === 'duplicado_de' && ticket.empresa_id == null ? (
                        <p className="text-xs text-amber-700 dark:text-amber-400">
                          Defina a empresa deste ticket (em Gerir) antes de marcar um duplicado — só chamados da mesma
                          rede e empresa podem ser duplicados.
                        </p>
                      ) : (
                        <TicketBuscaPicker
                          ticketAtualId={ticket.id}
                          excluirIds={idsTicketsExcluirBusca}
                          filtroEmpresaId={
                            tipoVinculoRelacionado === 'duplicado_de' ? ticket.empresa_id : undefined
                          }
                          filtroRedeId={tipoVinculoRelacionado === 'duplicado_de' ? ticket.rede_id : undefined}
                          label="Buscar ticket em aberto"
                          hint={
                            tipoVinculoRelacionado === 'duplicado_de'
                              ? `Somente tickets abertos da mesma rede e empresa${
                                  ticket.empresa_nome ? ` (${ticket.empresa_nome})` : ''
                                }.`
                              : 'Clique em um ticket da lista para vincular.'
                          }
                          disabled={vinculandoRelacionado}
                          loadingExterno={vinculandoRelacionado}
                          onSelecionar={(alvo) => void handleAdicionarVinculoRelacionado(alvo)}
                        />
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}

            {modalGerirFoco !== 'hierarquia' && modalGerirFoco !== 'relacionados' && (
              <div className="mt-5 space-y-4">
                {modalGerirFoco === 'geral' && (
                  <>
                    <Select
                      label="Rede"
                      value={editRede}
                      onChange={(v) => {
                        setEditRede(v === '' ? '' : Number(v))
                        setEditEmpresa('')
                      }}
                      options={redesList.map((r) => ({
                        value: r.id,
                        label: `${r.nome}${!r.ativo ? ' (inativa)' : ''}`,
                      }))}
                      includeEmpty
                      emptyLabel="— Selecione a rede —"
                      placeholder="Rede"
                      disabled={redeTriagemFixa}
                    />
                    <Select
                      label="Empresa"
                      value={editEmpresa}
                      onChange={(v) => setEditEmpresa(v === '' ? '' : Number(v))}
                      options={empresasOpcoesModal.map((e) => ({
                        value: e.id,
                        label: `${e.nome}${!e.ativo ? ' (inativa)' : ''}`,
                      }))}
                      includeEmpty
                      emptyLabel="— Selecione a empresa —"
                      placeholder="Empresa"
                      disabled={editRede === '' && empresasVinculoSugeridas.length === 0}
                    />
                    {editRede === '' && empresasVinculoSugeridas.length === 0 && (
                      <p className="text-xs text-slate-500 dark:text-slate-400">
                        Selecione a rede para listar as empresas vinculadas.
                      </p>
                    )}
                    {empresasVinculoSugeridas.length > 0 && (
                      <p className="text-xs text-slate-500 dark:text-slate-400">
                        Apenas empresas em que o remetente do e-mail está cadastrado.
                      </p>
                    )}
                  </>
                )}
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
                {(modalGerirFoco === 'geral' || modalGerirFoco === 'classificacao') && (
                  <>
                    <Select
                      label="Prioridade"
                      value={editPrioridade}
                      onChange={(v) => setEditPrioridade(v as PrioridadeTicket)}
                      options={PRIORIDADE_OPCOES.map((o) => ({ value: o.value, label: o.label }))}
                      disabled={Boolean(ticket?.fechado_em) && !isAdmin}
                    />
                    <TicketClassificacaoFields
                      value={editClassificacao}
                      onChange={setEditClassificacao}
                      disabled={Boolean(ticket?.fechado_em) && !isAdmin}
                    />
                  </>
                )}
              </div>
            )}

            {modalGerirFoco === 'geral' && (
              <div className="mt-5 rounded-lg border border-slate-200/90 bg-slate-50/60 p-3 dark:border-slate-700/70 dark:bg-slate-900/30">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                  Hierarquia de tickets
                </p>
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                  Filhos, ticket pai e vínculos com chamados existentes.
                </p>
                <Button
                  type="button"
                  variant="secondary"
                  className="mt-3"
                  onClick={() => setModalGerirFoco('hierarquia')}
                >
                  Gerir hierarquia…
                </Button>
              </div>
            )}

            {(modalGerirFoco === 'geral' || modalGerirFoco === 'status') && (
              <p className="mt-4 text-xs text-slate-500 dark:text-slate-400">
                Status com slug{' '}
                <code className="rounded bg-slate-100 px-1 dark:bg-slate-800 dark:text-slate-300">fechado</code> registra a
                data de fechamento.
              </p>
            )}

            {modalGerirFoco !== 'hierarquia' && modalGerirFoco !== 'relacionados' ? (
              <div className="mt-6 flex flex-wrap justify-end gap-2">
                <Button type="button" variant="secondary" onClick={() => setModalGerirAberto(false)}>
                  Cancelar
                </Button>
                <Button type="button" onClick={handleSalvar} loading={saving}>
                  {modalApenasUmCampo ? 'Salvar' : 'Aplicar'}
                </Button>
              </div>
            ) : (
              <div className="mt-6 flex flex-wrap justify-end gap-2">
                <Button type="button" variant="secondary" onClick={() => setModalGerirAberto(false)}>
                  Fechar
                </Button>
              </div>
            )}
          </div>
        </div>
      )}

      {modalFecharAberto && (
        <div
          className="fixed inset-0 z-[520] flex items-end justify-center bg-slate-950/60 p-4 backdrop-blur-[2px] sm:items-center dark:bg-slate-950/70"
          role="presentation"
          onClick={() => {
            if (fechando) return
            setModalFecharAberto(false)
          }}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="ticket-fechar-titulo"
            className={MODAL_PANEL_COMPACT}
            onClick={(e) => e.stopPropagation()}
          >
            <h2 id="ticket-fechar-titulo" className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              Fechar ticket
            </h2>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Ao fechar, o ticket sairá da lista de abertos e não permitirá novas mensagens. Informe a classificação do
              atendimento.
            </p>
            <div className="mt-4">
              <TicketClassificacaoFields
                value={fecharClassificacao}
                onChange={setFecharClassificacao}
                disabled={fechando}
              />
            </div>
            {filhosAbertosCount > 0 && (
              <p className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-950 dark:border-amber-800/50 dark:bg-amber-950/30 dark:text-amber-100">
                Este ticket tem {filhosAbertosCount} filho(s) direto(s) ainda em aberto. O sistema bloqueia o fecho até
                encerrá-los ou desvinculá-los.
              </p>
            )}
            <div className="mt-5 flex flex-wrap justify-end gap-2">
              <Button
                type="button"
                variant="secondary"
                onClick={() => setModalFecharAberto(false)}
                disabled={fechando}
              >
                Cancelar
              </Button>
              <Button
                type="button"
                variant="danger"
                onClick={fecharTicketConfirmado}
                loading={fechando}
                disabled={fechando || filhosAbertosCount > 0}
                title={
                  filhosAbertosCount > 0
                    ? 'Feche ou desvincule os tickets filhos em aberto antes de fechar este ticket.'
                    : undefined
                }
              >
                Fechar ticket
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

