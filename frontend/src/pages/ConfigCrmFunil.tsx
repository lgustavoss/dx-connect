import { useCallback, useEffect, useState } from 'react'
import { ApiError, crmFunil, type Crm } from '../api/client'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Input } from '../components/ui/Input'
import { Select } from '../components/ui/Select'
import { Switch } from '../components/ui/Switch'
import { FiltroInativos } from '../components/ui/FiltroInativos'
import { IconPencil } from '../components/ui/IconPencil'
import { useToast } from '../components/ui/Toast'
import { ConfigListPageShell } from '../components/config/ConfigListPageShell'
import { SemPermissao } from './SemPermissao'

const TIPO_OPTIONS = [
  { value: 'aberto', label: 'Aberto (em andamento)' },
  { value: 'ganho', label: 'Ganho' },
  { value: 'perdido', label: 'Perdido' },
]

const TIPO_LABEL: Record<string, string> = {
  aberto: 'Aberto',
  ganho: 'Ganho',
  perdido: 'Perdido',
}

function slugify(nome: string): string {
  return nome
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_|_$/g, '')
    .slice(0, 50)
}

type FormState = {
  nome: string
  slug: string
  ordem: string
  tipo: string
  ativo: boolean
}

const emptyForm = (): FormState => ({
  nome: '',
  slug: '',
  ordem: '100',
  tipo: 'aberto',
  ativo: true,
})

export function ConfigCrmFunil({ embedded = false }: { embedded?: boolean }) {
  const toast = useToast()
  const [list, setList] = useState<Crm.FunilEstagio[]>([])
  const [loading, setLoading] = useState(true)
  const [forbidden, setForbidden] = useState(false)
  const [incluirInativos, setIncluirInativos] = useState(false)
  const [modal, setModal] = useState<'create' | Crm.FunilEstagio | null>(null)
  const [form, setForm] = useState<FormState>(emptyForm())
  const [saving, setSaving] = useState(false)

  const load = useCallback(() => {
    setLoading(true)
    setForbidden(false)
    crmFunil
      .list({ incluir_inativos: incluirInativos })
      .then(setList)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 403) {
          setForbidden(true)
          setList([])
          return
        }
        toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível carregar o funil.'))
        setList([])
      })
      .finally(() => setLoading(false))
  }, [incluirInativos, toast])

  useEffect(() => {
    load()
  }, [load])

  function openCreate() {
    const maxOrdem = list.reduce((m, e) => Math.max(m, e.ordem), 0)
    setForm({ ...emptyForm(), ordem: String(maxOrdem + 10) })
    setModal('create')
  }

  function openEdit(row: Crm.FunilEstagio) {
    setForm({
      nome: row.nome,
      slug: row.slug,
      ordem: String(row.ordem),
      tipo: row.tipo,
      ativo: row.ativo,
    })
    setModal(row)
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    if (!form.nome.trim()) {
      toast.showWarning('Informe o nome do estágio.')
      return
    }
    setSaving(true)
    try {
      if (modal === 'create') {
        const slug = form.slug.trim() || slugify(form.nome)
        if (!slug) {
          toast.showWarning('Não foi possível gerar o identificador (slug). Ajuste o nome.')
          return
        }
        await crmFunil.create({
          nome: form.nome.trim(),
          slug,
          ordem: parseInt(form.ordem, 10) || 0,
          tipo: form.tipo,
          ativo: form.ativo,
        })
        toast.showSuccess('Estágio criado.')
      } else if (modal && typeof modal === 'object') {
        await crmFunil.update(modal.id, {
          nome: form.nome.trim(),
          ordem: parseInt(form.ordem, 10) || 0,
          tipo: form.tipo,
          ativo: form.ativo,
        })
        toast.showSuccess('Estágio atualizado.')
      }
      setModal(null)
      load()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível salvar o estágio.'))
    } finally {
      setSaving(false)
    }
  }

  const denied = (
    <SemPermissao
      title="Você não tem permissão para configurar o funil CRM."
      detail="Apenas administradores gerem os estágios do funil."
      voltarPara="/"
      voltarLabel="Voltar para o Dashboard"
    />
  )

  return (
    <ConfigListPageShell
      embedded={embedded}
      forbidden={forbidden}
      denied={denied}
      title="Funil CRM"
      actions={<Button onClick={openCreate}>Novo estágio</Button>}
    >
      <p className="mb-3 text-sm text-slate-500 dark:text-slate-400">
        Os estágios padrão (Lead, Em negociação, Documentação…) já vêm no sistema. Aqui você pode renomear, reordenar,
        desativar ou criar novos — o Kanban e a lista do CRM usam esta configuração.
      </p>
      <Card>
        <div className="mb-3">
          <FiltroInativos incluirInativos={incluirInativos} onChange={setIncluirInativos} />
        </div>
        {loading ? (
          <p className="text-slate-500">Carregando…</p>
        ) : list.length === 0 ? (
          <p className="text-slate-500">Nenhum estágio encontrado.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[560px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/60 dark:border-slate-800 dark:bg-slate-800/40">
                  <th className="px-3 py-2 font-medium text-slate-600 dark:text-slate-300">Ordem</th>
                  <th className="px-3 py-2 font-medium text-slate-600 dark:text-slate-300">Nome</th>
                  <th className="px-3 py-2 font-medium text-slate-600 dark:text-slate-300">Tipo</th>
                  <th className="px-3 py-2 font-medium text-slate-600 dark:text-slate-300">Identificador</th>
                  <th className="px-3 py-2 font-medium text-slate-600 dark:text-slate-300">Ativo</th>
                  <th className="px-3 py-2" />
                </tr>
              </thead>
              <tbody>
                {list.map((row) => (
                  <tr key={row.id} className="border-b border-slate-100 dark:border-slate-800/80">
                    <td className="px-3 py-2.5 text-slate-600">{row.ordem}</td>
                    <td className="px-3 py-2.5 font-medium text-slate-900 dark:text-slate-100">{row.nome}</td>
                    <td className="px-3 py-2.5 text-slate-600">{TIPO_LABEL[row.tipo] || row.tipo}</td>
                    <td className="px-3 py-2.5 font-mono text-xs text-slate-500">{row.slug}</td>
                    <td className="px-3 py-2.5">{row.ativo ? 'Sim' : 'Não'}</td>
                    <td className="px-3 py-2.5 text-right">
                      <button
                        type="button"
                        onClick={() => openEdit(row)}
                        className="inline-flex size-8 items-center justify-center rounded-md text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
                        aria-label={`Editar ${row.nome}`}
                      >
                        <IconPencil />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {modal ? (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-0 sm:items-center sm:p-4">
          <div className="max-h-[92vh] w-full overflow-y-auto rounded-t-2xl bg-white p-5 shadow-xl dark:bg-slate-900 sm:max-w-md sm:rounded-2xl">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              {modal === 'create' ? 'Novo estágio' : 'Editar estágio'}
            </h2>
            <form onSubmit={handleSave} className="mt-4 space-y-3">
              <Input
                label="Nome"
                value={form.nome}
                onChange={(e) => {
                  const nome = e.target.value
                  setForm((p) => ({
                    ...p,
                    nome,
                    slug: modal === 'create' ? slugify(nome) : p.slug,
                  }))
                }}
                required
              />
              {modal === 'create' ? (
                <Input
                  label="Identificador (slug)"
                  value={form.slug}
                  onChange={(e) => setForm((p) => ({ ...p, slug: e.target.value }))}
                  hint="Usado internamente; gerado a partir do nome."
                />
              ) : (
                <p className="text-xs text-slate-500">
                  Identificador: <span className="font-mono">{form.slug}</span> (não editável)
                </p>
              )}
              <Input
                label="Ordem"
                value={form.ordem}
                onChange={(e) => setForm((p) => ({ ...p, ordem: e.target.value }))}
              />
              <Select
                label="Tipo"
                value={form.tipo}
                onChange={(v) => setForm((p) => ({ ...p, tipo: String(v) }))}
                options={TIPO_OPTIONS}
              />
              <Switch
                bare
                checked={form.ativo}
                onCheckedChange={(ativo) => setForm((p) => ({ ...p, ativo }))}
                label="Estágio ativo"
                description="Inativos deixam de aparecer no funil e no Kanban."
                showStatusPill
                statusOnText="Ativo"
                statusOffText="Inativo"
              />
              <div className="flex flex-wrap justify-end gap-2 pt-2">
                <Button type="button" variant="cancel" onClick={() => setModal(null)} disabled={saving}>
                  Cancelar
                </Button>
                <Button type="submit" disabled={saving}>
                  {saving ? 'Salvando…' : 'Salvar'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </ConfigListPageShell>
  )
}
