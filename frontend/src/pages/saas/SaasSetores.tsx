import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError, saasSetores, type SaasSetores } from '../../api/client'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { ConfigListPageShell } from '../../components/config/ConfigListPageShell'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { FiltroInativos } from '../../components/ui/FiltroInativos'
import { useToast } from '../../components/ui/Toast'
import { SemPermissao } from '../SemPermissao'

export function SaasSetoresPage() {
  const navigate = useNavigate()
  const toast = useToast()
  const [list, setList] = useState<SaasSetores.Setor[]>([])
  const [loading, setLoading] = useState(true)
  const [incluirInativos, setIncluirInativos] = useState(false)
  const [forbidden, setForbidden] = useState(false)
  const [indisponivel, setIndisponivel] = useState(false)

  const load = useCallback(() => {
    setLoading(true)
    setForbidden(false)
    setIndisponivel(false)
    saasSetores
      .list({ incluir_inativos: incluirInativos })
      .then(setList)
      .catch((err) => {
        setList([])
        if (err instanceof ApiError && err.status === 403) {
          setForbidden(true)
          return
        }
        if (err instanceof ApiError && err.status === 404) {
          setIndisponivel(true)
          return
        }
        toast.showError(mensagemFalhaParaToast(err, 'Não encontramos os setores.'))
      })
      .finally(() => setLoading(false))
  }, [incluirInativos, toast])

  useEffect(() => {
    load()
  }, [load])

  if (indisponivel) {
    return (
      <SemPermissao
        title="Painel SaaS não disponível nesta instância."
        detail="Os cargos da equipe DeskRudder só existem no control-plane."
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
          title="Você não tem permissão para gerir os setores."
          voltarPara="/login/admin"
          voltarLabel="Voltar ao login admin"
        />
      }
      title="Setores"
      actions={<Button onClick={() => navigate('/saas/setores/novo')}>Novo setor</Button>}
    >
      <Card
        title="Cargos da equipe"
        description="Admin, Desenvolvimento, Comercial, etc. Um usuário pode ter vários cargos. Não altera permissões no painel (todos continuam ops)."
      >
        <div className="mb-4">
          <FiltroInativos incluirInativos={incluirInativos} onChange={setIncluirInativos} />
        </div>
        {loading ? (
          <p className="text-slate-500 dark:text-slate-400">Carregando...</p>
        ) : list.length === 0 ? (
          <p className="text-slate-500 dark:text-slate-400">Nenhum setor cadastrado.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[320px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/60 dark:border-slate-800 dark:bg-slate-800/40">
                  <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500 sm:px-6 dark:text-slate-400">
                    Nome
                  </th>
                  <th className="px-4 py-3 text-xs font-semibold uppercase text-slate-500 sm:px-6 dark:text-slate-400">
                    Situação
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {list.map((s) => (
                  <tr
                    key={s.id}
                    role="button"
                    tabIndex={0}
                    onClick={() => navigate(`/saas/setores/${s.id}`)}
                    onKeyDown={(ev) => {
                      if (ev.key === 'Enter' || ev.key === ' ') {
                        ev.preventDefault()
                        navigate(`/saas/setores/${s.id}`)
                      }
                    }}
                    className="cursor-pointer transition-colors hover:bg-slate-50 dark:hover:bg-white/5 focus:outline-none focus-visible:bg-slate-100/80 dark:focus-visible:bg-slate-800/60"
                  >
                    <td className="px-4 py-3.5 font-medium text-slate-800 sm:px-6 dark:text-slate-100">{s.nome}</td>
                    <td className="px-4 py-3.5 text-slate-600 sm:px-6 dark:text-slate-400">
                      {s.ativo ? 'Ativo' : 'Inativo'}
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
