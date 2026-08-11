import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError, saasPlanos, type SaasCatalogo } from '../../api/client'
import { Card } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { ListaAcoesVerEditar } from '../../components/ui/ListaAcoesVerEditar'
import { useToast } from '../../components/ui/Toast'
import { ConfigListPageShell } from '../../components/config/ConfigListPageShell'
import { SemPermissao } from '../SemPermissao'
import { mensagemFalhaParaToast } from '../../api/errorMessage'

export function SaasPlanos() {
  const navigate = useNavigate()
  const toast = useToast()
  const [list, setList] = useState<SaasCatalogo.Plano[]>([])
  const [loading, setLoading] = useState(true)
  const [forbidden, setForbidden] = useState(false)
  const [indisponivel, setIndisponivel] = useState(false)
  const [actingId, setActingId] = useState<number | null>(null)

  const carregar = useCallback(() => {
    setLoading(true)
    setForbidden(false)
    setIndisponivel(false)
    saasPlanos
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
        toast.showError(mensagemFalhaParaToast(err, 'Não foi possível carregar os planos.'))
      })
      .finally(() => setLoading(false))
  }, [toast])

  useEffect(() => {
    carregar()
  }, [carregar])

  async function toggleAtivo(item: SaasCatalogo.Plano) {
    setActingId(item.id)
    try {
      if (item.ativo) await saasPlanos.desativar(item.id)
      else await saasPlanos.ativar(item.id)
      toast.showSuccess(item.ativo ? 'Plano desactivado.' : 'Plano activado.')
      carregar()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível alterar o plano.'))
    } finally {
      setActingId(null)
    }
  }

  if (indisponivel) {
    return (
      <SemPermissao
        title="Painel de licenças não disponível nesta instância."
        voltarPara="/"
        voltarLabel="Voltar para o Dashboard"
      />
    )
  }

  if (forbidden) {
    return (
      <SemPermissao
        title="Você não tem permissão para gerir planos SaaS."
        voltarPara="/saas/licencas"
        voltarLabel="Voltar para Licenças"
      />
    )
  }

  return (
    <ConfigListPageShell
      title="Planos"
      description="Catálogo comercial — o que cada plano inclui (sem ligar features na instância)."
      actions={
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" onClick={() => navigate('/saas/modulos')}>
            Módulos
          </Button>
          <Button onClick={() => navigate('/saas/planos/novo')}>Novo plano</Button>
        </div>
      }
    >
      <Card>
        {loading ? (
          <div className="h-40 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800/50" />
        ) : list.length === 0 ? (
          <p className="px-2 py-8 text-center text-sm text-slate-500">Nenhum plano cadastrado.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-100 text-sm dark:divide-slate-800">
              <thead>
                <tr className="text-left">
                  <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500 sm:px-6">Nome</th>
                  <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500 sm:px-6">Código</th>
                  <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500 sm:px-6">Módulos</th>
                  <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500 sm:px-6">Estado</th>
                  <th className="w-px px-4 py-3 text-right text-xs font-semibold uppercase text-slate-500 sm:px-6">
                    <span className="sr-only">Ações</span>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {list.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-50 dark:hover:bg-white/5">
                    <td className="px-4 py-3.5 sm:px-6">
                      <span className="font-medium text-slate-800 dark:text-slate-100">{item.nome}</span>
                      {item.descricao ? (
                        <span className="mt-0.5 block text-xs text-slate-500">{item.descricao}</span>
                      ) : null}
                    </td>
                    <td className="px-4 py-3.5 font-mono text-xs sm:px-6">{item.codigo}</td>
                    <td className="px-4 py-3.5 text-slate-600 sm:px-6 dark:text-slate-300">
                      {item.modulos.length
                        ? item.modulos.map((m) => m.nome).join(', ')
                        : '—'}
                    </td>
                    <td className="px-4 py-3.5 sm:px-6">
                      <span
                        className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${
                          item.ativo
                            ? 'bg-emerald-50 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300'
                            : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400'
                        }`}
                      >
                        {item.ativo ? 'Activo' : 'Inactivo'}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 text-right sm:px-6">
                      <div className="flex items-center justify-end gap-2">
                        <Button
                          variant="secondary"
                          disabled={actingId === item.id}
                          onClick={() => void toggleAtivo(item)}
                        >
                          {item.ativo ? 'Desactivar' : 'Activar'}
                        </Button>
                        <ListaAcoesVerEditar
                          onVer={() => navigate(`/saas/planos/${item.id}`)}
                          onEditar={() => navigate(`/saas/planos/${item.id}`)}
                          verLabel="Ver plano"
                          editarLabel="Editar plano"
                        />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </ConfigListPageShell>
  )
}
