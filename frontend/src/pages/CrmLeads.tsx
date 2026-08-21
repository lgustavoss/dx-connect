import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  ApiError,
  atendentes,
  crmFunil,
  crmLeads,
  crmNegociacoes,
  type Atendentes,
  type Crm,
} from '../api/client'
import { coletarTodasPaginas } from '../api/collectPages'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Input } from '../components/ui/Input'
import { Select } from '../components/ui/Select'
import { IconPencil } from '../components/ui/IconPencil'
import { BarraBuscaPaginacao, PAGE_SIZE_PADRAO } from '../components/ui/BarraBuscaPaginacao'
import { useToast } from '../components/ui/Toast'
import { useAuth } from '../contexts/AuthContext'
import { SemPermissao } from './SemPermissao'

const DND_LEAD = 'application/x-crm-lead'
const DND_COL = 'application/x-crm-estagio'

type VistaCrm = 'lista' | 'kanban'

const VISTA_KEY = 'dx-crm-vista'

function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleDateString('pt-BR')
}

function lerVistaInicial(): VistaCrm {
  try {
    const v = localStorage.getItem(VISTA_KEY)
    return v === 'kanban' ? 'kanban' : 'lista'
  } catch {
    return 'lista'
  }
}

export function CrmLeads() {
  const navigate = useNavigate()
  const toast = useToast()
  const { user, isAdmin } = useAuth()

  const [vista, setVista] = useState<VistaCrm>(lerVistaInicial)
  const [estagios, setEstagios] = useState<Crm.FunilEstagio[]>([])
  const [contagens, setContagens] = useState<Record<number, number>>({})
  const [list, setList] = useState<Crm.Lead[]>([])
  const [kanbanLeads, setKanbanLeads] = useState<Crm.Lead[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [busca, setBusca] = useState('')
  const [debouncedBusca, setDebouncedBusca] = useState('')
  const [estagioId, setEstagioId] = useState<number | ''>('')
  const [soMinhas, setSoMinhas] = useState(false)
  const [loading, setLoading] = useState(true)
  const [forbidden, setForbidden] = useState(false)
  const [draggingId, setDraggingId] = useState<number | null>(null)
  const [draggingColId, setDraggingColId] = useState<number | null>(null)
  const [dropColId, setDropColId] = useState<number | null>(null)
  const [moving, setMoving] = useState(false)
  const [reorderingCols, setReorderingCols] = useState(false)
  const [editingColId, setEditingColId] = useState<number | null>(null)
  const [editingNome, setEditingNome] = useState('')
  const [savingCol, setSavingCol] = useState(false)
  const cancelEditColRef = useRef(false)

  const [modalOpen, setModalOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [nome, setNome] = useState('')
  const [telefone, setTelefone] = useState('')
  const [email, setEmail] = useState('')
  const [empresaTexto, setEmpresaTexto] = useState('')
  const [origem, setOrigem] = useState('')
  const [notas, setNotas] = useState('')
  const [responsavelId, setResponsavelId] = useState<number | ''>('')
  const [responsaveis, setResponsaveis] = useState<Atendentes.Atendente[]>([])
  const loadGenRef = useRef(0)

  function mudarVista(v: VistaCrm) {
    if (v === vista) return
    setLoading(true)
    setVista(v)
    try {
      localStorage.setItem(VISTA_KEY, v)
    } catch {
      /* ignore */
    }
  }

  useEffect(() => {
    const t = setTimeout(() => setDebouncedBusca(busca.trim()), 400)
    return () => clearTimeout(t)
  }, [busca])

  useEffect(() => {
    setPage(1)
  }, [debouncedBusca, estagioId, soMinhas, vista])

  const loadEstagios = useCallback(() => {
    crmFunil
      .list()
      .then(setEstagios)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 403) setForbidden(true)
        else toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível carregar o funil.'))
      })
  }, [toast])

  useEffect(() => {
    loadEstagios()
  }, [loadEstagios])

  useEffect(() => {
    if (!isAdmin) return
    atendentes
      .list({ limit: 100, offset: 0 })
      .then(({ items }) => {
        setResponsaveis(items.filter((a) => a.ativo && (a.role === 'comercial' || a.role === 'admin')))
      })
      .catch(() => setResponsaveis([]))
  }, [isAdmin])

  const loadContagens = useCallback(async (stages: Crm.FunilEstagio[]) => {
    if (!stages.length) return
    try {
      const pairs = await Promise.all(
        stages.map(async (e) => {
          const { total: t } = await crmLeads.list({
            estagio_id: e.id,
            limit: 1,
            offset: 0,
            so_minhas: soMinhas || undefined,
            ativo: true,
            q: debouncedBusca || undefined,
          })
          return [e.id, t] as const
        }),
      )
      setContagens(Object.fromEntries(pairs))
    } catch {
      /* contadores auxiliares */
    }
  }, [soMinhas, debouncedBusca])

  useEffect(() => {
    if (estagios.length) void loadContagens(estagios)
  }, [estagios, loadContagens])

  const loadLista = useCallback(() => {
    const gen = ++loadGenRef.current
    setLoading(true)
    setForbidden(false)
    crmLeads
      .list({
        q: debouncedBusca || undefined,
        estagio_id: estagioId === '' ? undefined : estagioId,
        so_minhas: soMinhas || undefined,
        ativo: true,
        offset: (page - 1) * PAGE_SIZE_PADRAO,
        limit: PAGE_SIZE_PADRAO,
      })
      .then(({ items, total: t }) => {
        if (gen !== loadGenRef.current) return
        setList(items)
        setTotal(t)
      })
      .catch((err) => {
        if (gen !== loadGenRef.current) return
        if (err instanceof ApiError && err.status === 403) {
          setForbidden(true)
          setList([])
          setTotal(0)
          return
        }
        toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível carregar as leads.'))
        setList([])
        setTotal(0)
      })
      .finally(() => {
        if (gen === loadGenRef.current) setLoading(false)
      })
  }, [debouncedBusca, estagioId, soMinhas, page, toast])

  const loadKanban = useCallback(() => {
    const gen = ++loadGenRef.current
    setLoading(true)
    setForbidden(false)
    coletarTodasPaginas<Crm.Lead>(
      (offset, limit) =>
        crmLeads.list({
          q: debouncedBusca || undefined,
          so_minhas: soMinhas || undefined,
          ativo: true,
          offset,
          limit,
        }),
      100,
      300,
    )
      .then((items) => {
        if (gen !== loadGenRef.current) return
        setKanbanLeads(items)
        setTotal(items.length)
      })
      .catch((err) => {
        if (gen !== loadGenRef.current) return
        if (err instanceof ApiError && err.status === 403) {
          setForbidden(true)
          setKanbanLeads([])
          return
        }
        toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível carregar o Kanban.'))
        setKanbanLeads([])
      })
      .finally(() => {
        if (gen === loadGenRef.current) setLoading(false)
      })
  }, [debouncedBusca, soMinhas, toast])

  useEffect(() => {
    if (vista === 'kanban') loadKanban()
    else loadLista()
  }, [vista, loadKanban, loadLista])

  const porEstagio = useMemo(() => {
    const map = new Map<number, Crm.Lead[]>()
    for (const e of estagios) map.set(e.id, [])
    for (const lead of kanbanLeads) {
      const bucket = map.get(lead.estagio_id)
      if (bucket) bucket.push(lead)
      else map.set(lead.estagio_id, [lead])
    }
    return map
  }, [estagios, kanbanLeads])

  function openModal() {
    setNome('')
    setTelefone('')
    setEmail('')
    setEmpresaTexto('')
    setOrigem('')
    setNotas('')
    setResponsavelId(user?.id ?? '')
    setModalOpen(true)
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    if (!nome.trim()) {
      toast.showWarning('Informe o nome do contato.')
      return
    }
    setSaving(true)
    try {
      const lead = await crmLeads.create({
        nome: nome.trim(),
        telefone: telefone.trim() || null,
        email: email.trim() || null,
        empresa_texto: empresaTexto.trim() || null,
        origem: origem.trim() || null,
        notas: notas.trim() || null,
        responsavel_id: responsavelId === '' ? undefined : Number(responsavelId),
        criar_negociacao: true,
      })
      toast.showSuccess('Lead criada.')
      setModalOpen(false)
      if (lead.negociacao_ativa_id) {
        navigate(`/crm/negociacoes/${lead.negociacao_ativa_id}`)
      } else {
        if (vista === 'kanban') loadKanban()
        else loadLista()
        void loadContagens(estagios)
      }
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível criar a lead.'))
    } finally {
      setSaving(false)
    }
  }

  function abrirNegociacao(lead: Crm.Lead) {
    if (lead.negociacao_ativa_id) {
      navigate(`/crm/negociacoes/${lead.negociacao_ativa_id}`)
      return
    }
    toast.showWarning('Esta lead não tem negociação ativa.')
  }

  async function moverLeadParaEstagio(lead: Crm.Lead, destinoId: number) {
    if (!lead.negociacao_ativa_id) {
      toast.showWarning('Esta lead não tem negociação ativa para mover.')
      return
    }
    if (lead.estagio_id === destinoId) return
    setMoving(true)
    try {
      await crmNegociacoes.moverEstagio(lead.negociacao_ativa_id, { estagio_id: destinoId })
      toast.showSuccess('Estágio atualizado.')
      loadKanban()
      void loadContagens(estagios)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível mover a lead.'))
    } finally {
      setMoving(false)
      setDraggingId(null)
      setDropColId(null)
    }
  }

  function iniciarEdicaoColuna(col: Crm.FunilEstagio) {
    cancelEditColRef.current = false
    setEditingColId(col.id)
    setEditingNome(col.nome)
  }

  async function salvarNomeColuna() {
    if (cancelEditColRef.current) {
      cancelEditColRef.current = false
      return
    }
    if (editingColId == null) return
    const nomeNovo = editingNome.trim()
    if (!nomeNovo) {
      toast.showWarning('Informe o nome do estágio.')
      return
    }
    const atual = estagios.find((e) => e.id === editingColId)
    if (atual && atual.nome === nomeNovo) {
      setEditingColId(null)
      return
    }
    setSavingCol(true)
    try {
      await crmFunil.update(editingColId, { nome: nomeNovo })
      toast.showSuccess('Nome do estágio atualizado.')
      setEditingColId(null)
      loadEstagios()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível renomear o estágio.'))
    } finally {
      setSavingCol(false)
    }
  }

  async function reordenarColunas(dragId: number, targetId: number) {
    if (!isAdmin || dragId === targetId || reorderingCols) return
    const ordered = [...estagios].sort((a, b) => a.ordem - b.ordem || a.id - b.id)
    const dragged = ordered.find((e) => e.id === dragId)
    if (!dragged) return
    const without = ordered.filter((e) => e.id !== dragId)
    const targetIdx = without.findIndex((e) => e.id === targetId)
    if (targetIdx < 0) return
    without.splice(targetIdx, 0, dragged)
    const next = without.map((e, i) => ({ ...e, ordem: (i + 1) * 10 }))
    const changed = next.filter((e) => {
      const prev = estagios.find((p) => p.id === e.id)
      return !prev || prev.ordem !== e.ordem
    })
    if (!changed.length) return
    setEstagios(next)
    setReorderingCols(true)
    try {
      await Promise.all(changed.map((e) => crmFunil.update(e.id, { ordem: e.ordem })))
      toast.showSuccess('Ordem das colunas atualizada.')
      loadEstagios()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível reordenar as colunas.'))
      loadEstagios()
    } finally {
      setReorderingCols(false)
      setDraggingColId(null)
      setDropColId(null)
    }
  }

  if (forbidden) {
    return (
      <SemPermissao
        title="Você não tem permissão para acessar o CRM."
        detail="Esta área é para perfil comercial ou administrador."
        voltarPara="/"
        voltarLabel="Voltar para o Dashboard"
      />
    )
  }

  const toggleVista = (
    <div className="inline-flex rounded-lg border border-slate-200 p-0.5 dark:border-slate-700">
      <button
        type="button"
        onClick={() => mudarVista('lista')}
        className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${
          vista === 'lista'
            ? 'bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900'
            : 'text-slate-600 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-800'
        }`}
      >
        Lista
      </button>
      <button
        type="button"
        onClick={() => mudarVista('kanban')}
        className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${
          vista === 'kanban'
            ? 'bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900'
            : 'text-slate-600 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-800'
        }`}
      >
        Kanban
      </button>
    </div>
  )

  return (
    <div className={`mx-auto space-y-4 pb-10 ${vista === 'kanban' ? 'max-w-[100%]' : 'max-w-6xl'}`}>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-100">CRM — Leads</h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Funil comercial: contatos, negociações e estágios.
            {isAdmin ? (
              <>
                {' '}
                <Link
                  to="/configuracoes/comercial/funil-crm"
                  className="font-medium text-cyan-700 hover:underline dark:text-cyan-400"
                >
                  Configurar funil
                </Link>
              </>
            ) : null}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {toggleVista}
          <Button type="button" onClick={openModal}>
            Criar Lead
          </Button>
        </div>
      </div>

      {vista === 'lista' ? (
        <>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => setEstagioId('')}
              className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                estagioId === ''
                  ? 'bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-200'
              }`}
            >
              Todas
              {Object.values(contagens).length > 0
                ? ` (${Object.values(contagens).reduce((a, b) => a + b, 0)})`
                : ''}
            </button>
            {estagios.map((e) => (
              <button
                key={e.id}
                type="button"
                onClick={() => setEstagioId(e.id)}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                  estagioId === e.id
                    ? 'bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900'
                    : 'bg-slate-100 text-slate-700 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-200'
                }`}
              >
                {e.nome}
                {contagens[e.id] != null ? ` (${contagens[e.id]})` : ''}
              </button>
            ))}
          </div>

          <Card>
            <BarraBuscaPaginacao
              busca={busca}
              onBuscaChange={setBusca}
              placeholder="Buscar por nome, telefone, e-mail…"
              page={page}
              total={total}
              onPageChange={setPage}
              disabled={loading}
              extra={
                <div className="flex flex-wrap items-center gap-3">
                  <Select
                    label="Estágio"
                    labelStyle="overline"
                    value={estagioId === '' ? '' : estagioId}
                    onChange={(v) => setEstagioId(v === '' ? '' : Number(v))}
                    options={estagios.map((e) => ({
                      value: e.id,
                      label: contagens[e.id] != null ? `${e.nome} (${contagens[e.id]})` : e.nome,
                    }))}
                    includeEmpty
                    emptyLabel="Todos os estágios"
                  />
                  <label className="inline-flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
                    <input
                      type="checkbox"
                      checked={soMinhas}
                      onChange={(ev) => setSoMinhas(ev.target.checked)}
                      className="size-4 rounded border-slate-300"
                    />
                    Só as minhas
                  </label>
                </div>
              }
            />

            {loading ? (
              <p className="text-slate-500 dark:text-slate-400">Carregando…</p>
            ) : list.length === 0 ? (
              <p className="text-slate-500 dark:text-slate-400">Nenhuma lead encontrada.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[640px] text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-100 bg-slate-50/60 dark:border-slate-800 dark:bg-slate-800/40">
                      <th className="px-3 py-2 font-medium text-slate-600 dark:text-slate-300">Lead</th>
                      <th className="px-3 py-2 font-medium text-slate-600 dark:text-slate-300">Estágio</th>
                      <th className="px-3 py-2 font-medium text-slate-600 dark:text-slate-300">Contato</th>
                      <th className="px-3 py-2 font-medium text-slate-600 dark:text-slate-300">Criada</th>
                      <th className="px-3 py-2 font-medium text-slate-600 dark:text-slate-300" />
                    </tr>
                  </thead>
                  <tbody>
                    {list.map((lead) => (
                      <tr key={lead.id} className="border-b border-slate-100 dark:border-slate-800/80">
                        <td className="px-3 py-2.5">
                          <div className="font-medium text-slate-900 dark:text-slate-100">{lead.nome}</div>
                          {lead.empresa_texto ? (
                            <div className="text-xs text-slate-500">{lead.empresa_texto}</div>
                          ) : null}
                          {lead.origem ? (
                            <div className="text-xs text-slate-400">Origem: {lead.origem}</div>
                          ) : null}
                        </td>
                        <td className="px-3 py-2.5 text-slate-700 dark:text-slate-300">
                          {lead.estagio_nome || '—'}
                        </td>
                        <td className="px-3 py-2.5 text-slate-600 dark:text-slate-400">
                          <div>{lead.telefone || '—'}</div>
                          <div className="text-xs">{lead.email || ''}</div>
                        </td>
                        <td className="px-3 py-2.5 text-slate-500">{formatDate(lead.created_at)}</td>
                        <td className="px-3 py-2.5 text-right">
                          <Button variant="secondary" onClick={() => abrirNegociacao(lead)}>
                            Abrir
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </>
      ) : (
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-3">
            <div className="min-w-[240px] flex-1 max-w-sm">
              <input
                type="search"
                value={busca}
                onChange={(e) => setBusca(e.target.value)}
                placeholder="Buscar por nome, telefone, e-mail…"
                aria-label="Buscar leads"
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500 dark:border-slate-600 dark:bg-slate-900/50 dark:text-slate-100"
              />
            </div>
            <label className="inline-flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
              <input
                type="checkbox"
                checked={soMinhas}
                onChange={(ev) => setSoMinhas(ev.target.checked)}
                className="size-4 rounded border-slate-300"
              />
              Só as minhas
            </label>
            {moving || reorderingCols ? (
              <span className="text-xs text-slate-500">Atualizando…</span>
            ) : null}
            <p className="text-xs text-slate-500">
              Arraste os cartões entre colunas
              {isAdmin ? ' · ≡ no cabeçalho reordena · lápis renomeia' : ''}.
            </p>
          </div>

          {loading ? (
            <p className="text-slate-500">Carregando Kanban…</p>
          ) : (
            <div className="dx-scrollbar -mx-1 flex gap-3 overflow-x-auto px-1 pb-3">
              {estagios.map((col) => {
                const cards = porEstagio.get(col.id) || []
                const isDropTarget = dropColId === col.id && (draggingId != null || draggingColId != null)
                const editing = editingColId === col.id
                return (
                  <div
                    key={col.id}
                    className={`flex w-72 shrink-0 flex-col rounded-xl border bg-slate-50/80 transition dark:bg-slate-900/50 ${
                      isDropTarget
                        ? 'border-cyan-400/80 ring-1 ring-cyan-400/40 dark:border-cyan-500/70'
                        : 'border-slate-200/90 dark:border-slate-700/80'
                    } ${draggingColId === col.id ? 'opacity-60' : ''}`}
                    onDragOver={(e) => {
                      e.preventDefault()
                      const isCol = e.dataTransfer.types.includes(DND_COL)
                      const isLead =
                        e.dataTransfer.types.includes(DND_LEAD) || e.dataTransfer.types.includes('text/plain')
                      if (isCol || isLead) {
                        e.dataTransfer.dropEffect = 'move'
                        setDropColId(col.id)
                      }
                    }}
                    onDragLeave={() => {
                      setDropColId((cur) => (cur === col.id ? null : cur))
                    }}
                    onDrop={(e) => {
                      e.preventDefault()
                      setDropColId(null)
                      const colRaw = e.dataTransfer.getData(DND_COL)
                      if (colRaw && isAdmin) {
                        void reordenarColunas(Number(colRaw), col.id)
                        return
                      }
                      const leadRaw = e.dataTransfer.getData(DND_LEAD) || e.dataTransfer.getData('text/plain')
                      const leadId = Number(leadRaw)
                      const lead = kanbanLeads.find((l) => l.id === leadId)
                      if (lead) void moverLeadParaEstagio(lead, col.id)
                    }}
                  >
                    <div className="flex items-center gap-1.5 border-b border-slate-200/80 px-2 py-2 dark:border-slate-700/80">
                      {isAdmin ? (
                        <button
                          type="button"
                          draggable={!reorderingCols && !editing}
                          onDragStart={(e) => {
                            setDraggingColId(col.id)
                            e.dataTransfer.setData(DND_COL, String(col.id))
                            e.dataTransfer.effectAllowed = 'move'
                          }}
                          onDragEnd={() => {
                            setDraggingColId(null)
                            setDropColId(null)
                          }}
                          className="cursor-grab rounded px-1 py-0.5 text-slate-400 hover:bg-slate-200/70 hover:text-slate-600 active:cursor-grabbing dark:hover:bg-slate-800 dark:hover:text-slate-200"
                          aria-label={`Reordenar coluna ${col.nome}`}
                          title="Arrastar para reordenar"
                        >
                          ≡
                        </button>
                      ) : null}
                      <div className="min-w-0 flex-1">
                        {editing ? (
                          <input
                            autoFocus
                            value={editingNome}
                            disabled={savingCol}
                            onChange={(e) => setEditingNome(e.target.value)}
                            onBlur={() => void salvarNomeColuna()}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') {
                                e.preventDefault()
                                void salvarNomeColuna()
                              }
                              if (e.key === 'Escape') {
                                cancelEditColRef.current = true
                                setEditingColId(null)
                              }
                            }}
                            className="w-full rounded-md border border-cyan-500/60 bg-white px-1.5 py-0.5 text-sm font-semibold text-slate-900 focus:outline-none dark:bg-slate-950 dark:text-slate-100"
                            aria-label="Nome do estágio"
                          />
                        ) : (
                          <h2 className="truncate text-sm font-semibold text-slate-800 dark:text-slate-100">
                            {col.nome}
                          </h2>
                        )}
                      </div>
                      <span className="shrink-0 rounded-md bg-slate-200/80 px-1.5 py-0.5 text-[11px] font-medium tabular-nums text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                        {contagens[col.id] ?? cards.length}
                      </span>
                      {isAdmin && !editing ? (
                        <button
                          type="button"
                          onClick={() => iniciarEdicaoColuna(col)}
                          className="rounded p-1 text-slate-400 hover:bg-slate-200/70 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200"
                          aria-label={`Editar nome de ${col.nome}`}
                          title="Renomear estágio"
                        >
                          <IconPencil className="size-3.5" />
                        </button>
                      ) : null}
                    </div>
                    <div className="dx-scrollbar flex max-h-[min(70vh,560px)] flex-col gap-2 overflow-y-auto p-2">
                      {cards.length === 0 ? (
                        <div className="rounded-lg border border-dashed border-slate-200 px-2 py-8 text-center text-xs text-slate-400 dark:border-slate-700">
                          Sem leads
                        </div>
                      ) : (
                        cards.map((lead) => (
                          <button
                            key={lead.id}
                            type="button"
                            draggable={!moving && !reorderingCols}
                            onDragStart={(e) => {
                              setDraggingId(lead.id)
                              e.dataTransfer.setData(DND_LEAD, String(lead.id))
                              e.dataTransfer.setData('text/plain', String(lead.id))
                              e.dataTransfer.effectAllowed = 'move'
                            }}
                            onDragEnd={() => {
                              setDraggingId(null)
                              setDropColId(null)
                            }}
                            onClick={() => abrirNegociacao(lead)}
                            className={`rounded-lg border border-slate-200/90 bg-white p-3 text-left shadow-sm transition hover:border-cyan-400/50 hover:shadow dark:border-slate-600/80 dark:bg-slate-800/90 ${
                              draggingId === lead.id ? 'opacity-50' : ''
                            }`}
                          >
                            <div className="font-medium text-slate-900 dark:text-slate-100">{lead.nome}</div>
                            {lead.empresa_texto ? (
                              <div className="mt-0.5 truncate text-xs text-slate-500">{lead.empresa_texto}</div>
                            ) : null}
                            <div className="mt-2 flex flex-wrap gap-2 text-xs text-slate-500">
                              {lead.telefone ? <span>{lead.telefone}</span> : null}
                              {lead.origem ? <span>· {lead.origem}</span> : null}
                            </div>
                            <div className="mt-1 text-[11px] text-slate-400">{formatDate(lead.created_at)}</div>
                          </button>
                        ))
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {modalOpen ? (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-0 sm:items-center sm:p-4">
          <div className="max-h-[92vh] w-full overflow-y-auto rounded-t-2xl bg-white p-5 shadow-xl dark:bg-slate-900 sm:max-w-lg sm:rounded-2xl">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Criar Lead</h2>
            <p className="mt-1 text-sm text-slate-500">Cria também a negociação inicial automaticamente.</p>
            <form onSubmit={handleCreate} className="mt-4 space-y-3">
              <Input label="Nome" value={nome} onChange={(e) => setNome(e.target.value)} required />
              <Input label="Telefone" value={telefone} onChange={(e) => setTelefone(e.target.value)} />
              <Input label="E-mail" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
              <Input
                label="Empresa / prospecto"
                value={empresaTexto}
                onChange={(e) => setEmpresaTexto(e.target.value)}
              />
              <Input
                label="Origem"
                value={origem}
                onChange={(e) => setOrigem(e.target.value)}
                placeholder="WhatsApp, indicação…"
              />
              <Input label="Observações" value={notas} onChange={(e) => setNotas(e.target.value)} />
              {isAdmin && responsaveis.length > 0 ? (
                <Select
                  label="Responsável"
                  value={responsavelId === '' ? '' : String(responsavelId)}
                  onChange={(v) => setResponsavelId(v === '' ? '' : Number(v))}
                  options={[
                    { value: '', label: 'Eu (usuário atual)' },
                    ...responsaveis.map((a) => ({ value: String(a.id), label: a.nome })),
                  ]}
                />
              ) : null}
              <div className="flex flex-wrap justify-end gap-2 pt-2">
                <Button type="button" variant="secondary" onClick={() => setModalOpen(false)} disabled={saving}>
                  Cancelar
                </Button>
                <Button type="submit" disabled={saving}>
                  {saving ? 'Salvando…' : 'Criar e abrir negociação'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </div>
  )
}
