import { useCallback, useEffect, useState } from 'react'
import { ApiError, atendentes, ponto, type Atendentes, type Ponto } from '../api/client'
import { coletarTodasPaginas } from '../api/collectPages'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Input } from '../components/ui/Input'
import { PageContainer, PageHeader } from '../components/ui/PageContainer'
import { Select } from '../components/ui/Select'
import { useToast } from '../components/ui/Toast'
import { useAuth } from '../contexts/AuthContext'
import { SemPermissao } from './SemPermissao'

function formatarHora(iso: string | null | undefined): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}

function inicioMesIso(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-01`
}

function hojeIso(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function rotuloStatus(s: Ponto.HojeItem['status']): string {
  switch (s) {
    case 'falta':
      return 'Falta'
    case 'parcial':
      return 'Parcial'
    case 'folga':
      return 'Folga'
    case 'folga_com_ponto':
      return 'Folga c/ ponto'
    case 'ok':
      return 'Ok'
    default:
      return 'Livre'
  }
}

export function PontoEquipe() {
  const toast = useToast()
  const { user } = useAuth()
  const [items, setItems] = useState<Ponto.BatidaAdmin[]>([])
  const [total, setTotal] = useState(0)
  const [hoje, setHoje] = useState<Ponto.HojeLista | null>(null)
  const [equipe, setEquipe] = useState<Atendentes.Atendente[]>([])
  const [atendenteId, setAtendenteId] = useState('')
  const [desde, setDesde] = useState(inicioMesIso)
  const [ate, setAte] = useState(hojeIso)
  const [loading, setLoading] = useState(true)
  const [semPermissao, setSemPermissao] = useState(false)

  const carregar = useCallback(
    async (silencioso = false) => {
      try {
        const [hist, dia] = await Promise.all([
          ponto.batidasAdmin({
            atendente_id: atendenteId ? Number(atendenteId) : undefined,
            desde,
            ate,
            limit: 100,
          }),
          ponto.hoje(),
        ])
        setItems(hist.items)
        setTotal(hist.total)
        setHoje(dia)
        setSemPermissao(false)
      } catch (err) {
        if (err instanceof ApiError && err.status === 403) {
          setSemPermissao(true)
          return
        }
        if (!silencioso) {
          toast.showError(mensagemFalhaParaToast(err, 'Não foi possível carregar o ponto da equipe.'))
        }
      } finally {
        setLoading(false)
      }
    },
    [ate, atendenteId, desde, toast],
  )

  useEffect(() => {
    void coletarTodasPaginas<Atendentes.Atendente>((o, l) =>
      atendentes.list({ incluir_inativos: false, offset: o, limit: l }),
    ).then(setEquipe)
  }, [])

  useEffect(() => {
    void carregar()
  }, [carregar])

  if (user?.role !== 'admin' || semPermissao) {
    return (
      <SemPermissao
        title="Acesso restrito a administradores."
        voltarPara="/ponto"
        voltarLabel="Ir para Meu ponto"
      />
    )
  }

  return (
    <PageContainer>
      <PageHeader
        title="Ponto da equipe"
        description="Batidas por período e visão do dia (esperado × realizado quando há escala)."
      />

      <div className="space-y-4">
        <Card title="Hoje">
          {loading && !hoje ? (
            <div className="h-24 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800/50" />
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="border-b border-slate-200 text-slate-500 dark:border-slate-700">
                  <tr>
                    <th className="py-2 pr-3 font-medium">Nome</th>
                    <th className="py-2 pr-3 font-medium">Esperado</th>
                    <th className="py-2 pr-3 font-medium">Status</th>
                    <th className="py-2 font-medium">Entrada</th>
                  </tr>
                </thead>
                <tbody>
                  {(hoje?.itens ?? []).map((item) => (
                    <tr key={item.atendente_id} className="border-b border-slate-100 dark:border-slate-800/80">
                      <td className="py-2 pr-3">{item.nome}</td>
                      <td className="py-2 pr-3">{item.esperado ? 'Trabalho' : '—'}</td>
                      <td className="py-2 pr-3">{rotuloStatus(item.status)}</td>
                      <td className="py-2">{formatarHora(item.entrada_em)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        <Card title="Histórico">
          <div className="mb-4 flex flex-wrap items-end gap-3">
            <Select
              label="Atendente"
              value={atendenteId}
              onChange={setAtendenteId}
              options={[
                { value: '', label: 'Todos' },
                ...equipe.map((a) => ({ value: String(a.id), label: a.nome })),
              ]}
            />
            <Input label="De" type="date" value={desde} onChange={(e) => setDesde(e.target.value)} />
            <Input label="Até" type="date" value={ate} onChange={(e) => setAte(e.target.value)} />
            <Button type="button" variant="secondary" onClick={() => void carregar()}>
              Filtrar
            </Button>
          </div>
          <p className="mb-3 text-sm text-slate-600 dark:text-slate-300">
            {total} batida{total === 1 ? '' : 's'} no filtro
          </p>
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-slate-200 text-slate-500 dark:border-slate-700">
                <tr>
                  <th className="py-2 pr-3 font-medium">Atendente</th>
                  <th className="py-2 pr-3 font-medium">Tipo</th>
                  <th className="py-2 pr-3 font-medium">Horário</th>
                  <th className="py-2 font-medium">Origem</th>
                </tr>
              </thead>
              <tbody>
                {items.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="py-6 text-slate-500">
                      Nenhuma batida neste filtro.
                    </td>
                  </tr>
                ) : (
                  items.map((b) => (
                    <tr key={b.id} className="border-b border-slate-100 dark:border-slate-800/80">
                      <td className="py-2 pr-3">{b.atendente_nome}</td>
                      <td className="py-2 pr-3 capitalize">{b.tipo}</td>
                      <td className="py-2 pr-3">{formatarHora(b.registrado_em)}</td>
                      <td className="py-2">{b.origem ?? '—'}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </PageContainer>
  )
}
