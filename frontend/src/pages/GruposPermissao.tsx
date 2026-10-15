import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError, permissaoGrupos, type PermissaoGrupos } from '../api/client'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { ConfigListPageShell } from '../components/config/ConfigListPageShell'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { ConfirmDialog } from '../components/ui/ConfirmDialog'
import { IconPencil } from '../components/ui/IconPencil'
import { IconTrash } from '../components/ui/IconTrash'
import { useToast } from '../components/ui/Toast'
import { useAuth } from '../contexts/AuthContext'
import { temPermissao } from '../lib/permissoes'
import { SemPermissao } from './SemPermissao'

const BASE = '/configuracoes/equipe/grupos-permissao'

function rotuloPermissao(item: PermissaoGrupos.CatalogoItem): string {
  if (item.codigo === 'admin' || item.codigo === 'comercial' || item.codigo === 'operacional') return item.nome
  return `${item.modulo}: ${item.nome}`
}

function resumoPermissoes(codigos: string[], catalogo: PermissaoGrupos.CatalogoItem[]): string {
  if (codigos.includes('admin')) return 'Acesso total'
  const porCodigo = new Map(catalogo.map((item) => [item.codigo, rotuloPermissao(item)]))
  const nomes = codigos.map((codigo) => porCodigo.get(codigo) ?? codigo)
  if (nomes.length <= 3) return nomes.join(', ')
  return `${nomes.slice(0, 3).join(', ')} +${nomes.length - 3}`
}

export function GruposPermissao({ embedded = false }: { embedded?: boolean }) {
  const navigate = useNavigate()
  const toast = useToast()
  const { user } = useAuth()
  const podeCriar = temPermissao(user, 'grupos.criar')
  const podeEditar = temPermissao(user, 'grupos.editar')
  const podeExcluir = temPermissao(user, 'grupos.excluir')
  const [list, setList] = useState<PermissaoGrupos.Grupo[]>([])
  const [catalogo, setCatalogo] = useState<PermissaoGrupos.CatalogoItem[]>([])
  const [loading, setLoading] = useState(true)
  const [forbidden, setForbidden] = useState(false)
  const [excluindo, setExcluindo] = useState<PermissaoGrupos.Grupo | null>(null)
  const [saving, setSaving] = useState(false)

  const load = useCallback(() => {
    setLoading(true)
    setForbidden(false)
    Promise.all([permissaoGrupos.list(), permissaoGrupos.catalogo()])
      .then(([grupos, itens]) => {
        setList(grupos)
        setCatalogo(itens)
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 403) setForbidden(true)
        else toast.showError(mensagemFalhaParaToast(err, 'Não foi possível carregar os grupos.'))
      })
      .finally(() => setLoading(false))
  }, [toast])

  useEffect(() => {
    load()
  }, [load])

  async function confirmarExclusao() {
    if (!excluindo) return
    setSaving(true)
    try {
      await permissaoGrupos.delete(excluindo.id)
      toast.showSuccess('Grupo excluído.')
      setExcluindo(null)
      load()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível excluir o grupo.'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <ConfigListPageShell
      embedded={embedded}
      forbidden={forbidden}
      denied={<SemPermissao />}
      title="Grupos de permissão"
      subtitle="O acesso nas telas segue o grupo mais amplo de cada pessoa."
      actions={podeCriar ? <Button onClick={() => navigate(`${BASE}/novo`)}>Novo grupo</Button> : undefined}
    >
      <Card>
        {loading ? (
          <p className="text-slate-500 dark:text-slate-400">Carregando...</p>
        ) : list.length === 0 ? (
          <p className="text-slate-500 dark:text-slate-400">Nenhum grupo encontrado.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/60 dark:border-slate-800 dark:bg-slate-800/40">
                  <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500 sm:px-6">Grupo</th>
                  <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500 sm:px-6">Permissões</th>
                  <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500 sm:px-6">Pessoas</th>
                  <th className="w-px px-4 py-3 text-right text-xs font-semibold uppercase text-slate-500 sm:px-6">
                    <span className="sr-only">Ações</span>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {list.map((g) => (
                  <tr
                    key={g.id}
                    role="button"
                    tabIndex={0}
                    onClick={() => navigate(`${BASE}/${g.id}`)}
                    onKeyDown={(ev) => {
                      if (ev.key === 'Enter' || ev.key === ' ') {
                        ev.preventDefault()
                        navigate(`${BASE}/${g.id}`)
                      }
                    }}
                    className="cursor-pointer transition-colors hover:bg-slate-50/90 focus:outline-none focus-visible:bg-slate-100/80 dark:hover:bg-white/5 dark:focus-visible:bg-slate-800/60"
                  >
                    <td className="px-4 py-3.5 sm:px-6">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-medium text-slate-800 dark:text-slate-100">{g.nome}</span>
                        {g.sistema ? (
                          <span className="rounded bg-slate-200 px-1.5 py-0.5 text-xs text-slate-600 dark:bg-slate-700 dark:text-slate-300">
                            Padrão
                          </span>
                        ) : null}
                      </div>
                    </td>
                    <td className="px-4 py-3.5 text-slate-600 sm:px-6 dark:text-slate-400">
                      {resumoPermissoes(g.permissoes, catalogo)}
                    </td>
                    <td className="px-4 py-3.5 text-slate-600 sm:px-6 dark:text-slate-400">{g.membros}</td>
                    <td className="px-4 py-3.5 text-right sm:px-6" onClick={(ev) => ev.stopPropagation()}>
                      <div className="inline-flex gap-1.5">
                        {podeEditar ? (
                          <Button
                            variant="ghost"
                            aria-label="Editar grupo"
                            onClick={() => navigate(`${BASE}/${g.id}/editar`)}
                          >
                            <IconPencil ariaHidden={false} />
                          </Button>
                        ) : null}
                        {!podeExcluir || g.sistema ? null : (
                          <Button variant="ghost" aria-label="Excluir grupo" onClick={() => setExcluindo(g)}>
                            <IconTrash ariaHidden={false} />
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <ConfirmDialog
        open={excluindo != null}
        title="Excluir grupo"
        message={
          excluindo
            ? `Excluir o grupo «${excluindo.nome}»? Quem estiver nele precisa ser movido antes.`
            : undefined
        }
        confirmLabel="Excluir"
        variant="danger"
        loading={saving}
        onConfirm={() => void confirmarExclusao()}
        onCancel={() => {
          if (!saving) setExcluindo(null)
        }}
      />
    </ConfigListPageShell>
  )
}
