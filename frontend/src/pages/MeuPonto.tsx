import { useCallback, useEffect, useMemo, useState } from 'react'
import { ponto, type Ponto } from '../api/client'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { PontoCalendarioMes } from '../components/PontoCalendarioMes'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Input } from '../components/ui/Input'
import { PageContainer, PageHeader } from '../components/ui/PageContainer'
import { Select } from '../components/ui/Select'
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
  const [justifs, setJustifs] = useState<Ponto.Justificativa[]>([])
  const [justData, setJustData] = useState(hojeIso)
  const [justTipo, setJustTipo] = useState<Ponto.JustificativaCreate['tipo']>('esquecimento')
  const [justMotivo, setJustMotivo] = useState('')
  const [enviandoJust, setEnviandoJust] = useState(false)
  const [banco, setBanco] = useState<Ponto.BancoHoras | null>(null)
  const agora = new Date()
  const [calAno, setCalAno] = useState(agora.getFullYear())
  const [calMes, setCalMes] = useState(agora.getMonth() + 1)
  const [calendario, setCalendario] = useState<Ponto.Calendario | null>(null)
  const [diaCal, setDiaCal] = useState<string | null>(hojeIso())
  const [loadingCal, setLoadingCal] = useState(false)

  const carregar = useCallback(
    async (silencioso = false) => {
      try {
        const [me, hist, js, bh] = await Promise.all([
          ponto.me(),
          ponto.minhasBatidas({ desde, ate, limit: 100 }),
          ponto.minhasJustificativas(),
          ponto.meuBancoHoras(desde, ate),
        ])
        setEstado(me)
        setHistorico(hist)
        setJustifs(js)
        setBanco(bh)
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

  const carregarCalendario = useCallback(
    async (silencioso = false) => {
      setLoadingCal(true)
      try {
        const cal = await ponto.meuCalendario(calAno, calMes)
        setCalendario(cal)
      } catch (err) {
        if (!silencioso) {
          toast.showError(mensagemFalhaParaToast(err, 'Não foi possível carregar o calendário.'))
        }
      } finally {
        setLoadingCal(false)
      }
    },
    [calAno, calMes, toast],
  )

  useEffect(() => {
    void carregarCalendario()
  }, [carregarCalendario])

  useEffect(() => {
    const onFocus = () => void carregar(true)
    window.addEventListener('focus', onFocus)
    return () => window.removeEventListener('focus', onFocus)
  }, [carregar])

  async function bater(tipo: Ponto.Tipo) {
    setBatendo(true)
    const fechouPausaAuto = tipo === 'saida' && !!estado?.em_pausa
    try {
      await ponto.bater({ tipo, origem: 'web' })
      if (fechouPausaAuto) {
        toast.showSuccess('Pausa encerrada automaticamente ao sair.')
      } else {
        const msgs: Record<Ponto.Tipo, string> = {
          entrada: 'Entrada registrada.',
          saida: 'Saída registrada.',
          pausa_inicio: 'Pausa iniciada.',
          pausa_fim: 'Pausa encerrada.',
        }
        toast.showSuccess(msgs[tipo])
      }
      await Promise.all([carregar(true), carregarCalendario(true)])
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível bater o ponto.'))
    } finally {
      setBatendo(false)
    }
  }

  async function enviarJustificativa() {
    if (!justMotivo.trim()) {
      toast.showWarning('Informe o motivo da justificativa.')
      return
    }
    setEnviandoJust(true)
    try {
      await ponto.criarJustificativa({
        data_ref: justData,
        tipo: justTipo,
        motivo: justMotivo.trim(),
      })
      toast.showSuccess('Justificativa enviada para aprovação.')
      setJustMotivo('')
      await carregar(true)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível enviar a justificativa.'))
    } finally {
      setEnviandoJust(false)
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

  const emJornada = !!estado?.em_jornada
  const emPausa = !!estado?.em_pausa

  return (
    <PageContainer>
      <PageHeader
        title="Meu ponto"
        subtitle="Registre entrada, pausas e saída. A presença online do painel é independente."
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
                  {!emJornada ? 'Fora' : emPausa ? 'Em pausa' : 'Em jornada'}
                </p>
                {emJornada && estado?.entrada_aberta_em && (
                  <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
                    Desde {formatarHora(estado.entrada_aberta_em)}
                  </p>
                )}
                {hintEscala && (
                  <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">{hintEscala}</p>
                )}
              </div>
              <div className="flex flex-wrap gap-2">
                <Button type="button" disabled={batendo || emJornada} onClick={() => void bater('entrada')}>
                  Entrada
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  disabled={batendo || !emJornada || emPausa}
                  onClick={() => void bater('pausa_inicio')}
                >
                  Pausar
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  disabled={batendo || !emPausa}
                  onClick={() => void bater('pausa_fim')}
                >
                  Retomar
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  disabled={batendo || !emJornada}
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
              Trabalhado (sem pausas): <strong>{formatarDuracao(historico.total_segundos_fechados)}</strong>
              {historico.total_segundos_pausa != null && historico.total_segundos_pausa > 0 && (
                <>
                  {' '}
                  · Pausas: <strong>{formatarDuracao(historico.total_segundos_pausa)}</strong>
                </>
              )}
              {banco && (
                <>
                  {' '}
                  · Banco:{' '}
                  <strong className={banco.saldo_segundos < 0 ? 'text-amber-700 dark:text-amber-300' : undefined}>
                    {banco.saldo_segundos >= 0 ? '+' : '−'}
                    {formatarDuracao(Math.abs(banco.saldo_segundos))}
                  </strong>
                  <span className="text-slate-500">
                    {' '}
                    (esperado {formatarDuracao(banco.segundos_esperados)} · realizado{' '}
                    {formatarDuracao(banco.segundos_realizados)})
                  </span>
                </>
              )}
            </p>
          )}
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-slate-200 text-slate-500 dark:border-slate-700 dark:text-slate-400">
                <tr>
                  <th className="py-2 pr-3 font-medium">Entrada</th>
                  <th className="py-2 pr-3 font-medium">Saída</th>
                  <th className="py-2 pr-3 font-medium">Pausas</th>
                  <th className="py-2 font-medium">Trabalhado</th>
                </tr>
              </thead>
              <tbody>
                {(historico?.intervalos ?? []).length === 0 ? (
                  <tr>
                    <td colSpan={4} className="py-6 text-slate-500 dark:text-slate-400">
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
                      <td className="py-2 pr-3">{formatarDuracao(it.segundos_pausa ?? 0)}</td>
                      <td className="py-2">{formatarDuracao(it.duracao_segundos)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      <div className="mt-4">
        <Card title="Calendário do mês">
          <PontoCalendarioMes
            calendario={calendario}
            loading={loadingCal}
            diaSelecionado={diaCal}
            onSelecionarDia={(iso) => {
              setDiaCal(iso)
              setDesde(iso)
              setAte(iso)
            }}
            onMesAnterior={() => {
              if (calMes <= 1) {
                setCalMes(12)
                setCalAno((y) => y - 1)
              } else setCalMes((m) => m - 1)
            }}
            onMesSeguinte={() => {
              if (calMes >= 12) {
                setCalMes(1)
                setCalAno((y) => y + 1)
              } else setCalMes((m) => m + 1)
            }}
          />
          <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
            Clique num dia para filtrar o histórico acima com as batidas dessa data.
          </p>
        </Card>
      </div>

      <div className="mt-4">
        <Card title="Justificativas">
          <div className="mb-4 flex flex-wrap items-end gap-3">
            <Input label="Data" type="date" value={justData} onChange={(e) => setJustData(e.target.value)} />
            <Select
              label="Tipo"
              value={justTipo}
              onChange={(v) => setJustTipo(String(v) as Ponto.JustificativaCreate['tipo'])}
              options={[
                { value: 'esquecimento', label: 'Esquecimento de batida' },
                { value: 'falta', label: 'Falta' },
                { value: 'folga_com_ponto', label: 'Ponto em dia de folga' },
                { value: 'outro', label: 'Outro' },
              ]}
            />
            <Input
              label="Motivo"
              value={justMotivo}
              onChange={(e) => setJustMotivo(e.target.value)}
              placeholder="Descreva o ocorrido"
            />
            <Button type="button" disabled={enviandoJust} onClick={() => void enviarJustificativa()}>
              Enviar
            </Button>
          </div>
          <ul className="space-y-2 text-sm">
            {justifs.length === 0 ? (
              <li className="text-slate-500">Nenhuma justificativa enviada.</li>
            ) : (
              justifs.map((j) => (
                <li
                  key={j.id}
                  className="rounded-lg border border-slate-200 px-3 py-2 dark:border-slate-800"
                >
                  <span className="font-medium">{j.data_ref}</span> · {j.tipo} ·{' '}
                  <span className="capitalize">{j.estado}</span>
                  <p className="text-slate-600 dark:text-slate-300">{j.motivo}</p>
                  {j.decisao_motivo && (
                    <p className="text-xs text-slate-500">Decisão: {j.decisao_motivo}</p>
                  )}
                </li>
              ))
            )}
          </ul>
        </Card>
      </div>
    </PageContainer>
  )
}
