import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError, setores, sla, type Sla } from '../api/client'
import { HorarioSemanaEditor } from '../components/horario/HorarioSemanaEditor'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { ConfigListPageShell } from '../components/config/ConfigListPageShell'
import { FiltroInativos } from '../components/ui/FiltroInativos'
import { Switch } from '../components/ui/Switch'
import { useToast } from '../components/ui/Toast'
import { SemPermissao } from './SemPermissao'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import {
  horarioSemanaFromApi,
  horarioSemanaPadrao,
  validarHorarioSemana,
  type HorarioSemana,
} from '../lib/horarioSemana'

type FormState = {
  nome: string
  setor_id: number | null
  horario_timezone: string
  horario_semana: HorarioSemana
  usar_feriados_nacionais: boolean
  ativo: boolean
}

function formVazio(): FormState {
  return {
    nome: '',
    setor_id: null,
    horario_timezone: 'America/Sao_Paulo',
    horario_semana: horarioSemanaPadrao(),
    usar_feriados_nacionais: false,
    ativo: true,
  }
}

function resumoHorario(c: Sla.BusinessCalendar): string {
  const hs = c.horario_semana
  if (hs) {
    const abertos = Object.values(hs).filter((d) => d?.ativo).length
    return abertos > 0 ? `${abertos} dia(s) na semana` : 'Sem dias abertos'
  }
  if (c.horario_inicio && c.horario_fim) {
    return `${c.horario_inicio}–${c.horario_fim}`
  }
  return '—'
}

export function SlaCalendariosPage({ embedded = false }: { embedded?: boolean }) {
  const toast = useToast()
  const [list, setList] = useState<Sla.BusinessCalendar[]>([])
  const [setorOpts, setSetorOpts] = useState<{ id: number; nome: string }[]>([])
  const [loading, setLoading] = useState(true)
  const [forbidden, setForbidden] = useState(false)
  const [incluirInativos, setIncluirInativos] = useState(false)

  const [editId, setEditId] = useState<number | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const [form, setForm] = useState<FormState>(formVazio())
  const [saving, setSaving] = useState(false)

  const load = useCallback(() => {
    setLoading(true)
    setForbidden(false)
    sla.calendars
      .list({ incluir_inativos: incluirInativos })
      .then(setList)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 403) {
          setForbidden(true)
          setList([])
          return
        }
        toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível carregar os calendários.'))
      })
      .finally(() => setLoading(false))
  }, [incluirInativos, toast])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    setores.list({ limit: 100 }).then(({ items }) => {
      setSetorOpts(items.map((s) => ({ id: s.id, nome: s.nome })))
    })
  }, [])

  function iniciarNova() {
    setEditId(null)
    setForm(formVazio())
    setFormOpen(true)
  }

  function iniciarEdicao(cal: Sla.BusinessCalendar) {
    setEditId(cal.id)
    setForm({
      nome: cal.nome,
      setor_id: cal.setor_id,
      horario_timezone: cal.horario_timezone || 'America/Sao_Paulo',
      horario_semana: horarioSemanaFromApi(cal.horario_semana ?? undefined),
      usar_feriados_nacionais: cal.usar_feriados_nacionais,
      ativo: cal.ativo,
    })
    setFormOpen(true)
  }

  function cancelarForm() {
    setEditId(null)
    setFormOpen(false)
    setForm(formVazio())
  }

  async function salvar() {
    const nome = form.nome.trim()
    if (!nome) {
      toast.showWarning('Informe o nome do calendário.')
      return
    }
    const erroHorario = validarHorarioSemana(form.horario_semana)
    if (erroHorario) {
      toast.showWarning(erroHorario)
      return
    }

    const payload = {
      nome,
      setor_id: form.setor_id,
      horario_timezone: form.horario_timezone.trim() || 'America/Sao_Paulo',
      horario_semana: form.horario_semana,
      horario_inicio: null as string | null,
      horario_fim: null as string | null,
      usar_feriados_nacionais: form.usar_feriados_nacionais,
      ativo: form.ativo,
    }

    setSaving(true)
    try {
      if (editId) {
        await sla.calendars.update(editId, payload)
        toast.showSuccess('Calendário atualizado.')
      } else {
        await sla.calendars.create(payload)
        toast.showSuccess('Calendário criado.')
      }
      cancelarForm()
      load()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível salvar o calendário.'))
    } finally {
      setSaving(false)
    }
  }

  async function desativar(cal: Sla.BusinessCalendar) {
    if (!window.confirm(`Desativar o calendário «${cal.nome}»? Políticas novas não poderão vinculá-lo.`)) return
    try {
      await sla.calendars.update(cal.id, { ativo: false })
      toast.showSuccess('Calendário desativado.')
      if (editId === cal.id) cancelarForm()
      load()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível desativar.'))
    }
  }

  const denied = (
    <SemPermissao
      title="Você não tem permissão para gerenciar calendários SLA."
      voltarPara="/"
      voltarLabel="Voltar para o Dashboard"
    />
  )

  return (
    <ConfigListPageShell
      embedded={embedded}
      forbidden={forbidden}
      denied={denied}
      title="Calendários comerciais"
      subtitle="Horário útil compartilhado entre políticas SLA (minutos contam só dentro destes intervalos)."
      actions={<Button onClick={iniciarNova}>Novo calendário</Button>}
    >
      <p className="text-sm text-slate-600 dark:text-slate-400 mb-4">
        Vincule calendários em{' '}
        <Link to="/configuracoes/equipa/sla/politicas" className="text-sky-600 hover:underline dark:text-sky-400">
          Políticas SLA
        </Link>
        . Calendários inativos não aparecem em novos vínculos.
      </p>

      <div className="mb-4">
        <FiltroInativos incluirInativos={incluirInativos} onChange={setIncluirInativos} />
      </div>

      <Card className="mb-6 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 dark:border-slate-800 text-left">
              <th className="p-2">Nome</th>
              <th className="p-2">Setor</th>
              <th className="p-2">Fuso</th>
              <th className="p-2">Horário</th>
              <th className="p-2">Feriados BR</th>
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
                  Nenhum calendário cadastrado.
                </td>
              </tr>
            ) : (
              list.map((c) => (
                <tr key={c.id} className="border-b border-slate-100 dark:border-slate-800">
                  <td className="p-2 font-medium">
                    {c.nome}
                    {!c.ativo ? (
                      <span className="ml-2 text-xs text-amber-600 dark:text-amber-400">inativo</span>
                    ) : null}
                  </td>
                  <td className="p-2 text-slate-600 dark:text-slate-400">
                    {c.setor_id
                      ? (setorOpts.find((s) => s.id === c.setor_id)?.nome ?? `#${c.setor_id}`)
                      : 'Todos os setores'}
                  </td>
                  <td className="p-2 text-slate-600 dark:text-slate-400">{c.horario_timezone}</td>
                  <td className="p-2 text-slate-600 dark:text-slate-400">{resumoHorario(c)}</td>
                  <td className="p-2">{c.usar_feriados_nacionais ? 'Sim' : 'Não'}</td>
                  <td className="p-2">
                    <Button type="button" variant="ghost" className="px-2 py-1" onClick={() => iniciarEdicao(c)}>
                      Editar
                    </Button>
                    {c.ativo ? (
                      <Button type="button" variant="ghost" className="px-2 py-1" onClick={() => desativar(c)}>
                        Desativar
                      </Button>
                    ) : null}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </Card>

      {formOpen ? (
        <Card className="mb-6 p-4 space-y-4">
          <h3 className="font-semibold">{editId ? 'Editar calendário' : 'Novo calendário'}</h3>

          <div className="grid gap-3 md:grid-cols-2">
            <label className="block text-sm md:col-span-2">
              Nome
              <input
                className="mt-1 w-full rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 px-2 py-1.5"
                value={form.nome}
                onChange={(e) => setForm((f) => ({ ...f, nome: e.target.value }))}
                maxLength={120}
              />
            </label>
            <label className="block text-sm">
              Setor (opcional)
              <select
                className="mt-1 w-full rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 px-2 py-1.5"
                value={form.setor_id ?? ''}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    setor_id: e.target.value ? Number(e.target.value) : null,
                  }))
                }
              >
                <option value="">Compartilhado (todos os setores)</option>
                {setorOpts.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.nome}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm">
              Fuso horário (IANA)
              <input
                className="mt-1 w-full rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 px-2 py-1.5"
                value={form.horario_timezone}
                onChange={(e) => setForm((f) => ({ ...f, horario_timezone: e.target.value }))}
                placeholder="America/Sao_Paulo"
              />
            </label>
          </div>

          <Switch
            checked={form.usar_feriados_nacionais}
            onCheckedChange={(v) => setForm((f) => ({ ...f, usar_feriados_nacionais: v }))}
            label="Considerar feriados nacionais"
            description="Feriados nacionais (Brasil) contam como dia fechado."
            showStatusPill
            statusOnText="Ativo"
            statusOffText="Inativo"
          />

          <HorarioSemanaEditor
            value={form.horario_semana}
            onChange={(horario_semana) => setForm((f) => ({ ...f, horario_semana }))}
          />

          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.ativo}
              onChange={(e) => setForm((f) => ({ ...f, ativo: e.target.checked }))}
            />
            Calendário ativo
          </label>

          <div className="flex gap-2">
            <Button onClick={salvar} disabled={saving}>
              {saving ? 'Salvando…' : 'Salvar'}
            </Button>
            <Button type="button" variant="cancel" onClick={cancelarForm}>
              Cancelar
            </Button>
          </div>
        </Card>
      ) : null}
    </ConfigListPageShell>
  )
}
