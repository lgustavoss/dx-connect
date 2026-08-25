import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError, saasModulos, type SaasCatalogo } from '../../api/client'
import { Card } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { useToast } from '../../components/ui/Toast'
import { ConfigListPageShell } from '../../components/config/ConfigListPageShell'
import { SemPermissao } from '../SemPermissao'
import { mensagemFalhaParaToast } from '../../api/errorMessage'

function formatPreco(v: number | null | undefined): string {
  if (v == null) return '—'
  return `R$ ${Number(v).toLocaleString('pt-BR', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  })}`
}

export function SaasModulos() {
  const navigate = useNavigate()
  const toast = useToast()
  const [list, setList] = useState<SaasCatalogo.Modulo[]>([])
  const [loading, setLoading] = useState(true)
  const [forbidden, setForbidden] = useState(false)
  const [indisponivel, setIndisponivel] = useState(false)
  const [actingId, setActingId] = useState<number | null>(null)
  const [saving, setSaving] = useState(false)
  const [formOpen, setFormOpen] = useState(false)

  const [codigo, setCodigo] = useState('')
  const [nome, setNome] = useState('')
  const [descricao, setDescricao] = useState('')
  const [precoMensal, setPrecoMensal] = useState('')
  const [editId, setEditId] = useState<number | null>(null)

  const carregar = useCallback(() => {
    setLoading(true)
    saasModulos
      .list()
      .then(setList)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 403) {
          setForbidden(true)
          return
        }
        if (err instanceof ApiError && err.status === 404) {
          setIndisponivel(true)
          return
        }
        toast.showError(mensagemFalhaParaToast(err, 'Não foi possível carregar os módulos.'))
      })
      .finally(() => setLoading(false))
  }, [toast])

  useEffect(() => {
    carregar()
  }, [carregar])

  function resetForm() {
    setEditId(null)
    setCodigo('')
    setNome('')
    setDescricao('')
    setPrecoMensal('')
    setFormOpen(false)
  }

  function startCreate() {
    setEditId(null)
    setCodigo('')
    setNome('')
    setDescricao('')
    setPrecoMensal('')
    setFormOpen(true)
  }

  function startEdit(m: SaasCatalogo.Modulo) {
    setEditId(m.id)
    setCodigo(m.codigo)
    setNome(m.nome)
    setDescricao(m.descricao ?? '')
    setPrecoMensal(m.preco_mensal != null ? String(m.preco_mensal) : '')
    setFormOpen(true)
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      const precoN = precoMensal.trim() === '' ? null : Number(precoMensal)
      const preco = precoN != null && Number.isFinite(precoN) ? precoN : null
      if (editId != null) {
        await saasModulos.update(editId, {
          nome: nome.trim(),
          descricao: descricao.trim() || null,
          preco_mensal: preco,
        })
        toast.showSuccess('Módulo atualizado. Planos que o usam recalculam o preço.')
      } else {
        await saasModulos.create({
          codigo: codigo.trim().toLowerCase(),
          nome: nome.trim(),
          descricao: descricao.trim() || null,
          preco_mensal: preco,
        })
        toast.showSuccess('Módulo criado.')
      }
      resetForm()
      carregar()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível salvar o módulo.'))
    } finally {
      setSaving(false)
    }
  }

  async function toggleAtivo(item: SaasCatalogo.Modulo) {
    setActingId(item.id)
    try {
      if (item.ativo) await saasModulos.desativar(item.id)
      else await saasModulos.ativar(item.id)
      toast.showSuccess(item.ativo ? 'Módulo desativado.' : 'Módulo ativado.')
      carregar()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível alterar o módulo.'))
    } finally {
      setActingId(null)
    }
  }

  if (indisponivel) {
    return (
      <SemPermissao
        title="Painel SaaS não disponível nesta instância."
        voltarPara="/"
        voltarLabel="Voltar para o Dashboard"
      />
    )
  }

  const editando = editId != null

  return (
    <ConfigListPageShell
      forbidden={forbidden}
      denied={
        <SemPermissao
          title="Você não tem permissão para gerir módulos."
          voltarPara="/saas/planos"
          voltarLabel="Voltar para Planos"
        />
      }
      title="Módulos"
      subtitle="Preço mensal de cada módulo — o plano soma os habilitados."
      actions={
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" onClick={() => navigate('/saas/planos')}>
            Voltar aos planos
          </Button>
          {!formOpen ? (
            <Button onClick={startCreate}>Novo módulo</Button>
          ) : null}
        </div>
      }
    >
      <div className="space-y-4">
        {formOpen ? (
          <Card title={editando ? 'Editar módulo' : 'Novo módulo'}>
            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="grid gap-4 sm:grid-cols-12">
                <div className="sm:col-span-5">
                  <Input
                    label="Nome"
                    value={nome}
                    onChange={(e) => setNome(e.target.value)}
                    required
                    placeholder="Ex.: Contratos"
                    autoFocus
                  />
                </div>
                <div className="sm:col-span-4">
                  <Input
                    label="Código"
                    value={codigo}
                    onChange={(e) => setCodigo(e.target.value)}
                    required
                    disabled={editando}
                    placeholder="contratos"
                    className="font-mono text-sm"
                  />
                </div>
                <div className="sm:col-span-3">
                  <Input
                    label="Preço (R$/mês)"
                    type="number"
                    step="0.01"
                    min={0}
                    value={precoMensal}
                    onChange={(e) => setPrecoMensal(e.target.value)}
                    placeholder="0"
                  />
                </div>
                <div className="sm:col-span-12">
                  <Input
                    label="Descrição"
                    value={descricao}
                    onChange={(e) => setDescricao(e.target.value)}
                    placeholder="Opcional"
                  />
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-2 border-t border-slate-100 pt-4 dark:border-slate-800">
                <Button type="submit" disabled={saving}>
                  {editando ? 'Salvar' : 'Criar módulo'}
                </Button>
                <Button type="button" variant="cancel" disabled={saving} onClick={resetForm}>
                  Cancelar
                </Button>
              </div>
            </form>
          </Card>
        ) : null}

        <Card>
          {loading ? (
            <div className="h-40 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800/50" />
          ) : list.length === 0 ? (
            <div className="px-2 py-10 text-center">
              <p className="text-sm text-slate-500 dark:text-slate-400">Nenhum módulo cadastrado.</p>
              {!formOpen ? (
                <Button className="mt-4" onClick={startCreate}>
                  Novo módulo
                </Button>
              ) : null}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-100 text-sm dark:divide-slate-800">
                <thead>
                  <tr className="text-left">
                    <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500 sm:px-6">
                      Nome
                    </th>
                    <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500 sm:px-6">
                      Código
                    </th>
                    <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500 sm:px-6">
                      Preço
                    </th>
                    <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500 sm:px-6">
                      Situação
                    </th>
                    <th className="w-px px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-slate-500 sm:px-6">
                      <span className="sr-only">Ações</span>
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {list.map((m) => (
                    <tr
                      key={m.id}
                      className={`hover:bg-slate-50 dark:hover:bg-white/5 ${
                        editId === m.id ? 'bg-sky-50/60 dark:bg-sky-950/20' : ''
                      }`}
                    >
                      <td className="px-4 py-3.5 sm:px-6">
                        <span className="font-medium text-slate-800 dark:text-slate-100">{m.nome}</span>
                        {m.descricao ? (
                          <span className="mt-0.5 block max-w-md truncate text-xs text-slate-500">
                            {m.descricao}
                          </span>
                        ) : null}
                      </td>
                      <td className="px-4 py-3.5 font-mono text-xs text-slate-600 sm:px-6 dark:text-slate-300">
                        {m.codigo}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3.5 tabular-nums text-slate-700 sm:px-6 dark:text-slate-200">
                        {formatPreco(m.preco_mensal)}
                      </td>
                      <td className="px-4 py-3.5 sm:px-6">
                        <span
                          className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${
                            m.ativo
                              ? 'bg-emerald-50 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300'
                              : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400'
                          }`}
                        >
                          {m.ativo ? 'Ativo' : 'Inativo'}
                        </span>
                      </td>
                      <td className="px-4 py-3.5 text-right sm:px-6">
                        <div className="flex items-center justify-end gap-2">
                          <Button variant="secondary" onClick={() => startEdit(m)}>
                            Editar
                          </Button>
                          <Button
                            variant="secondary"
                            disabled={actingId === m.id}
                            onClick={() => void toggleAtivo(m)}
                          >
                            {m.ativo ? 'Desativar' : 'Ativar'}
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </ConfigListPageShell>
  )
}
