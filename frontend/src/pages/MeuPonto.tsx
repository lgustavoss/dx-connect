import { useCallback, useEffect, useMemo, useState } from 'react'
import { ponto, type Ponto } from '../api/client'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Input } from '../components/ui/Input'
import { PageContainer, PageHeader } from '../components/ui/PageContainer'
import { useToast } from '../components/ui/Toast'

function formatarHora(iso: string | null | undefined): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}

function formatarDuracao(segundos: number | null | undefined): string {
  if (segundos == null || segundos < 0) return '—'
  const h = Math.floor(segundos / 3600)
  const m = Math.floor((segundos % 3600) / 60)
  if (h <= 0) return `${m} min`
  return `${h} h ${String(m).padStart(2, '0')} min`
}

function inicioMesIso(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-01`
}

function hojeIso(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

export function MeuPonto() {
  const toast = useToast()
  const [estado, setEstado] = useState<Ponto.EstadoMe | null>(null)
  const [historico, setHistorico] = useState<Ponto.Historico | null>(null)
  const [desde, setDesde] = useState(inicioMesIso)
  const [ate, setAte] = useState(hojeIso)
  const [loading, setLoading] = useState(true)
  const [batendo, setBatendo] = useState(false)

  const carregar = useCallback(
    async (silencioso = false) => {
      try {
        const [me, hist] = await Promise.all([
          ponto.me(),
          ponto.minhasBatidas({ desde, ate, limit: 100 }),
        ])
        setEstado(me)
        setHistorico(hist)
      } catch (err) {
        if (!silencioso) {
          toast.showError(mensagemFalhaParaToast(err, 'Não foi possível carregar o ponto.'))
        }
      } finally {
        setLoading(false)
      }
    },
    [ate, desde, toast],
  )

  useEffect(() => {
    void carregar()
  }, [carregar])

  useEffect(() => {
    const onFocus = () => void carregar(true)
    window.addEventListener('focus', onFocus)
    return () => window.removeEventListener('focus', onFocus)
  }, [carregar])

  async function bater(tipo: 'entrada' | 'saida') {
    setBatendo(true)
    try {
      await ponto.bater({ tipo, origem: 'web' })
      toast.showSuccess(tipo === 'entrada' ? 'Entrada registrada.' : 'Saída registrada.')
      await carregar(true)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível bater o ponto.'))
    } finally {
      setBatendo(false)
    }
  }

  const hintEscala = useMemo(() => {
    if (!estado?.usa_escala) return null
    if (estado.hoje_esperado === true) {
      return `Hoje é dia de trabalho na escala ${estado.escala_rotulo ?? ''}`.trim()
    }
    if (estado.hoje_esperado === false) {
      return `Hoje é folga na escala ${estado.escala_rotulo ?? ''}`.trim()
    }
    return estado.escala_rotulo ? `Escala ${estado.escala_rotulo}` : null
  }, [estado])

  return (
    <PageContainer>
      <PageHeader
        title="Meu ponto"
        description="Registre entrada e saída da jornada. A presença online do painel é independente."
      />

      <div className="grid gap-4 lg:grid-cols-[minmax(0,22rem)_1fr]">
        <Card title="Jornada atual">
          {loading && !estado ? (
            <div className="h-28 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800/50" />
          ) : (
            <div className="space-y-4">
              <div>
                <p className="text-sm text-slate-500 dark:text-slate-400">Estado</p>
                <p className="text-lg font-semibold text-slate-900 dark:text-slate-100">
                  {estado?.em_jornada ? 'Em jornada' : 'Fora'}
                </p>
                {estado?.em_jornada && estado.entrada_aberta_em && (
                  <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
                    Desde {formatarHora(estado.entrada_aberta_em)}
                  </p>
                )}
                {hintEscala && (
                  <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">{hintEscala}</p>
                )}
              </div>
              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  disabled={batendo || !!estado?.em_jornada}
                  onClick={() => void bater('entrada')}
                >
                  Entrada
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  disabled={batendo || !estado?.em_jornada}
                  onClick={() => void bater('saida')}
                >
                  Saída
                </Button>
              </div>
            </div>
          )}
        </Card>

        <Card title="Histórico">
          <div className="mb-4 flex flex-wrap items-end gap-3">
            <Input label="De" type="date" value={desde} onChange={(e) => setDesde(e.target.value)} />
            <Input label="Até" type="date" value={ate} onChange={(e) => setAte(e.target.value)} />
            <Button type="button" variant="secondary" onClick={() => void carregar()}>
              Filtrar
            </Button>
          </div>
          {historico && (
            <p className="mb-3 text-sm text-slate-600 dark:text-slate-300">
              Total no período (intervalos fechados):{' '}
              <strong>{formatarDuracao(historico.total_segundos_fechados)}</strong>
            </p>
          )}
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-slate-200 text-slate-500 dark:border-slate-700 dark:text-slate-400">
                <tr>
                  <th className="py-2 pr-3 font-medium">Entrada</th>
                  <th className="py-2 pr-3 font-medium">Saída</th>
                  <th className="py-2 font-medium">Duração</th>
                </tr>
              </thead>
              <tbody>
                {(historico?.intervalos ?? []).length === 0 ? (
                  <tr>
                    <td colSpan={3} className="py-6 text-slate-500 dark:text-slate-400">
                      Nenhuma batida neste período.
                    </td>
                  </tr>
                ) : (
                  (historico?.intervalos ?? []).map((it, idx) => (
                    <tr
                      key={`${it.entrada_em}-${idx}`}
                      className="border-b border-slate-100 dark:border-slate-800/80"
                    >
                      <td className="py-2 pr-3">{formatarHora(it.entrada_em)}</td>
                      <td className="py-2 pr-3">
                        {it.aberto ? (
                          <span className="text-amber-700 dark:text-amber-300">Em aberto</span>
                        ) : (
                          formatarHora(it.saida_em)
                        )}
                      </td>
                      <td className="py-2">{formatarDuracao(it.duracao_segundos)}</td>
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
