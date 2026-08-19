import { useCallback, useEffect, useState } from 'react'
import { ApiError, comercialContratoTemplates, type ComercialContrato } from '../api/client'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Input, TEXTAREA_FIELD_CLASS } from '../components/ui/Input'
import { Switch } from '../components/ui/Switch'
import { FiltroInativos } from '../components/ui/FiltroInativos'
import { IconPencil } from '../components/ui/IconPencil'
import { useToast } from '../components/ui/Toast'
import { ConfigListPageShell } from '../components/config/ConfigListPageShell'
import { SemPermissao } from './SemPermissao'

const PLACEHOLDERS = [
  '{{razao_social}}',
  '{{cnpj}}',
  '{{itens}}',
  '{{valor_mensalidade}}',
  '{{setup_bloco}}',
  '{{data_inicio}}',
  '{{data_fim_fidelidade}}',
  '{{fidelidade_meses}}',
  '{{fidelidade}}',
  '{{multa}}',
  '{{igpm}}',
  '{{clausula_deslocamento}}',
  '{{clausula_alimentacao}}',
  '{{clausula_hospedagem}}',
  '{{logo}}',
  '{{empresa_sistema}}',
] as const

type FormState = {
  nome: string
  conteudo_html: string
  ativo: boolean
}

const emptyForm = (): FormState => ({
  nome: '',
  conteudo_html: '',
  ativo: true,
})

export function ConfigContratoTemplates({ embedded = false }: { embedded?: boolean }) {
  const toast = useToast()
  const [list, setList] = useState<ComercialContrato.Template[]>([])
  const [loading, setLoading] = useState(true)
  const [forbidden, setForbidden] = useState(false)
  const [incluirInativos, setIncluirInativos] = useState(false)
  const [modal, setModal] = useState<'create' | ComercialContrato.Template | null>(null)
  const [form, setForm] = useState<FormState>(emptyForm())
  const [saving, setSaving] = useState(false)
  const [previewHtml, setPreviewHtml] = useState<string | null>(null)

  const load = useCallback(() => {
    setLoading(true)
    setForbidden(false)
    comercialContratoTemplates
      .list({ incluir_inativos: incluirInativos })
      .then(setList)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 403) {
          setForbidden(true)
          setList([])
          return
        }
        toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível carregar os modelos.'))
        setList([])
      })
      .finally(() => setLoading(false))
  }, [incluirInativos, toast])

  useEffect(() => {
    load()
  }, [load])

  function openCreate() {
    setForm(emptyForm())
    setPreviewHtml(null)
    setModal('create')
  }

  function openEdit(row: ComercialContrato.Template) {
    setForm({
      nome: row.nome,
      conteudo_html: row.conteudo_html,
      ativo: row.ativo,
    })
    setPreviewHtml(null)
    setModal(row)
  }

  async function handlePreview() {
    if (!form.conteudo_html.trim()) {
      toast.showWarning('Informe o HTML do modelo.')
      return
    }
    try {
      const r = await comercialContratoTemplates.preview(form.conteudo_html)
      setPreviewHtml(r.html)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível gerar o preview.'))
    }
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    if (!form.nome.trim() || !form.conteudo_html.trim()) {
      toast.showWarning('Informe nome e HTML do modelo.')
      return
    }
    setSaving(true)
    try {
      if (modal === 'create') {
        await comercialContratoTemplates.create({
          nome: form.nome.trim(),
          conteudo_html: form.conteudo_html,
          ativo: form.ativo,
        })
        toast.showSuccess('Modelo criado.')
      } else if (modal && typeof modal === 'object') {
        await comercialContratoTemplates.update(modal.id, {
          nome: form.nome.trim(),
          conteudo_html: form.conteudo_html,
          ativo: form.ativo,
        })
        toast.showSuccess('Modelo atualizado. A versão sobe se o HTML mudar; contratos já gerados não mudam.')
      }
      setModal(null)
      load()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível salvar o modelo.'))
    } finally {
      setSaving(false)
    }
  }

  const denied = (
    <SemPermissao
      title="Você não tem permissão para configurar modelos de contrato."
      detail="Apenas administradores gerem os templates do contrato comercial."
      voltarPara="/"
      voltarLabel="Voltar para o Dashboard"
    />
  )

  return (
    <ConfigListPageShell
      embedded={embedded}
      forbidden={forbidden}
      denied={denied}
      title="Modelos de contrato"
      actions={<Button onClick={openCreate}>Novo modelo</Button>}
    >
      <p className="mb-3 text-sm text-slate-500 dark:text-slate-400">
        HTML usado ao gerar o contrato na negociação. Não inclua custo ou margem — esses dados são internos.
        Editar o HTML sobe a versão do modelo; o PDF já gerado permanece na versão gravada no contrato.
      </p>
      <details className="mb-3 rounded-lg border border-slate-200 px-3 py-2 text-sm dark:border-slate-700">
        <summary className="cursor-pointer font-medium text-slate-700 dark:text-slate-200">
          Placeholders disponíveis
        </summary>
        <ul className="mt-2 flex flex-wrap gap-1.5">
          {PLACEHOLDERS.map((p) => (
            <li key={p}>
              <code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-800 dark:bg-slate-800 dark:text-slate-200">
                {p}
              </code>
            </li>
          ))}
        </ul>
      </details>
      <Card>
        <div className="mb-3">
          <FiltroInativos incluirInativos={incluirInativos} onChange={setIncluirInativos} />
        </div>
        {loading ? (
          <p className="text-slate-500">Carregando…</p>
        ) : list.length === 0 ? (
          <p className="text-slate-500">Nenhum modelo encontrado.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[560px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/60 dark:border-slate-800 dark:bg-slate-800/40">
                  <th className="px-3 py-2 font-medium text-slate-600 dark:text-slate-300">Nome</th>
                  <th className="px-3 py-2 font-medium text-slate-600 dark:text-slate-300">Versão</th>
                  <th className="px-3 py-2 font-medium text-slate-600 dark:text-slate-300">Ativo</th>
                  <th className="px-3 py-2" />
                </tr>
              </thead>
              <tbody>
                {list.map((row) => (
                  <tr key={row.id} className="border-b border-slate-100 dark:border-slate-800/80">
                    <td className="px-3 py-2.5 font-medium text-slate-900 dark:text-slate-100">{row.nome}</td>
                    <td className="px-3 py-2.5 text-slate-600">v{row.versao}</td>
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
          <div className="max-h-[92vh] w-full overflow-y-auto rounded-t-2xl bg-white p-5 shadow-xl dark:bg-slate-900 sm:max-w-2xl sm:rounded-2xl">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              {modal === 'create' ? 'Novo modelo' : 'Editar modelo'}
            </h2>
            <form onSubmit={handleSave} className="mt-4 space-y-3">
              <Input
                label="Nome"
                value={form.nome}
                onChange={(e) => setForm((p) => ({ ...p, nome: e.target.value }))}
                required
              />
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                HTML
                <textarea
                  value={form.conteudo_html}
                  onChange={(e) => setForm((p) => ({ ...p, conteudo_html: e.target.value }))}
                  rows={12}
                  required
                  className={`mt-1 font-mono text-xs ${TEXTAREA_FIELD_CLASS}`}
                />
              </label>
              <Switch
                bare
                checked={form.ativo}
                onCheckedChange={(ativo) => setForm((p) => ({ ...p, ativo }))}
                label="Modelo ativo"
                description="Inativos não aparecem na geração do contrato."
                showStatusPill
                statusOnText="Ativo"
                statusOffText="Inativo"
              />
              {previewHtml ? (
                <div>
                  <p className="mb-1 text-xs text-slate-500">
                    Sanitiza o HTML. Placeholders só são preenchidos ao gerar o contrato na negociação.
                  </p>
                  <iframe
                    title="Preview do modelo"
                    sandbox=""
                    srcDoc={previewHtml}
                    className="h-64 w-full rounded-lg border border-slate-200 bg-white dark:border-slate-700"
                  />
                </div>
              ) : null}
              <div className="flex flex-wrap justify-end gap-2 pt-2">
                <Button type="button" variant="secondary" onClick={() => setModal(null)} disabled={saving}>
                  Cancelar
                </Button>
                <Button type="button" variant="secondary" onClick={() => void handlePreview()} disabled={saving}>
                  Preview
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
