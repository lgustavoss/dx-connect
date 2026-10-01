import { useCallback, useEffect, useMemo, useState } from 'react'
import { ponto, type Ponto } from '../api/client'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { PontoAjudaModal } from '../components/PontoAjudaModal'
import { PontoCalendarioMes } from '../components/PontoCalendarioMes'
import { calcularMetricasMes, PontoMetricasMes } from '../components/PontoMetricasMes'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { ConfirmDialog } from '../components/ui/ConfirmDialog'
import { Input } from '../components/ui/Input'
import { PageContainer, PageHeader } from '../components/ui/PageContainer'
import { Select } from '../components/ui/Select'
import { useToast } from '../components/ui/Toast'
import { useEventStream } from '../contexts/EventStreamContext'
import { isCapacitorNative } from '../lib/capacitorNative'
import { geolocationSupported } from '../lib/geolocation'
import {
  countPendingPontoBatidas,
  syncPendingPontoBatidas,
} from '../lib/pontoOfflineQueue'
import {
  formatarDuracao,
  formatarDataRef,
  formatarHora,
  formatarHoraCurta,
  quandoSolicitado,
  hojeIso,
  boundsSaldoInicialMes,
  rotuloPoliticaGeo,
} from '../lib/pontoFormat'
import { avisarPontoEstadoMudou } from '../lib/pontoEstadoEvent'
import { acaoPrincipalPonto, baterProximoPonto } from '../lib/pontoBater'

type AbaMeuPonto = 'operacao' | 'espelho'
type FiltroSol = 'todas' | 'pendente' | 'aprovada' | 'rejeitada'

function toDatetimeLocalValue(isoOrDate?: string | Date): string {
  const d = isoOrDate ? new Date(isoOrDate) : new Date()
  if (Number.isNaN(d.getTime())) return ''
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function boundsMes(ano: number, mes: number): { desde: string; ate: string } {
  const pad = (n: number) => String(n).padStart(2, '0')
  const ultimo = new Date(ano, mes, 0).getDate()
  return {
    desde: `${ano}-${pad(mes)}-01`,
    ate: `${ano}-${pad(mes)}-${pad(ultimo)}`,
  }
}

function horarioComDataRef(dataRef: string, horarioLocal: string): string {
  const hora = horarioLocal.includes('T') ? horarioLocal.split('T')[1]?.slice(0, 5) : horarioLocal.slice(0, 5)
  return `${dataRef}T${hora || '08:00'}`
}

function rotuloHorarioSolicitacao(s: Ponto.SolicitacaoAjuste): string {
  if (s.tipo === 'abono') return s.motivo
  const novo = quandoSolicitado(s.data_ref, s.horario_solicitado)
  if (s.tipo === 'correcao' && s.horario_anterior) {
    return `${formatarDataRef(s.data_ref)} · ${formatarHoraCurta(s.horario_anterior)} → ${formatarHoraCurta(s.horario_solicitado)} — ${s.motivo}`
  }
  if (s.tipo === 'inclusao') return `Novo horário: ${novo} — ${s.motivo}`
  return `Horário: ${novo} — ${s.motivo}`
}

export function MeuPonto() {
  const toast = useToast()
  const { subscribe } = useEventStream()
  const [aba, setAba] = useState<AbaMeuPonto>('operacao')
  const [estado, setEstado] = useState<Ponto.EstadoMe | null>(null)
  const [historicoHoje, setHistoricoHoje] = useState<Ponto.Historico | null>(null)
  const [historicoDiaSol, setHistoricoDiaSol] = useState<Ponto.Historico | null>(null)
  const [loading, setLoading] = useState(true)
  const [batendo, setBatendo] = useState(false)
  const [ajudaAberta, setAjudaAberta] = useState(false)
  const [ciencia, setCiencia] = useState<Ponto.CienciaMe | null>(null)
  const cienciaRef = useMemo(() => {
    const d = new Date()
    const prev = new Date(d.getFullYear(), d.getMonth() - 1, 1)
    return { ano: prev.getFullYear(), mes: prev.getMonth() + 1 }
  }, [])
  const [bancoMes, setBancoMes] = useState<Ponto.BancoHoras | null>(null)
  const [bancoMesAnterior, setBancoMesAnterior] = useState<Ponto.BancoHoras | null>(null)
  const agora = new Date()
  const [calAno, setCalAno] = useState(agora.getFullYear())
  const [calMes, setCalMes] = useState(agora.getMonth() + 1)
  const [calendario, setCalendario] = useState<Ponto.Calendario | null>(null)
  const [diaCal, setDiaCal] = useState<string | null>(hojeIso())
  const [loadingCal, setLoadingCal] = useState(false)
  const [relogio, setRelogio] = useState(() => new Date())
  const [incluirLocalizacao, setIncluirLocalizacao] = useState(
    () => isCapacitorNative() || geolocationSupported(),
  )
  const [geoSettings, setGeoSettings] = useState<Ponto.SettingsPublic | null>(null)
  const [pendentesOffline, setPendentesOffline] = useState(countPendingPontoBatidas())

  const [solTipo, setSolTipo] = useState<'inclusao' | 'correcao' | 'abono'>('inclusao')
  const [solTipoBatida, setSolTipoBatida] = useState<'entrada' | 'saida'>('entrada')
  const [solHorario, setSolHorario] = useState('')
  const [solMotivo, setSolMotivo] = useState('')
  const [solAnexo, setSolAnexo] = useState<File | null>(null)
  const [solBatidaId, setSolBatidaId] = useState('')
  const [solDataRef, setSolDataRef] = useState(hojeIso)
  const [enviandoSol, setEnviandoSol] = useState(false)
  const [mostrarSolForm, setMostrarSolForm] = useState(false)
  const [solicitacoes, setSolicitacoes] = useState<Ponto.SolicitacaoAjuste[]>([])
  const [filtroSol, setFiltroSol] = useState<FiltroSol>('todas')

  const politicaGeo = geoSettings?.politica_geolocalizacao ?? 'opcional'
  const geoObrigatoria = politicaGeo === 'obrigatoria' && !!geoSettings?.tem_locais_ativos
  const geoRecomendada = politicaGeo === 'recomendada' && !!geoSettings?.tem_locais_ativos
  const deveIncluirGeo = geoObrigatoria || (geoRecomendada ? true : incluirLocalizacao)

  const carregar = useCallback(
    async (silencioso = false) => {
      const hoje = hojeIso()
      try {
        const [me, hist, gs, cin, sols] = await Promise.all([
          ponto.me(),
          ponto.minhasBatidas({ desde: hoje, ate: hoje, limit: 100 }),
          ponto.meSettings(),
          ponto.minhaCiencia(cienciaRef.ano, cienciaRef.mes),
          ponto.minhasSolicitacoesAjuste(),
        ])
        setEstado(me)
        avisarPontoEstadoMudou(me)
        setHistoricoHoje(hist)
        setGeoSettings(gs)
        setCiencia(cin)
        setSolicitacoes(sols)
        if (gs.politica_geolocalizacao === 'obrigatoria' && gs.tem_locais_ativos) {
          setIncluirLocalizacao(true)
        }
      } catch (err) {
        if (!silencioso) {
          toast.showError(mensagemFalhaParaToast(err, 'Não foi possível carregar o ponto.'))
        }
      } finally {
        setLoading(false)
      }
    },
    [cienciaRef.ano, cienciaRef.mes, toast],
  )

  const carregarCalendario = useCallback(
    async (silencioso = false) => {
      setLoadingCal(true)
      try {
        const mes = boundsMes(calAno, calMes)
        const saldoIni = boundsSaldoInicialMes(calAno, calMes)
        const [cal, bhMes, bhAnt] = await Promise.all([
          ponto.meuCalendario(calAno, calMes),
          ponto.meuBancoHoras(mes.desde, mes.ate),
          ponto.meuBancoHoras(saldoIni.desde, saldoIni.ate),
        ])
        setCalendario(cal)
        setBancoMes(bhMes)
        setBancoMesAnterior(bhAnt)
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
    void carregar()
  }, [carregar])

  useEffect(() => {
    const unsub = subscribe('ponto.solicitacao_ajuste', () => {
      void carregar(true)
    })
    return unsub
  }, [subscribe, carregar])

  useEffect(() => {
    void carregarCalendario()
  }, [carregarCalendario])

  useEffect(() => {
    const onFocus = () => {
      void carregar(true)
      void carregarCalendario(true)
    }
    window.addEventListener('focus', onFocus)
    return () => window.removeEventListener('focus', onFocus)
  }, [carregar, carregarCalendario])

  useEffect(() => {
    const t = window.setInterval(() => setRelogio(new Date()), 1000)
    return () => window.clearInterval(t)
  }, [])

  useEffect(() => {
    const origem = isCapacitorNative() ? 'mobile' : 'web'
    const sync = async () => {
      const n = await syncPendingPontoBatidas((data) => ponto.bater(data), origem)
      setPendentesOffline(countPendingPontoBatidas())
      if (n > 0) {
        toast.showSuccess(`${n} batida(s) offline sincronizada(s).`)
        await Promise.all([carregar(true), carregarCalendario(true)])
      } else if (countPendingPontoBatidas() > 0) {
        await carregar(true)
      }
    }
    void sync()
    const onOnline = () => void sync()
    window.addEventListener('online', onOnline)
    return () => window.removeEventListener('online', onOnline)
  }, [carregar, carregarCalendario, toast])

  async function bater() {
    setBatendo(true)
    try {
      const r = await baterProximoPonto({
        estado,
        incluirLocalizacao,
        settings: geoSettings,
        toast,
      })
      if (r.ok) {
        if (r.estadoOptimista) setEstado(r.estadoOptimista)
        setPendentesOffline(countPendingPontoBatidas())
        await Promise.all([carregar(true), carregarCalendario(true)])
      }
    } finally {
      setBatendo(false)
    }
  }

  async function abrirSolicitacao(tipo: 'inclusao' | 'correcao' | 'abono', dataIso: string) {
    setSolTipo(tipo)
    setSolDataRef(dataIso)
    setDiaCal(dataIso)
    setSolMotivo('')
    setSolAnexo(null)
    setSolBatidaId('')
    setSolHorario(tipo === 'abono' ? '' : toDatetimeLocalValue(`${dataIso}T08:00:00`))
    setSolTipoBatida('entrada')
    setMostrarSolForm(true)
    if (tipo === 'abono') {
      setHistoricoDiaSol(null)
      return
    }
    try {
      const hist = await ponto.minhasBatidas({ desde: dataIso, ate: dataIso, limit: 100 })
      setHistoricoDiaSol(hist)
      if (tipo === 'correcao') {
        const primeiro = hist.intervalos[0]
        if (primeiro?.entrada_batida_id) {
          setSolBatidaId(String(primeiro.entrada_batida_id))
          setSolTipoBatida('entrada')
          setSolHorario(toDatetimeLocalValue(primeiro.entrada_em))
        }
      }
    } catch (err) {
      setHistoricoDiaSol(null)
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível carregar as batidas do dia.'))
    }
  }

  async function enviarSolicitacaoAjuste() {
    if (!solMotivo.trim()) {
      toast.showWarning('Informe o motivo da solicitação.')
      return
    }
    if (solTipo === 'abono') {
      if (!solDataRef) {
        toast.showWarning('Informe a data da folga.')
        return
      }
    } else {
      if (!solHorario) {
        toast.showWarning('Informe o horário solicitado.')
        return
      }
      if (solTipo === 'correcao' && !solBatidaId) {
        toast.showWarning('Selecione a batida que deseja corrigir.')
        return
      }
    }
    setEnviandoSol(true)
    try {
      if (solTipo === 'abono') {
        await ponto.criarSolicitacaoAjuste(
          {
            tipo: 'abono',
            motivo: solMotivo.trim(),
            data_ref: solDataRef,
          },
          solAnexo,
        )
      } else {
        await ponto.criarSolicitacaoAjuste(
          {
            tipo: solTipo,
            tipo_batida: solTipoBatida,
            horario_solicitado: new Date(horarioComDataRef(solDataRef, solHorario)).toISOString(),
            motivo: solMotivo.trim(),
            batida_id: solTipo === 'correcao' ? Number(solBatidaId) : null,
            data_ref: solDataRef || null,
          },
          solAnexo,
        )
      }
      toast.showSuccess('Solicitação enviada para aprovação.')
      setSolMotivo('')
      setSolAnexo(null)
      setSolHorario('')
      setSolBatidaId('')
      setMostrarSolForm(false)
      setAba('operacao')
      setFiltroSol('pendente')
      await carregar(true)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível enviar a solicitação.'))
    } finally {
      setEnviandoSol(false)
    }
  }

  async function excluirSolicitacao(s: Ponto.SolicitacaoAjuste) {
    if (!window.confirm('Excluir esta solicitação pendente?')) return
    try {
      await ponto.cancelarSolicitacaoAjuste(s.id)
      toast.showSuccess('Solicitação excluída.')
      await carregar(true)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível excluir a solicitação.'))
    }
  }

  async function baixarAnexoSol(s: Ponto.SolicitacaoAjuste) {
    try {
      const blob = await ponto.fetchSolicitacaoAjusteAnexoBlob(s.id)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = s.anexo_nome || `anexo-solicitacao-${s.id}`
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível baixar o anexo.'))
    }
  }

  const opcoesBatidaCorrecao = useMemo(() => {
    const opts: { value: string; label: string }[] = []
    for (const it of historicoDiaSol?.intervalos ?? []) {
      if (it.entrada_batida_id) {
        opts.push({
          value: String(it.entrada_batida_id),
          label: `Entrada ${formatarHora(it.entrada_em)}`,
        })
      }
      if (it.saida_batida_id && it.saida_em) {
        opts.push({
          value: String(it.saida_batida_id),
          label: `Saída ${formatarHora(it.saida_em)}`,
        })
      }
    }
    return opts
  }, [historicoDiaSol])

  const solicitacoesFiltradas = useMemo(() => {
    if (filtroSol === 'todas') return solicitacoes
    return solicitacoes.filter((s) => s.estado === filtroSol)
  }, [filtroSol, solicitacoes])

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
  const principal = acaoPrincipalPonto(emJornada, emPausa)

  const metricasMes = useMemo(
    () => calcularMetricasMes(calendario, bancoMes, bancoMesAnterior, hojeIso()),
    [calendario, bancoMes, bancoMesAnterior],
  )

  const statusRotulo = !emJornada ? 'Fora da jornada' : emPausa ? 'Em pausa' : 'Em jornada'
  const statusTone = !emJornada
    ? 'bg-slate-200 text-slate-800 dark:bg-slate-700 dark:text-slate-100'
    : emPausa
      ? 'bg-amber-100 text-amber-900 dark:bg-amber-950/60 dark:text-amber-100'
      : 'bg-emerald-100 text-emerald-900 dark:bg-emerald-950/60 dark:text-emerald-100'

  const intervalosHoje = historicoHoje?.intervalos ?? []

  const horaRelogio = relogio.toLocaleTimeString('pt-BR', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
  const dataRelogio = relogio.toLocaleDateString('pt-BR', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
  })

  const cienciaPendente = !!ciencia && !ciencia.confirmada && !!ciencia.pode_confirmar

  function rotuloEstadoSolicitacao(estadoSol: string) {
    switch (estadoSol) {
      case 'pendente':
        return 'Pendente'
      case 'aprovada':
        return 'Aprovada'
      case 'rejeitada':
        return 'Negada'
      case 'cancelada':
        return 'Excluída'
      default:
        return estadoSol
    }
  }

  function corEstadoSolicitacao(estadoSol: string) {
    switch (estadoSol) {
      case 'pendente':
        return 'text-amber-700 dark:text-amber-300'
      case 'aprovada':
        return 'text-emerald-700 dark:text-emerald-300'
      case 'rejeitada':
        return 'text-rose-700 dark:text-rose-300'
      default:
        return 'text-slate-600'
    }
  }

  const abas: { id: AbaMeuPonto; label: string }[] = [
    { id: 'operacao', label: 'Operação' },
    { id: 'espelho', label: 'Espelho do mês' },
  ]

  const filtrosSol: { id: FiltroSol; label: string }[] = [
    { id: 'todas', label: 'Todas' },
    { id: 'pendente', label: 'Pendentes' },
    { id: 'aprovada', label: 'Aprovadas' },
    { id: 'rejeitada', label: 'Negadas' },
  ]

  return (
    <PageContainer>
      <PageHeader
        title="Meu ponto"
        subtitle="Registre o ponto, acompanhe solicitações e confira o espelho do mês. Também dá para bater pelo indicador na barra superior."
        actions={
          <Button
            type="button"
            variant="ghost"
            onClick={() => setAjudaAberta(true)}
            title="Abrir ajuda do ponto"
          >
            Ajuda
          </Button>
        }
      />

      <div className="mb-4 flex flex-wrap gap-1 border-b border-slate-200 dark:border-slate-800">
        {abas.map((t) => (
          <button
            key={t.id}
            type="button"
            aria-current={aba === t.id ? 'page' : undefined}
            onClick={() => setAba(t.id)}
            className={`px-4 py-2.5 text-sm font-medium transition ${
              aba === t.id
                ? 'border-b-2 border-cyan-600 text-cyan-800 dark:border-cyan-400 dark:text-cyan-200'
                : 'text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {aba === 'operacao' ? (
        <>
          <Card className="overflow-hidden border-cyan-200/60 bg-gradient-to-br from-slate-50 via-white to-cyan-50/40 dark:border-cyan-900/40 dark:from-slate-950 dark:via-slate-900 dark:to-cyan-950/20">
            {loading && !estado ? (
              <div className="h-40 animate-pulse rounded-xl bg-slate-100 dark:bg-slate-800/50" />
            ) : (
              <div className="grid gap-6 lg:grid-cols-[1fr_minmax(0,18rem)] lg:items-center">
                <div className="space-y-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`rounded-full px-3 py-1 text-xs font-semibold ${statusTone}`}>
                      {statusRotulo}
                    </span>
                    {hintEscala ? (
                      <span className="text-xs text-slate-500 dark:text-slate-400">{hintEscala}</span>
                    ) : null}
                  </div>
                  <div>
                    <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
                      Horário atual
                    </p>
                    <p className="mt-1 font-mono text-4xl font-semibold tracking-tight text-slate-900 tabular-nums dark:text-slate-50 sm:text-5xl">
                      {horaRelogio}
                    </p>
                    <p className="mt-1 capitalize text-sm text-slate-600 dark:text-slate-300">{dataRelogio}</p>
                    {emJornada && estado?.entrada_aberta_em ? (
                      <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
                        Entrada às <strong>{formatarHoraCurta(estado.entrada_aberta_em)}</strong>
                      </p>
                    ) : null}
                  </div>
                  <div>
                    <p className="mb-2 text-sm text-slate-600 dark:text-slate-300">{principal.dica}</p>
                    {geolocationSupported() && !geoObrigatoria ? (
                      <label className="mb-3 flex items-start gap-2 text-sm text-slate-600 dark:text-slate-300">
                        <input
                          type="checkbox"
                          className="mt-0.5"
                          checked={deveIncluirGeo}
                          disabled={geoRecomendada}
                          onChange={(e) => setIncluirLocalizacao(e.target.checked)}
                        />
                        <span>
                          Incluir localização na batida
                          {geoRecomendada ? (
                            <span className="mt-0.5 block text-xs text-amber-700 dark:text-amber-300">
                              Política recomendada — fora da área gera aviso, mas registra.
                            </span>
                          ) : (
                            <span className="mt-0.5 block text-xs text-slate-500">
                              Opcional — útil no celular/APK. Se falhar, o ponto registra mesmo assim.
                            </span>
                          )}
                        </span>
                      </label>
                    ) : null}
                    {geoObrigatoria ? (
                      <p className="mb-3 text-sm text-amber-800 dark:text-amber-200">
                        Geolocalização <strong>obrigatória</strong> ({rotuloPoliticaGeo(politicaGeo)}).
                      </p>
                    ) : null}
                    {pendentesOffline > 0 ? (
                      <p className="mb-3 text-sm text-amber-800 dark:text-amber-200">
                        {pendentesOffline} batida(s) aguardando sync offline.
                      </p>
                    ) : null}
                    <Button
                      type="button"
                      disabled={batendo}
                      loading={batendo}
                      className="min-h-12 w-full max-w-sm px-8 text-base font-semibold shadow-lg shadow-cyan-500/25 sm:w-auto"
                      onClick={() => void bater()}
                    >
                      {principal.rotulo}
                    </Button>
                  </div>
                </div>

                <div className="rounded-2xl border border-slate-200/80 bg-white/70 p-4 dark:border-slate-700 dark:bg-slate-950/50">
                  <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Hoje</p>
                  {intervalosHoje.length === 0 ? (
                    <p className="mt-3 text-sm text-slate-500">Ainda sem períodos fechados hoje.</p>
                  ) : (
                    <ul className="mt-3 max-h-48 space-y-2 overflow-y-auto">
                      {intervalosHoje.map((it, idx) => (
                        <li
                          key={`${it.entrada_em}-${idx}`}
                          className="rounded-lg border border-slate-100 bg-slate-50/80 px-3 py-2 text-sm dark:border-slate-800 dark:bg-slate-900/60"
                        >
                          <div className="flex items-center justify-between gap-2">
                            <span className="font-medium text-slate-800 dark:text-slate-100">
                              Período {idx + 1}
                            </span>
                            <span
                              className={`text-xs font-semibold ${
                                it.aberto
                                  ? 'text-amber-700 dark:text-amber-300'
                                  : 'text-emerald-700 dark:text-emerald-300'
                              }`}
                            >
                              {it.aberto ? 'Em aberto' : 'Completo'}
                            </span>
                          </div>
                          <p className="mt-1 text-slate-600 dark:text-slate-300">
                            {formatarHoraCurta(it.entrada_em)}
                            {' → '}
                            {it.aberto ? '…' : formatarHoraCurta(it.saida_em)}
                            {!it.aberto ? (
                              <span className="text-slate-500"> · {formatarDuracao(it.duracao_segundos)}</span>
                            ) : null}
                          </p>
                          {(it.segundos_pausa ?? 0) > 0 ? (
                            <p className="text-xs text-slate-500">Pausa {formatarDuracao(it.segundos_pausa)}</p>
                          ) : null}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            )}
          </Card>

          {ciencia ? (
            <Card
              className={`mt-4 ${
                cienciaPendente
                  ? 'border-amber-300 ring-2 ring-amber-400/60 dark:border-amber-700 dark:ring-amber-500/40'
                  : ''
              }`}
              title={`Ciência do espelho — ${String(cienciaRef.mes).padStart(2, '0')}/${cienciaRef.ano}`}
            >
              {ciencia.confirmada ? (
                <p className="text-sm text-emerald-700 dark:text-emerald-300">
                  Você confirmou ciência
                  {ciencia.confirmado_em
                    ? ` em ${new Date(ciencia.confirmado_em).toLocaleString('pt-BR')}`
                    : ''}
                  .
                </p>
              ) : ciencia.pode_confirmar ? (
                <div className="flex flex-wrap items-center gap-3">
                  <p className="text-sm font-medium text-amber-900 dark:text-amber-100">
                    Atenção: o mês foi fechado. Confirme que leu e concorda com o espelho.
                  </p>
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() => {
                      setCalAno(cienciaRef.ano)
                      setCalMes(cienciaRef.mes)
                      setAba('espelho')
                    }}
                  >
                    Ver espelho de {String(cienciaRef.mes).padStart(2, '0')}/{cienciaRef.ano}
                  </Button>
                  <Button
                    type="button"
                    onClick={() => {
                      void (async () => {
                        try {
                          await ponto.confirmarCiencia(cienciaRef.ano, cienciaRef.mes)
                          toast.showSuccess('Ciência confirmada.')
                          await carregar(true)
                        } catch (err) {
                          toast.showError(mensagemFalhaParaToast(err, 'Não foi possível confirmar.'))
                        }
                      })()
                    }}
                  >
                    Li e concordo
                  </Button>
                </div>
              ) : (
                <p className="text-sm text-slate-500">
                  {ciencia.competencia_fechada
                    ? 'Ciência indisponível.'
                    : 'Aguarde o fechamento da competência para confirmar.'}
                </p>
              )}
            </Card>
          ) : null}

          <Card
            className="mt-4"
            title="Solicitações de ajuste"
            description="Inclusão, correção ou folga concedida (banco) — o admin aprova. Também dá para pedir pelo dia no calendário (aba Espelho)."
          >
            <div className="mb-3 flex flex-wrap gap-2">
              {filtrosSol.map((f) => (
                <button
                  key={f.id}
                  type="button"
                  onClick={() => setFiltroSol(f.id)}
                  className={`rounded-full px-3 py-1 text-xs font-semibold transition ${
                    filtroSol === f.id
                      ? 'bg-cyan-600 text-white'
                      : 'bg-slate-100 text-slate-700 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700'
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>
            <Button
              type="button"
              variant="secondary"
              onClick={() => void abrirSolicitacao('inclusao', hojeIso())}
            >
              Nova solicitação
            </Button>
            <ul className="mt-4 space-y-2 text-sm">
              {solicitacoesFiltradas.length === 0 ? (
                <li className="text-slate-500">Nenhuma solicitação neste filtro.</li>
              ) : (
                solicitacoesFiltradas.map((s) => (
                  <li
                    key={s.id}
                    className="rounded-lg border border-slate-200 px-3 py-2 dark:border-slate-800"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium">{formatarDataRef(s.data_ref)}</span>
                      <span className="text-slate-500">·</span>
                      <span>
                        {s.tipo === 'inclusao'
                          ? 'Inclusão'
                          : s.tipo === 'abono'
                            ? 'Folga (banco)'
                            : 'Correção'}
                      </span>
                      {s.tipo !== 'abono' ? (
                        <>
                          <span className="text-slate-500">·</span>
                          <span>{s.tipo_batida === 'entrada' ? 'Entrada' : 'Saída'}</span>
                        </>
                      ) : null}
                      <span className="text-slate-500">·</span>
                      <span className={corEstadoSolicitacao(s.estado)}>
                        {rotuloEstadoSolicitacao(s.estado)}
                      </span>
                    </div>
                    <p className="text-slate-600 dark:text-slate-300">{rotuloHorarioSolicitacao(s)}</p>
                    {s.estado === 'pendente' ? (
                      <button
                        type="button"
                        className="mt-1 text-xs font-medium text-rose-700 underline dark:text-rose-300"
                        onClick={() => void excluirSolicitacao(s)}
                      >
                        Excluir solicitação
                      </button>
                    ) : null}
                    {s.tem_anexo ? (
                      <button
                        type="button"
                        className="mt-1 text-xs font-medium text-cyan-700 underline dark:text-cyan-300"
                        onClick={() => void baixarAnexoSol(s)}
                      >
                        Anexo{s.anexo_nome ? `: ${s.anexo_nome}` : ''}
                      </button>
                    ) : null}
                    {s.decisao_motivo ? (
                      <p className="text-xs text-slate-500">Decisão: {s.decisao_motivo}</p>
                    ) : null}
                  </li>
                ))
              )}
            </ul>
          </Card>
        </>
      ) : null}

      {aba === 'espelho' ? (
        <div className="space-y-4">
          <PontoMetricasMes metricas={metricasMes} loading={loadingCal} />
          <Card title="Calendário do mês">
            <PontoCalendarioMes
              calendario={calendario}
              loading={loadingCal}
              diaSelecionado={diaCal}
              onSelecionarDia={(iso) => setDiaCal(iso)}
              ano={calAno}
              mes={calMes}
              onMudarMes={(ano, mes) => {
                setCalAno(ano)
                setCalMes(mes)
              }}
              onSolicitarInclusao={(iso) => void abrirSolicitacao('inclusao', iso)}
              onSolicitarCorrecao={(iso) => void abrirSolicitacao('correcao', iso)}
              onSolicitarAbono={(iso) => void abrirSolicitacao('abono', iso)}
            />
          </Card>
        </div>
      ) : null}

      <ConfirmDialog
        open={mostrarSolForm}
        title={
          solTipo === 'inclusao'
            ? 'Solicitar inclusão'
            : solTipo === 'abono'
              ? 'Solicitar folga (banco de horas)'
              : 'Solicitar correção'
        }
        hideActions
        onConfirm={() => undefined}
        onCancel={() => setMostrarSolForm(false)}
      >
        <div className="mt-4 space-y-3">
          <div className="flex flex-wrap items-end gap-3">
            <Select
              label="Tipo"
              value={solTipo}
              onChange={(v) => {
                const t = String(v) as 'inclusao' | 'correcao' | 'abono'
                if (solDataRef) void abrirSolicitacao(t, solDataRef)
                else setSolTipo(t)
              }}
              options={[
                { value: 'inclusao', label: 'Inclusão de batida' },
                { value: 'correcao', label: 'Correção de batida' },
                { value: 'abono', label: 'Folga concedida (desconta do banco)' },
              ]}
            />
            {solTipo !== 'abono' ? (
              <Select
                label="Tipo de batida"
                value={solTipoBatida}
                onChange={(v) => setSolTipoBatida(String(v) as 'entrada' | 'saida')}
                options={[
                  { value: 'entrada', label: 'Entrada' },
                  { value: 'saida', label: 'Saída' },
                ]}
              />
            ) : null}
            <Input
              label="Data de referência"
              type="date"
              value={solDataRef}
              onChange={(e) => {
                const data = e.target.value
                setSolDataRef(data)
                if (solTipo === 'inclusao') {
                  setSolHorario((atual) => horarioComDataRef(data, atual))
                }
                if (solTipo === 'correcao' || solTipo === 'abono') {
                  void abrirSolicitacao(solTipo, data)
                }
              }}
            />
            {solTipo !== 'abono' ? (
              <Input
                label="Horário solicitado"
                type="datetime-local"
                value={solHorario}
                onChange={(e) => setSolHorario(e.target.value)}
              />
            ) : null}
          </div>
          {solTipo === 'correcao' ? (
            <Select
              label="Batida a corrigir"
              value={solBatidaId}
              onChange={(v) => {
                const id = String(v)
                setSolBatidaId(id)
                const it = (historicoDiaSol?.intervalos ?? []).find(
                  (x) => String(x.entrada_batida_id) === id || String(x.saida_batida_id) === id,
                )
                if (!it) return
                if (String(it.entrada_batida_id) === id) {
                  setSolTipoBatida('entrada')
                  setSolHorario(toDatetimeLocalValue(it.entrada_em))
                  setSolDataRef(it.data)
                } else if (it.saida_em) {
                  setSolTipoBatida('saida')
                  setSolHorario(toDatetimeLocalValue(it.saida_em))
                  setSolDataRef(it.data)
                }
              }}
              options={[{ value: '', label: 'Selecione…' }, ...opcoesBatidaCorrecao]}
            />
          ) : null}
          {solTipo === 'abono' ? (
            <p className="text-sm text-slate-600 dark:text-slate-300">
              Use quando houver acordo (ex.: com o supervisor) para não trabalhar naquele dia. O dia
              aparece como folga concedida (não como falta) e as horas da jornada são descontadas do
              banco, após aprovação do admin.
            </p>
          ) : null}
          <Input
            label="Motivo"
            value={solMotivo}
            onChange={(e) => setSolMotivo(e.target.value)}
            placeholder="Descreva o motivo da solicitação"
          />
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-200">
              Anexo (opcional)
            </label>
            <input
              type="file"
              accept="application/pdf,image/*"
              className="block w-full text-sm text-slate-600 file:mr-3 file:rounded-md file:border-0 file:bg-slate-100 file:px-3 file:py-1.5 file:text-sm file:font-medium dark:text-slate-300 dark:file:bg-slate-800"
              onChange={(e) => setSolAnexo(e.target.files?.[0] ?? null)}
            />
            <p className="mt-1 text-xs text-slate-500">
              PDF ou imagem — útil para atestado ou comprovante. {solAnexo ? `Selecionado: ${solAnexo.name}` : ''}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button type="button" disabled={enviandoSol} onClick={() => void enviarSolicitacaoAjuste()}>
              Enviar solicitação
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                setMostrarSolForm(false)
                setSolAnexo(null)
              }}
            >
              Cancelar
            </Button>
          </div>
        </div>
      </ConfirmDialog>

      <PontoAjudaModal
        open={ajudaAberta}
        onClose={() => setAjudaAberta(false)}
        audiencia="colaborador"
      />
    </PageContainer>
  )
}
