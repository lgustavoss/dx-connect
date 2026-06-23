import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError, setores, sla, type Sla } from '../api/client'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { ConfigListPageShell } from '../components/config/ConfigListPageShell'
import { FiltroInativos } from '../components/ui/FiltroInativos'
import { useToast } from '../components/ui/Toast'
import { SemPermissao } from './SemPermissao'
import { mensagemFalhaParaToast } from '../api/errorMessage'

const PRIORIDADE_LABELS: Record<Sla.Prioridade, string> = {
  baixa: 'Baixa',
  normal: 'Normal',
  alta: 'Alta',
  urgente: 'Urgente',
}

function formatMinutosSla(min: number | null | undefined, comercial: boolean): string {
  if (min == null || min <= 0) return '—'
  const suf = comercial ? ' úteis' : ''
  if (min < 60) return `${min} min${suf}`
  const h = Math.floor(min / 60)
  const rest = min % 60
  if (rest === 0) return `${h}h${suf}`
  return `${h}h ${rest}min${suf}`
}

function formVazio(): Sla.PolicyCreate {
  return {
    setor_id: 0,
    prioridade: null,
    business_calendar_id: null,
    meta_primeira_resposta_min: 60,
    meta_resolucao_min: 480,
    ativo: true,
  }
}

function buildPreview(
  form: Sla.PolicyCreate,
  prioridade: Sla.Prioridade | null | undefined,
): string {
  const prioLabel = prioridade ? PRIORIDADE_LABELS[prioridade] : 'padrão'
  const comercial = !!form.business_calendar_id
  const p1 = formatMinutosSla(form.meta_primeira_resposta_min, comercial)
  const p2 = formatMinutosSla(form.meta_resolucao_min, comercial)
  return `Exemplo: Prioridade ${prioLabel} = ${p1} primeira resposta / ${p2} resolução`
}

export function SlaPoliticasPage({ embedded = false }: { embedded?: boolean }) {
  const toast = useToast()
  const [list, setList] = useState<Sla.Policy[]>([])
  const [calendars, setCalendars] = useState<Sla.BusinessCalendar[]>([])
  const [prioridades, setPrioridades] = useState<Sla.Prioridade[]>([])
  const [loading, setLoading] = useState(true)
  const [forbidden, setForbidden] = useState(false)
  const [incluirInativos, setIncluirInativos] = useState(false)
  const [filtroSetor, setFiltroSetor] = useState<number | ''>('')
  const [setorOpts, setSetorOpts] = useState<{ id: number; nome: string }[]>([])

  const [editId, setEditId] = useState<number | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const [form, setForm] = useState<Sla.PolicyCreate>(formVazio())
  const [saving, setSaving] = useState(false)

  const preview = useMemo(() => buildPreview(form, form.prioridade), [form])

  const load = useCallback(() => {
    setLoading(true)
    setForbidden(false)
    sla.policies
      .list({
        incluir_inativos: incluirInativos,
        setor_id: filtroSetor === '' ? undefined : filtroSetor,
      })
      .then(setList)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 403) {
          setForbidden(true)
          setList([])
          return
        }
        toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível carregar as políticas SLA.'))
      })
      .finally(() => setLoading(false))
  }, [filtroSetor, incluirInativos, toast])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    setores.list({ limit: 100 }).then(({ items }) => {
      const opts = items.map((s) => ({ id: s.id, nome: s.nome }))
      setSetorOpts(opts)
      setForm((f) => (f.setor_id ? f : { ...f, setor_id: opts[0]?.id ?? 0 }))
    })
    sla.prioridades().then((r) => setPrioridades(r.prioridades))
    sla.calendars.list({ incluir_inativos: true }).then(setCalendars).catch(() => setCalendars([]))
  }, [])

  function iniciarNova() {
    setEditId(null)
    setForm({
      ...formVazio(),
      setor_id: setorOpts[0]?.id ?? 0,
    })
    setFormOpen(true)
  }

  function iniciarEdicao(policy: Sla.Policy) {
    setEditId(policy.id)
    setForm({
      setor_id: policy.setor_id,
      prioridade: policy.prioridade,
      business_calendar_id: policy.business_calendar_id,
      meta_primeira_resposta_min: policy.meta_primeira_resposta_min,
      meta_resolucao_min: policy.meta_resolucao_min,
      ativo: policy.ativo,
    })
    setFormOpen(true)
  }

  function cancelarForm() {
    setEditId(null)
    setFormOpen(false)
    setForm(formVazio())
  }

  async function salvar() {
    if (!form.setor_id) {
      toast.showWarning('Selecione o setor.')
      return
    }
    const primeira = form.meta_primeira_resposta_min
    const resolucao = form.meta_resolucao_min
    if ((!primeira || primeira <= 0) && (!resolucao || resolucao <= 0)) {
      toast.showWarning('Informe ao menos uma meta com minutos maior que zero.')
      return
    }
    if (primeira != null && primeira <= 0) {
      toast.showWarning('Minutos de primeira resposta devem ser maiores que zero.')
      return
    }
    if (resolucao != null && resolucao <= 0) {
      toast.showWarning('Minutos de resolução devem ser maiores que zero.')
      return
    }

    setSaving(true)
    try {
      const payload = {
        ...form,
        prioridade: form.prioridade || null,
        business_calendar_id: form.business_calendar_id || null,
        meta_primeira_resposta_min: primeira && primeira > 0 ? primeira : null,
        meta_resolucao_min: resolucao && resolucao > 0 ? resolucao : null,
      }
      if (editId) {
        await sla.policies.update(editId, payload)
        toast.showSuccess('Política atualizada.')
      } else {
        await sla.policies.create(payload)
        toast.showSuccess('Política criada.')
      }
      cancelarForm()
      load()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível salvar a política.'))
    } finally {
      setSaving(false)
    }
  }

  async function desativar(policy: Sla.Policy) {
    if (!window.confirm(`Desativar a política SLA do setor ${policy.setor_nome ?? policy.setor_id}?`)) return
    try {
      await sla.policies.update(policy.id, { ativo: false })
      toast.showSuccess('Política desativada.')
      if (editId === policy.id) cancelarForm()
      load()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível desativar.'))
    }
  }

  const denied = (
    <SemPermissao
      title="Você não tem permissão para gerenciar SLA."
      voltarPara="/"
      voltarLabel="Voltar para o Dashboard"
    />
  )

  return (
    <ConfigListPageShell
      embedded={embedded}
      forbidden={forbidden}
      denied={denied}
      title="SLA"
      subtitle="Metas de primeira resposta e resolução por setor e prioridade."
      actions={<Button onClick={iniciarNova}>Nova política</Button>}
    >
      <div className="flex flex-wrap items-center gap-3 mb-4">
        <FiltroInativos incluirInativos={incluirInativos} onChange={setIncluirInativos} />
        <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
          Setor
          <select
            className="rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 px-2 py-1.5 text-sm"
            value={filtroSetor}
            onChange={(e) => setFiltroSetor(e.target.value ? Number(e.target.value) : '')}
          >
            <option value="">Todos</option>
            {setorOpts.map((s) => (
              <option key={s.id} value={s.id}>
                {s.nome}
              </option>
            ))}
          </select>
        </label>
      </div>

      <Card className="mb-6 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 dark:border-slate-700 text-left">
              <th className="p-2">Setor</th>
              <th className="p-2">Prioridade</th>
              <th className="p-2">Primeira resposta</th>
              <th className="p-2">Resolução</th>
              <th className="p-2">Calendário</th>
              <th className="p-2 w-36" />
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={6} className="p-4 text-slate-500">
                  Carregando…
                </td>
              </tr>
            ) : list.length === 0 ? (
              <tr>
                <td colSpan={6} className="p-4 text-slate-500">
                  Nenhuma política cadastrada.
                </td>
              </tr>
            ) : (
              list.map((p) => {
                const comercial = !!p.business_calendar_id
                return (
                  <tr key={p.id} className="border-b border-slate-100 dark:border-slate-800">
                    <td className="p-2 font-medium">{p.setor_nome ?? `#${p.setor_id}`}</td>
                    <td className="p-2">
                      {p.prioridade ? PRIORIDADE_LABELS[p.prioridade] : 'Padrão'}
                      {!p.ativo ? (
                        <span className="ml-2 text-xs text-amber-600 dark:text-amber-400">inativa</span>
                      ) : null}
                    </td>
                    <td className="p-2">{formatMinutosSla(p.meta_primeira_resposta_min, comercial)}</td>
                    <td className="p-2">{formatMinutosSla(p.meta_resolucao_min, comercial)}</td>
                    <td className="p-2 text-slate-600 dark:text-slate-400">
                      {p.business_calendar_nome ?? (comercial ? '—' : '24×7')}
                    </td>
                    <td className="p-2">
                      <Button type="button" variant="ghost" className="px-2 py-1" onClick={() => iniciarEdicao(p)}>
                        Editar
                      </Button>
                      {p.ativo ? (
                        <Button type="button" variant="ghost" className="px-2 py-1" onClick={() => desativar(p)}>
                          Desativar
                        </Button>
                      ) : null}
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </Card>

      {formOpen ? (
        <Card className="mb-6 p-4 space-y-4">
          <h3 className="font-semibold">{editId ? 'Editar política' : 'Nova política'}</h3>

          <div className="grid gap-3 md:grid-cols-2">
            <label className="block text-sm">
              Setor
              <select
                className="mt-1 w-full rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 px-2 py-1.5"
                value={form.setor_id || ''}
                onChange={(e) => setForm((f) => ({ ...f, setor_id: Number(e.target.value) }))}
              >
                {setorOpts.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.nome}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm">
              Prioridade
              <select
                className="mt-1 w-full rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 px-2 py-1.5"
                value={form.prioridade ?? ''}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    prioridade: (e.target.value || null) as Sla.Prioridade | null,
                  }))
                }
              >
                <option value="">Padrão (qualquer prioridade sem regra específica)</option>
                {prioridades.map((p) => (
                  <option key={p} value={p}>
                    {PRIORIDADE_LABELS[p]}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm">
              Primeira resposta (minutos)
              <input
                type="number"
                min={1}
                className="mt-1 w-full rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 px-2 py-1.5"
                value={form.meta_primeira_resposta_min ?? ''}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    meta_primeira_resposta_min: e.target.value ? Number(e.target.value) : null,
                  }))
                }
              />
            </label>
            <label className="block text-sm">
              Resolução (minutos)
              <input
                type="number"
                min={1}
                className="mt-1 w-full rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 px-2 py-1.5"
                value={form.meta_resolucao_min ?? ''}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    meta_resolucao_min: e.target.value ? Number(e.target.value) : null,
                  }))
                }
              />
            </label>
            <label className="block text-sm md:col-span-2">
              Calendário comercial
              <select
                className="mt-1 w-full rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 px-2 py-1.5"
                value={form.business_calendar_id ?? ''}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    business_calendar_id: e.target.value ? Number(e.target.value) : null,
                  }))
                }
              >
                <option value="">Sem calendário (contagem contínua 24×7)</option>
                {calendars
                  .filter((c) => c.ativo || c.id === form.business_calendar_id)
                  .map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.nome}
                    {!c.ativo ? ' (inativo)' : ''}
                  </option>
                ))}
              </select>
              <span className="mt-1 block text-xs text-slate-500 dark:text-slate-400">
                Gerencie calendários em{' '}
                <Link to="/configuracoes/atendimento/sla/calendarios" className="text-sky-600 hover:underline dark:text-sky-400">
                  SLA → Calendários
                </Link>
                . Apenas calendários ativos podem ser vinculados em novas políticas.
              </span>
            </label>
          </div>

          <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700 dark:border-slate-700 dark:bg-slate-800/50 dark:text-slate-200">
            {preview}
          </div>

          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.ativo !== false}
              onChange={(e) => setForm((f) => ({ ...f, ativo: e.target.checked }))}
            />
            Política ativa
          </label>

          <div className="flex gap-2">
            <Button onClick={salvar} disabled={saving}>
              {saving ? 'Salvando…' : 'Salvar'}
            </Button>
            <Button type="button" variant="ghost" onClick={cancelarForm}>
              Cancelar
            </Button>
          </div>
        </Card>
      ) : null}
    </ConfigListPageShell>
  )
}
