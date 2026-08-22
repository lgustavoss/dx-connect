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

export function SaasModulos() {
  const navigate = useNavigate()
  const toast = useToast()
  const [list, setList] = useState<SaasCatalogo.Modulo[]>([])
  const [loading, setLoading] = useState(true)
  const [forbidden, setForbidden] = useState(false)
  const [indisponivel, setIndisponivel] = useState(false)
  const [actingId, setActingId] = useState<number | null>(null)
  const [saving, setSaving] = useState(false)

  const [codigo, setCodigo] = useState('')
  const [nome, setNome] = useState('')
  const [descricao, setDescricao] = useState('')
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
  }

  function startEdit(m: SaasCatalogo.Modulo) {
    setEditId(m.id)
    setCodigo(m.codigo)
    setNome(m.nome)
    setDescricao(m.descricao ?? '')
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      if (editId != null) {
        await saasModulos.update(editId, {
          nome: nome.trim(),
          descricao: descricao.trim() || null,
        })
        toast.showSuccess('Módulo actualizado.')
      } else {
        await saasModulos.create({
          codigo: codigo.trim().toLowerCase(),
          nome: nome.trim(),
          descricao: descricao.trim() || null,
        })
        toast.showSuccess('Módulo criado.')
      }
      resetForm()
      carregar()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível guardar o módulo.'))
    } finally {
      setSaving(false)
    }
  }

  async function toggleAtivo(item: SaasCatalogo.Modulo) {
    setActingId(item.id)
    try {
      if (item.ativo) await saasModulos.desativar(item.id)
      else await saasModulos.ativar(item.id)
      toast.showSuccess(item.ativo ? 'Módulo desactivado.' : 'Módulo activado.')
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
      subtitle="Peças do catálogo comercial que podem ser associadas a planos."
      actions={
        <Button variant="secondary" onClick={() => navigate('/saas/planos')}>
          Voltar aos planos
        </Button>
      }
    >
      <div className="space-y-6">
        <Card title={editId != null ? 'Editar módulo' : 'Novo módulo'}>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <Input
                label="Código"
                value={codigo}
                onChange={(e) => setCodigo(e.target.value)}
                required
                disabled={editId != null}
                hint="Ex.: contratos"
              />
              <Input label="Nome" value={nome} onChange={(e) => setNome(e.target.value)} required />
            </div>
            <Input
              label="Descrição"
              value={descricao}
              onChange={(e) => setDescricao(e.target.value)}
            />
            <div className="flex flex-wrap gap-2">
              <Button type="submit" disabled={saving}>
                {editId != null ? 'Guardar' : 'Criar'}
              </Button>
              {editId != null ? (
                <Button type="button" variant="cancel" disabled={saving} onClick={resetForm}>
                  Cancelar edição
                </Button>
              ) : null}
            </div>
          </form>
        </Card>

        <Card>
          {loading ? (
            <div className="h-32 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800/50" />
          ) : list.length === 0 ? (
            <p className="py-6 text-center text-sm text-slate-500">Nenhum módulo.</p>
          ) : (
            <ul className="divide-y divide-slate-100 dark:divide-slate-800">
              {list.map((m) => (
                <li
                  key={m.id}
                  className="flex flex-wrap items-center justify-between gap-3 px-1 py-3 sm:px-2"
                >
                  <div>
                    <p className="font-medium text-slate-800 dark:text-slate-100">
                      {m.nome}{' '}
                      <span className="font-mono text-xs font-normal text-slate-500">{m.codigo}</span>
                    </p>
                    {m.descricao ? (
                      <p className="text-xs text-slate-500">{m.descricao}</p>
                    ) : null}
                  </div>
                  <div className="flex items-center gap-2">
                    <span
                      className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${
                        m.ativo
                          ? 'bg-emerald-50 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300'
                          : 'bg-slate-100 text-slate-600'
                      }`}
                    >
                      {m.ativo ? 'Activo' : 'Inactivo'}
                    </span>
                    <Button variant="secondary" onClick={() => startEdit(m)}>
                      Editar
                    </Button>
                    <Button
                      variant="secondary"
                      disabled={actingId === m.id}
                      onClick={() => void toggleAtivo(m)}
                    >
                      {m.ativo ? 'Desactivar' : 'Activar'}
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </ConfigListPageShell>
  )
}
