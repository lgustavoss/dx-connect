import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError, saasOpsUsuarios, type SaasOpsUsuarios } from '../../api/client'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { ConfigListPageShell } from '../../components/config/ConfigListPageShell'
import { BarraBuscaPaginacao, PAGE_SIZE_PADRAO } from '../../components/ui/BarraBuscaPaginacao'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { FiltroInativos } from '../../components/ui/FiltroInativos'
import { useToast } from '../../components/ui/Toast'
import { SemPermissao } from '../SemPermissao'

export function SaasUsuarios() {
  const navigate = useNavigate()
  const toast = useToast()
  const [list, setList] = useState<SaasOpsUsuarios.Usuario[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [busca, setBusca] = useState('')
  const [debouncedBusca, setDebouncedBusca] = useState('')
  const [loading, setLoading] = useState(true)
  const [incluirInativos, setIncluirInativos] = useState(false)
  const [forbidden, setForbidden] = useState(false)
  const [indisponivel, setIndisponivel] = useState(false)

  useEffect(() => {
    const t = setTimeout(() => setDebouncedBusca(busca.trim()), 400)
    return () => clearTimeout(t)
  }, [busca])

  useEffect(() => {
    setPage(1)
  }, [debouncedBusca, incluirInativos])

  const load = useCallback(() => {
    setLoading(true)
    setForbidden(false)
    setIndisponivel(false)
    saasOpsUsuarios
      .list({
        incluir_inativos: incluirInativos,
        busca: debouncedBusca || undefined,
        offset: (page - 1) * PAGE_SIZE_PADRAO,
        limit: PAGE_SIZE_PADRAO,
      })
      .then(({ items, total: t }) => {
        setList(items)
        setTotal(t)
      })
      .catch((err) => {
        setList([])
        setTotal(0)
        if (err instanceof ApiError && err.status === 403) {
          setForbidden(true)
          return
        }
        if (err instanceof ApiError && err.status === 404) {
          setIndisponivel(true)
          return
        }
        toast.showError(mensagemFalhaParaToast(err, 'Não encontramos a equipe.'))
      })
      .finally(() => setLoading(false))
  }, [debouncedBusca, incluirInativos, page, toast])

  useEffect(() => {
    load()
  }, [load])

  if (indisponivel) {
    return (
      <SemPermissao
        title="Painel SaaS não disponível nesta instância."
        detail="A equipe DeskRudder só existe no control-plane."
        voltarPara="/login/admin"
        voltarLabel="Voltar ao login admin"
      />
    )
  }

  return (
    <ConfigListPageShell
      forbidden={forbidden}
      denied={
        <SemPermissao
          title="Você não tem permissão para gerir a equipe."
          voltarPara="/login/admin"
          voltarLabel="Voltar ao login admin"
        />
      }
      title="Equipe DeskRudder"
      actions={<Button onClick={() => navigate('/saas/usuarios/novo')}>Novo usuário</Button>}
    >
      <Card
        title="Usuários"
        description="Quem entra no /login/admin (desenvolvimento e comercial). Cada pessoa gera o próprio token Cursor em Minha conta."
      >
        <BarraBuscaPaginacao
          busca={busca}
          onBuscaChange={setBusca}
          placeholder="Buscar por nome ou e-mail"
          page={page}
          total={total}
          onPageChange={setPage}
          disabled={loading}
          extra={<FiltroInativos incluirInativos={incluirInativos} onChange={setIncluirInativos} />}
        />
        {loading ? (
          <p className="text-slate-500 dark:text-slate-400">Carregando...</p>
        ) : list.length === 0 ? (
          <p className="text-slate-500 dark:text-slate-400">Nenhum usuário encontrado.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/60 dark:border-slate-800 dark:bg-slate-800/40">
                  <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500 sm:px-6 dark:text-slate-400">
                    Nome
                  </th>
                  <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500 sm:px-6 dark:text-slate-400">
                    Cargos
                  </th>
                  <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500 sm:px-6 dark:text-slate-400">
                    E-mail
                  </th>
                  <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500 sm:px-6 dark:text-slate-400">
                    Token Cursor
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {list.map((u) => (
                  <tr
                    key={u.id}
                    role="button"
                    tabIndex={0}
                    onClick={() => navigate(`/saas/usuarios/${u.id}`)}
                    onKeyDown={(ev) => {
                      if (ev.key === 'Enter' || ev.key === ' ') {
                        ev.preventDefault()
                        navigate(`/saas/usuarios/${u.id}`)
                      }
                    }}
                    className="cursor-pointer transition-colors hover:bg-slate-50 dark:hover:bg-white/5 focus:outline-none focus-visible:bg-slate-100/80 dark:focus-visible:bg-slate-800/60"
                  >
                    <td className="px-4 py-3.5 sm:px-6">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className={`font-medium ${u.ativo ? 'text-slate-800 dark:text-slate-100' : 'text-slate-400'}`}>
                          {u.nome}
                        </span>
                        {!u.ativo ? (
                          <span className="shrink-0 rounded bg-slate-200 px-1.5 py-0.5 text-xs text-slate-600 dark:text-slate-400">
                            Inativo
                          </span>
                        ) : null}
                        {u.must_change_password ? (
                          <span className="shrink-0 rounded bg-amber-100 px-1.5 py-0.5 text-xs text-amber-800 dark:bg-amber-500/20 dark:text-amber-200">
                            Trocar senha
                          </span>
                        ) : null}
                      </div>
                    </td>
                    <td className="max-w-[14rem] px-4 py-3.5 text-slate-600 sm:px-6 dark:text-slate-400">
                      {(u.setores ?? []).length > 0
                        ? (u.setores ?? []).map((s) => s.nome).join(', ')
                        : '—'}
                    </td>
                    <td className="max-w-[16rem] truncate px-4 py-3.5 text-slate-600 sm:px-6 dark:text-slate-400" title={u.email}>
                      {u.email}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3.5 text-slate-600 sm:px-6 dark:text-slate-400">
                      {u.mcp_token_configurado ? 'Configurado' : 'Ainda não'}
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
