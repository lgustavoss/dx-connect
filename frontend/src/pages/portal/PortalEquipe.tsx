import { useEffect, useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { portalCliente, type PortalCliente } from '../../api/client'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { usePortalAuth } from '../../contexts/PortalAuthContext'
import { useToast } from '../../components/ui/Toast'
import { Switch } from '../../components/ui/Switch'
import {
  PortalPageHeader,
  portalCardClass,
  portalInputClass,
  portalPrimaryBtnClass,
} from './portalUi'

const tipoLabel: Record<string, string> = {
  socio: 'Sócio',
  supervisor: 'Supervisor',
  colaborador: 'Colaborador',
}

export function PortalEquipe() {
  const { user } = usePortalAuth()
  const [incluirInativos, setIncluirInativos] = useState(false)
  const [busca, setBusca] = useState('')
  const [buscaDebounced, setBuscaDebounced] = useState('')
  const [items, setItems] = useState<PortalCliente.EquipeFuncionario[]>([])
  const [loading, setLoading] = useState(true)
  const toast = useToast()

  useEffect(() => {
    const t = window.setTimeout(() => setBuscaDebounced(busca.trim()), 300)
    return () => window.clearTimeout(t)
  }, [busca])

  useEffect(() => {
    if (user?.tipo !== 'socio') return
    let cancelled = false
    setLoading(true)
    portalCliente
      .listEquipe({ incluir_inativos: incluirInativos, busca: buscaDebounced || undefined, limit: 50 })
      .then((res) => {
        if (!cancelled) setItems(res.items)
      })
      .catch((err) => {
        if (!cancelled) toast.showError(mensagemFalhaParaToast(err, 'Não foi possível carregar os usuários.'))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.tipo, incluirInativos, buscaDebounced])

  if (user && user.tipo !== 'socio') {
    return <Navigate to="/portal/tickets" replace />
  }

  return (
    <div className="space-y-6">
      <PortalPageHeader
        title="Usuários"
        subtitle="Cadastre colaboradores e supervisores, defina empresas e acesso ao portal."
        action={
          <Link to="/portal/equipe/novo" className={portalPrimaryBtnClass} style={{ backgroundColor: 'var(--portal-primary)' }}>
            Novo usuário
          </Link>
        }
      />

      <div className="flex flex-wrap items-center gap-4">
        <Switch
          bare
          checked={incluirInativos}
          onCheckedChange={setIncluirInativos}
          label="Mostrar inativos"
          showStatusPill
          statusOnText="Sim"
          statusOffText="Não"
        />
      </div>

      <input
        type="search"
        value={busca}
        onChange={(e) => setBusca(e.target.value)}
        placeholder="Buscar por nome ou e-mail…"
        className={portalInputClass}
      />

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 animate-pulse rounded-xl bg-slate-200/60" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 bg-white px-4 py-12 text-center text-sm text-slate-500">
          Nenhum usuário encontrado.
        </div>
      ) : (
        <ul className="space-y-2">
          {items.map((f) => (
            <li key={f.id}>
              <Link to={`/portal/equipe/${f.id}`} className={`block ${portalCardClass}`}>
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate font-medium text-slate-900">{f.nome}</p>
                    <p className="truncate text-sm text-slate-500">{f.email || 'Sem e-mail'}</p>
                    <p className="mt-1 text-xs text-slate-400">
                      {f.portal_habilitado ? 'Portal habilitado' : 'Sem acesso ao portal'}
                      {!f.ativo ? ' · Inativo' : ''}
                    </p>
                  </div>
                  <span className="shrink-0 rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-medium text-slate-700 ring-1 ring-slate-200/80">
                    {tipoLabel[f.tipo] || f.tipo}
                  </span>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
