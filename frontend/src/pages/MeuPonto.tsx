import { useCallback, useEffect, useMemo, useState } from 'react'
import { ponto, type Ponto } from '../api/client'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { PontoAjudaModal } from '../components/PontoAjudaModal'
import { PontoCalendarioMes } from '../components/PontoCalendarioMes'
import { PontoBatidaMapaModal } from '../components/PontoBatidaMapaModal'
import { PontoMetricCard } from '../components/PontoMetricCard'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Input } from '../components/ui/Input'
import { PageContainer, PageHeader } from '../components/ui/PageContainer'
import { Select } from '../components/ui/Select'
import { useToast } from '../components/ui/Toast'
import { useEventStream } from '../contexts/EventStreamContext'
import { useAuth } from '../contexts/AuthContext'
import { isCapacitorNative } from '../lib/capacitorNative'
import { geolocationSupported, getCurrentPosition, type GeoError } from '../lib/geolocation'
import {
  countPendingPontoBatidas,
  enqueuePontoBatida,
  isLikelyOfflineError,
  syncPendingPontoBatidas,
} from '../lib/pontoOfflineQueue'
import {
  formatarDuracao,
  formatarHora,
  formatarHoraCurta,
  hojeIso,
  inicioMesIso,
  rotuloPoliticaGeo,
} from '../lib/pontoFormat'
import { aplicarBatidaOptimista, coordenadasMapaIntervalo, rotuloGeoIntervalo } from '../lib/pontoOptimistic'

function acaoPrincipal(emJornada: boolean, emPausa: boolean): AcaoPrincipal {
  if (!emJornada) {
    return { tipo: 'entrada', rotulo: 'Registrar entrada', dica: 'Inicie a jornada do dia' }
  }
  if (emPausa) {
    return { tipo: 'pausa_fim', rotulo: 'Retomar jornada', dica: 'Encerrar pausa e voltar ao trabalho' }
  }
  return { tipo: 'saida', rotulo: 'Registrar saída', dica: 'Com pausa aberta, a pausa fecha automaticamente' }
}

type AcaoPrincipal = {
  tipo: Ponto.Tipo
  rotulo: string
  dica: string
}

export function MeuPonto() {
  const toast = useToast()
  const { subscribe } = useEventStream()
  const { user } = useAuth()
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
  const [coberturas, setCoberturas] = useState<Ponto.Cobertura[]>([])
  const [colegasCob, setColegasCob] = useState<Ponto.CoberturaColega[]>([])
  const [cobCobertor, setCobCobertor] = useState('')
  const [cobData, setCobData] = useState(hojeIso)
  const [cobMotivo, setCobMotivo] = useState('')
  const [enviandoCob, setEnviandoCob] = useState(false)
  const [ajudaAberta, setAjudaAberta] = useState(false)
  const [ciencia, setCiencia] = useState<Ponto.CienciaMe | null>(null)
  const cienciaRef = useMemo(() => {
    const d = new Date()
    const prev = new Date(d.getFullYear(), d.getMonth() - 1, 1)
    return { ano: prev.getFullYear(), mes: prev.getMonth() + 1 }
  }, [])
  const [banco, setBanco] = useState<Ponto.BancoHoras | null>(null)
  const [refSemana, setRefSemana] = useState(hojeIso)
  const [resumoSemana, setResumoSemana] = useState<Ponto.ResumoSemana | null>(null)
  const agora = new Date()
  const [calAno, setCalAno] = useState(agora.getFullYear())
  const [calMes, setCalMes] = useState(agora.getMonth() + 1)
  const [calendario, setCalendario] = useState<Ponto.Calendario | null>(null)
  const [diaCal, setDiaCal] = useState<string | null>(hojeIso())
  const [loadingCal, setLoadingCal] = useState(false)
  const [relogio, setRelogio] = useState(() => new Date())
  const [mostrarJust, setMostrarJust] = useState(false)
  const [incluirLocalizacao, setIncluirLocalizacao] = useState(
    () => isCapacitorNative() || geolocationSupported(),
  )
  const [geoSettings, setGeoSettings] = useState<Ponto.SettingsPublic | null>(null)
  const [pendentesOffline, setPendentesOffline] = useState(countPendingPontoBatidas())
  const [obtendoLocalizacao, setObtendoLocalizacao] = useState(false)
  const [mapaAberto, setMapaAberto] = useState<{
    lat: number
    lon: number
    label: string
  } | null>(null)
  const [justAnexo, setJustAnexo] = useState<File | null>(null)
  const [ausencias, setAusencias] = useState<Ponto.Ausencia[]>([])
  const [ausTipo, setAusTipo] = useState<'ferias' | 'folga_programada'>('folga_programada')
  const [ausDesde, setAusDesde] = useState(hojeIso)
  const [ausAte, setAusAte] = useState(hojeIso)
  const [ausMotivo, setAusMotivo] = useState('')
  const [enviandoAus, setEnviandoAus] = useState(false)
  const [heStatus, setHeStatus] = useState<Ponto.HoraExtraMeStatus | null>(null)
  const [heHist, setHeHist] = useState<Ponto.HoraExtra[]>([])
  const [heMotivo, setHeMotivo] = useState('')
  const [heModo, setHeModo] = useState<'resto_do_dia' | 'ate_horario' | 'duracao'>('resto_do_dia')
  const [heAteHorario, setHeAteHorario] = useState('20:00')
  const [heDuracaoMin, setHeDuracaoMin] = useState('60')
  const [enviandoHe, setEnviandoHe] = useState(false)

  const politicaGeo = geoSettings?.politica_geolocalizacao ?? 'opcional'
  const geoObrigatoria = politicaGeo === 'obrigatoria' && !!geoSettings?.tem_locais_ativos
  const geoRecomendada = politicaGeo === 'recomendada' && !!geoSettings?.tem_locais_ativos
  const deveIncluirGeo = geoObrigatoria || (geoRecomendada ? true : incluirLocalizacao)

  const carregar = useCallback(
    async (silencioso = false) => {
      try {
        const [me, hist, js, bh, gs, cobs, cols, cin, aus, heSt, heList] = await Promise.all([
          ponto.me(),
          ponto.minhasBatidas({ desde, ate, limit: 100 }),
          ponto.minhasJustificativas(),
          ponto.meuBancoHoras(desde, ate),
          ponto.meSettings(),
          ponto.minhasCoberturas(),
          ponto.colegasCobertura(),
          ponto.minhaCiencia(cienciaRef.ano, cienciaRef.mes),
          ponto.minhasAusencias(),
          ponto.horaExtraMeStatus(),
          ponto.minhasHoraExtra(),
        ])
        setEstado(me)
        setHistorico(hist)
        setJustifs(js)
        setBanco(bh)
        setGeoSettings(gs)
        setCoberturas(cobs)
        setColegasCob(cols)
        setCiencia(cin)
        setAusencias(aus)
        setHeStatus(heSt)
        setHeHist(heList)
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
    [ate, cienciaRef.ano, cienciaRef.mes, desde, toast],
  )

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

  const carregarResumoSemana = useCallback(
    async (silencioso = false) => {
      try {
        const rs = await ponto.meuResumoSemana(refSemana)
        setResumoSemana(rs)
      } catch (err) {
        if (!silencioso) {
          toast.showError(mensagemFalhaParaToast(err, 'Não foi possível carregar o resumo da semana.'))
        }
      }
    },
    [refSemana, toast],
  )

  useEffect(() => {
    void carregar()
  }, [carregar])

  useEffect(() => {
    const unsub = subscribe('ponto.he_atualizada', () => {
      void carregar(true)
    })
    return unsub
  }, [subscribe, carregar])

  useEffect(() => {
    void carregarResumoSemana(true)
  }, [carregarResumoSemana])

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

  async function bater(tipo: Ponto.Tipo) {
    setBatendo(true)
    const fechouPausaAuto = tipo === 'saida' && !!estado?.em_pausa
    const origem = isCapacitorNative() ? 'mobile' : 'web'
    let geo:
      | { latitude: number; longitude: number; accuracy_metros: number }
      | undefined
    try {
      if (deveIncluirGeo && geolocationSupported()) {
        setObtendoLocalizacao(true)
        try {
          const pos = await getCurrentPosition()
          geo = {
            latitude: pos.latitude,
            longitude: pos.longitude,
            accuracy_metros: pos.accuracy,
          }
        } catch (geoErr) {
          const msg = (geoErr as GeoError)?.message || 'Localização indisponível'
          if (geoObrigatoria) {
            toast.showError(`${msg} A geolocalização é obrigatória nesta instância.`)
            return
          }
          toast.showWarning(`${msg} O ponto será registado sem localização.`)
        } finally {
          setObtendoLocalizacao(false)
        }
      }

      if (!navigator.onLine) {
        enqueuePontoBatida({ tipo, ...geo })
        setPendentesOffline(countPendingPontoBatidas())
        setEstado((prev) => aplicarBatidaOptimista(prev, tipo))
        toast.showWarning('Sem ligação — batida guardada offline. Será enviada ao voltar online.')
        return
      }

      const batida = await ponto.bater({
        tipo,
        origem,
        ...(geo ?? {}),
      })
      if (batida.fora_area) {
        toast.showWarning('Batida registada fora da área permitida.')
      }
      if (fechouPausaAuto) {
        toast.showSuccess(
          geo
            ? 'Pausa encerrada automaticamente ao sair (com localização).'
            : 'Pausa encerrada automaticamente ao sair.',
        )
      } else {
        const msgs: Record<Ponto.Tipo, string> = {
          entrada: geo ? 'Entrada registrada (com localização).' : 'Entrada registrada.',
          saida: geo ? 'Saída registrada (com localização).' : 'Saída registrada.',
          pausa_inicio: geo ? 'Pausa iniciada (com localização).' : 'Pausa iniciada.',
          pausa_fim: geo ? 'Pausa encerrada (com localização).' : 'Pausa encerrada.',
        }
        toast.showSuccess(msgs[tipo])
      }
      await Promise.all([carregar(true), carregarCalendario(true), carregarResumoSemana(true)])
    } catch (err) {
      if (isLikelyOfflineError(err)) {
        enqueuePontoBatida({ tipo, ...geo })
        setPendentesOffline(countPendingPontoBatidas())
        setEstado((prev) => aplicarBatidaOptimista(prev, tipo))
        toast.showWarning('Falha de rede — batida guardada offline.')
        return
      }
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível bater o ponto.'))
    } finally {
      setObtendoLocalizacao(false)
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
      const payload = {
        data_ref: justData,
        tipo: justTipo,
        motivo: justMotivo.trim(),
      }
      if (justAnexo) {
        await ponto.criarJustificativaComAnexo(payload, justAnexo)
      } else {
        await ponto.criarJustificativa(payload)
      }
      toast.showSuccess('Justificativa enviada para aprovação.')
      setJustMotivo('')
      setJustAnexo(null)
      await carregar(true)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível enviar a justificativa.'))
    } finally {
      setEnviandoJust(false)
    }
  }

  async function solicitarAusencia() {
    if (ausAte < ausDesde) {
      toast.showWarning('A data final deve ser igual ou posterior à inicial.')
      return
    }
    setEnviandoAus(true)
    try {
      await ponto.solicitarAusencia({
        tipo: ausTipo,
        desde: ausDesde,
        ate: ausAte,
        motivo: ausMotivo.trim() || null,
      })
      toast.showSuccess('Pedido de ausência enviado.')
      setAusMotivo('')
      await carregar(true)
      await carregarCalendario(true)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível solicitar a ausência.'))
    } finally {
      setEnviandoAus(false)
    }
  }

  async function solicitarHe() {
    if (heStatus?.pedido_pendente) {
      toast.showWarning('Já existe um pedido de hora extra aguardando decisão.')
      return
    }
    if (heStatus?.he_ativa) {
      toast.showWarning('Você já tem hora extra ativa.')
      return
    }
    setEnviandoHe(true)
    try {
      await ponto.solicitarHoraExtra({
        motivo: heMotivo.trim() || null,
        modo: heModo,
        ate_horario: heModo === 'ate_horario' ? heAteHorario : null,
        duracao_minutos: heModo === 'duracao' ? Math.max(15, Number(heDuracaoMin) || 60) : null,
      })
      toast.showSuccess('Pedido de hora extra enviado.')
      setHeMotivo('')
      await carregar(true)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível solicitar hora extra.'))
    } finally {
      setEnviandoHe(false)
    }
  }

  async function solicitarCobertura() {
    if (!cobCobertor) {
      toast.showWarning('Selecione quem vai cobrir o plantão.')
      return
    }
    setEnviandoCob(true)
    try {
      await ponto.solicitarCobertura({
        cobertor_id: Number(cobCobertor),
        data_ref: cobData,
        motivo: cobMotivo.trim() || null,
      })
      toast.showSuccess('Pedido de cobertura enviado. Aguarde o cobertor e o admin.')
      setCobMotivo('')
      await carregar(true)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível solicitar a cobertura.'))
    } finally {
      setEnviandoCob(false)
    }
  }

  async function responderCob(id: number, aceitar: boolean) {
    try {
      await ponto.responderCobertura(id, { aceitar })
      toast.showSuccess(aceitar ? 'Cobertura aceita — aguarda homologação do admin.' : 'Pedido recusado.')
      await carregar(true)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível responder.'))
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
  const principal = acaoPrincipal(emJornada, emPausa)

  const statusRotulo = !emJornada ? 'Fora da jornada' : emPausa ? 'Em pausa' : 'Em jornada'
  const statusTone = !emJornada
    ? 'bg-slate-200 text-slate-800 dark:bg-slate-700 dark:text-slate-100'
    : emPausa
      ? 'bg-amber-100 text-amber-900 dark:bg-amber-950/60 dark:text-amber-100'
      : 'bg-emerald-100 text-emerald-900 dark:bg-emerald-950/60 dark:text-emerald-100'

  const hoje = hojeIso()
  const intervalosHoje = useMemo(
    () => (historico?.intervalos ?? []).filter((it) => it.data === hoje),
    [historico, hoje],
  )

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

  return (
    <PageContainer>
      <PageHeader
        title="Meu ponto"
        subtitle="Registre a jornada com um toque. Pausas e histórico ficam à mão — presença online do painel é independente."
        actions={
          <Button type="button" variant="secondary" onClick={() => setAjudaAberta(true)}>
            Como funciona o ponto
          </Button>
        }
      />

      {ciencia ? (
        <Card className="mb-4" title={`Ciência do espelho — ${String(cienciaRef.mes).padStart(2, '0')}/${cienciaRef.ano}`}>
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
              <p className="text-sm text-slate-600 dark:text-slate-300">
                O mês foi fechado pelo admin. Confirme que leu e concorda com o espelho.
              </p>
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

      {/* Hero — inspirado no dx-ponto: relógio + CTA principal */}
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
                          Política recomendada — fora da área gera aviso, mas regista.
                        </span>
                      ) : (
                        <span className="mt-0.5 block text-xs text-slate-500">
                          Opcional — útil no telemóvel/APK. Se falhar, o ponto regista na mesma.
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
                  disabled={batendo || obtendoLocalizacao}
                  loading={batendo || obtendoLocalizacao}
                  className="min-h-12 w-full max-w-sm px-8 text-base font-semibold shadow-lg shadow-cyan-500/25 sm:w-auto"
                  onClick={() => void bater(principal.tipo)}
                >
                  {obtendoLocalizacao ? 'Obtendo localização…' : principal.rotulo}
                </Button>
                <div className="mt-3 flex flex-wrap gap-2">
                  {emJornada && !emPausa ? (
                    <Button
                      type="button"
                      variant="secondary"
                      disabled={batendo}
                      onClick={() => void bater('pausa_inicio')}
                    >
                      Iniciar pausa
                    </Button>
                  ) : null}
                  {emPausa ? (
                    <Button
                      type="button"
                      variant="secondary"
                      disabled={batendo}
                      onClick={() => void bater('saida')}
                    >
                      Sair (fecha pausa)
                    </Button>
                  ) : null}
                </div>
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

      {/* Métricas — estilo cards do dx-ponto */}
      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <PontoMetricCard
          label="Trabalhado no período"
          value={formatarDuracao(historico?.total_segundos_fechados)}
          hint={`${desde} → ${ate}`}
          tone="info"
        />
        <PontoMetricCard
          label="Pausas"
          value={formatarDuracao(historico?.total_segundos_pausa ?? 0)}
          hint="Não conta como trabalhado"
          tone="neutral"
        />
        <PontoMetricCard
          label="Banco de horas"
          value={
            banco
              ? `${banco.saldo_segundos >= 0 ? '+' : '−'}${formatarDuracao(Math.abs(banco.saldo_segundos))}`
              : '—'
          }
          hint={
            banco
              ? `Esperado ${formatarDuracao(banco.segundos_esperados)} · realizado ${formatarDuracao(banco.segundos_realizados)}`
              : undefined
          }
          tone={banco && banco.saldo_segundos < 0 ? 'warn' : 'good'}
        />
      </div>

      <Card className="mt-4" title="Resumo da semana">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <p className="text-sm text-slate-600 dark:text-slate-300">
            {resumoSemana
              ? `${resumoSemana.desde} → ${resumoSemana.ate}`
              : 'Carregando…'}
          </p>
          <div className="flex gap-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                const d = new Date(`${refSemana}T12:00:00`)
                d.setDate(d.getDate() - 7)
                setRefSemana(d.toISOString().slice(0, 10))
              }}
            >
              Semana anterior
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                const d = new Date(`${refSemana}T12:00:00`)
                d.setDate(d.getDate() + 7)
                const iso = d.toISOString().slice(0, 10)
                setRefSemana(iso > hojeIso() ? hojeIso() : iso)
              }}
            >
              Próxima semana
            </Button>
          </div>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <PontoMetricCard
            label="Previsto × feito"
            value={
              resumoSemana
                ? `${formatarDuracao(resumoSemana.segundos_realizados)} / ${formatarDuracao(resumoSemana.segundos_esperados)}`
                : '—'
            }
            tone="info"
          />
          <PontoMetricCard
            label="Atrasos"
            value={String(resumoSemana?.atrasos ?? 0)}
            tone={resumoSemana && resumoSemana.atrasos > 0 ? 'warn' : 'neutral'}
          />
          <PontoMetricCard
            label="Hora extra"
            value={
              resumoSemana
                ? `${resumoSemana.he_minutos} min`
                : '—'
            }
            hint="Liberações aprovadas na semana"
            tone="neutral"
          />
          <PontoMetricCard
            label="Saldo (banco)"
            value={
              resumoSemana
                ? `${resumoSemana.saldo_segundos >= 0 ? '+' : '−'}${formatarDuracao(Math.abs(resumoSemana.saldo_segundos))}`
                : '—'
            }
            tone={resumoSemana && resumoSemana.saldo_segundos < 0 ? 'warn' : 'good'}
          />
        </div>
      </Card>

      <Card className="mt-4" title="Hora extra (WhatsApp)">
        {heStatus?.he_ativa ? (
          <p className="mb-3 text-sm text-emerald-800 dark:text-emerald-200">
            Hora extra ativa
            {heStatus.he_restante_minutos != null
              ? ` — restam cerca de ${heStatus.he_restante_minutos} min`
              : ''}
            {heStatus.he_ativa.ate_em
              ? ` (até ${formatarHora(heStatus.he_ativa.ate_em)})`
              : ''}
            .
          </p>
        ) : null}
        {heStatus?.pedido_pendente ? (
          <p className="mb-3 text-sm text-amber-800 dark:text-amber-200">
            Pedido pendente de aprovação
            {heStatus.pedido_pendente.modo ? ` (${heStatus.pedido_pendente.modo.replace(/_/g, ' ')})` : ''}
            .
          </p>
        ) : null}
        {heStatus?.ultimo_rejeitado ? (
          <p className="mb-3 text-sm text-rose-800 dark:text-rose-200">
            Último pedido negado
            {heStatus.ultimo_rejeitado.decisao_motivo
              ? `: ${heStatus.ultimo_rejeitado.decisao_motivo}`
              : '.'}
          </p>
        ) : null}
        {heStatus?.he_teto_mensal_minutos != null ? (
          <p className="mb-3 text-xs text-slate-500 dark:text-slate-400">
            Consumo no mês: {heStatus.he_consumido_mensal_minutos ?? 0} / {heStatus.he_teto_mensal_minutos}{' '}
            min
          </p>
        ) : null}
        {!heStatus?.he_ativa && !heStatus?.pedido_pendente ? (
          <div className="mb-4 flex flex-wrap items-end gap-3">
            <Select
              label="Janela desejada"
              value={heModo}
              onChange={(v) => setHeModo(String(v) as 'resto_do_dia' | 'ate_horario' | 'duracao')}
              options={[
                { value: 'resto_do_dia', label: 'Resto do dia' },
                { value: 'ate_horario', label: 'Até horário' },
                { value: 'duracao', label: 'Duração (minutos)' },
              ]}
            />
            {heModo === 'ate_horario' ? (
              <Input
                label="Até (HH:MM)"
                type="time"
                value={heAteHorario}
                onChange={(e) => setHeAteHorario(e.target.value)}
              />
            ) : null}
            {heModo === 'duracao' ? (
              <Input
                label="Minutos"
                type="number"
                min={15}
                max={1440}
                value={heDuracaoMin}
                onChange={(e) => setHeDuracaoMin(e.target.value)}
              />
            ) : null}
            <Input
              label="Motivo"
              value={heMotivo}
              onChange={(e) => setHeMotivo(e.target.value)}
              placeholder="Ex.: pico no WhatsApp"
            />
            <Button type="button" disabled={enviandoHe} onClick={() => void solicitarHe()}>
              Solicitar HE
            </Button>
          </div>
        ) : null}
        {heHist.length > 0 ? (
          <ul className="space-y-2 border-t border-slate-200 pt-3 dark:border-slate-700">
            {heHist.slice(0, 8).map((h) => (
              <li key={h.id} className="text-sm text-slate-600 dark:text-slate-300">
                <span className="font-medium text-slate-800 dark:text-slate-100">{h.estado}</span>
                {h.modo ? ` · ${h.modo.replace(/_/g, ' ')}` : ''}
                {h.motivo ? ` — ${h.motivo}` : ''}
                {h.decisao_motivo && h.estado === 'rejeitada' ? ` (${h.decisao_motivo})` : ''}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-slate-500">Nenhum pedido recente.</p>
        )}
      </Card>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
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
        </Card>

        <Card title="Histórico do período">
          <div className="mb-4 flex flex-wrap items-end gap-3">
            <Input label="De" type="date" value={desde} onChange={(e) => setDesde(e.target.value)} />
            <Input label="Até" type="date" value={ate} onChange={(e) => setAte(e.target.value)} />
            <Button type="button" variant="secondary" onClick={() => void carregar()}>
              Filtrar
            </Button>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-slate-200 text-slate-500 dark:border-slate-700 dark:text-slate-400">
                <tr>
                  <th className="py-2 pr-3 font-medium">Entrada</th>
                  <th className="py-2 pr-3 font-medium">Saída</th>
                  <th className="py-2 pr-3 font-medium">Pausas</th>
                  <th className="py-2 pr-3 font-medium">Trabalhado</th>
                  <th className="py-2 font-medium">Local</th>
                </tr>
              </thead>
              <tbody>
                {(historico?.intervalos ?? []).length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-6 text-slate-500 dark:text-slate-400">
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
                      <td className="py-2 pr-3">{formatarDuracao(it.duracao_segundos)}</td>
                      <td className="py-2">
                        {(() => {
                          const geo = rotuloGeoIntervalo(it)
                          const mapa = coordenadasMapaIntervalo(it)
                          if (!geo || !mapa) return '—'
                          return (
                            <div className="flex flex-col gap-1">
                              <span
                                className={
                                  geo.includes('fora')
                                    ? 'text-xs text-amber-700 dark:text-amber-300'
                                    : 'text-xs text-slate-600 dark:text-slate-300'
                                }
                              >
                                {geo}
                              </span>
                              <Button
                                type="button"
                                variant="ghost"
                                className="h-auto px-0 py-0 text-xs text-cyan-700 dark:text-cyan-300"
                                onClick={() =>
                                  setMapaAberto({ lat: mapa.lat, lon: mapa.lon, label: mapa.label })
                                }
                              >
                                Ver mapa
                              </Button>
                            </div>
                          )
                        })()}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      <div className="mt-4">
        <Card
          title="Justificativas"
          description="Esquecimento de batida, falta ou ponto em folga — o admin aprova."
        >
          <Button type="button" variant="secondary" onClick={() => setMostrarJust((v) => !v)}>
            {mostrarJust ? 'Ocultar formulário' : 'Nova justificativa'}
          </Button>
          {mostrarJust ? (
            <div className="mt-4 flex flex-wrap items-end gap-3">
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
              <div className="min-w-[12rem]">
                <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">
                  Anexo (opcional)
                </label>
                <input
                  type="file"
                  accept="image/*,.pdf,application/pdf"
                  className="block w-full text-sm text-slate-600 file:mr-2 file:rounded-md file:border-0 file:bg-slate-100 file:px-2 file:py-1 dark:text-slate-300 dark:file:bg-slate-800"
                  onChange={(e) => setJustAnexo(e.target.files?.[0] ?? null)}
                />
              </div>
              <Button type="button" disabled={enviandoJust} onClick={() => void enviarJustificativa()}>
                Enviar
              </Button>
            </div>
          ) : null}
          <ul className="mt-4 space-y-2 text-sm">
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
                  {j.tem_anexo ? (
                    <button
                      type="button"
                      className="mt-1 text-xs text-cyan-700 underline dark:text-cyan-300"
                      onClick={() =>
                        void ponto
                          .baixarJustificativaAnexo(j.id, j.anexo_nome)
                          .catch((err) =>
                            toast.showError(
                              mensagemFalhaParaToast(err, 'Não foi possível baixar o anexo.'),
                            ),
                          )
                      }
                    >
                      Baixar anexo{j.anexo_nome ? ` (${j.anexo_nome})` : ''}
                    </button>
                  ) : null}
                  {j.decisao_motivo ? (
                    <p className="text-xs text-slate-500">Decisão: {j.decisao_motivo}</p>
                  ) : null}
                </li>
              ))
            )}
          </ul>
        </Card>
      </div>

      <div className="mt-4">
        <Card
          title="Cobertura de plantão"
          description="Peça para um colega cobrir seu dia; ele aceita e o admin homologa."
        >
          <div className="flex flex-wrap items-end gap-3">
            <Select
              label="Quem cobre"
              value={cobCobertor}
              onChange={(v) => setCobCobertor(String(v))}
              options={[
                { value: '', label: 'Selecione' },
                ...colegasCob.map((c) => ({ value: String(c.id), label: c.nome })),
              ]}
            />
            <Input label="Data" type="date" value={cobData} onChange={(e) => setCobData(e.target.value)} />
            <Input
              label="Motivo (opcional)"
              value={cobMotivo}
              onChange={(e) => setCobMotivo(e.target.value)}
            />
            <Button type="button" disabled={enviandoCob} onClick={() => void solicitarCobertura()}>
              Solicitar
            </Button>
          </div>
          <ul className="mt-4 space-y-2 text-sm">
            {coberturas.length === 0 ? (
              <li className="text-slate-500">Nenhuma cobertura neste histórico.</li>
            ) : (
              coberturas.map((c) => {
                const souCobertor = user?.id === c.cobertor_id
                const pendenteMim = souCobertor && c.estado === 'pendente_cobertor'
                return (
                  <li
                    key={c.id}
                    className="flex flex-wrap items-start justify-between gap-2 rounded-lg border border-slate-200 px-3 py-2 dark:border-slate-800"
                  >
                    <div>
                      <p className="font-medium">
                        {c.solicitante_nome} → {c.cobertor_nome} · {c.data_ref}
                      </p>
                      <p className="capitalize text-slate-500">{c.estado.replace(/_/g, ' ')}</p>
                      {c.motivo ? <p className="text-slate-600 dark:text-slate-300">{c.motivo}</p> : null}
                    </div>
                    {pendenteMim ? (
                      <div className="flex gap-2">
                        <Button type="button" variant="secondary" onClick={() => void responderCob(c.id, true)}>
                          Aceitar
                        </Button>
                        <Button type="button" variant="ghost" onClick={() => void responderCob(c.id, false)}>
                          Recusar
                        </Button>
                      </div>
                    ) : null}
                  </li>
                )
              })
            )}
          </ul>
        </Card>
      </div>

      <div className="mt-4">
        <Card
          title="Férias / folga programada"
          description="Solicite um período; o admin aprova. Dias aprovados não geram falta automática."
        >
          <div className="flex flex-wrap items-end gap-3">
            <Select
              label="Tipo"
              value={ausTipo}
              onChange={(v) => setAusTipo(String(v) as 'ferias' | 'folga_programada')}
              options={[
                { value: 'folga_programada', label: 'Folga programada' },
                { value: 'ferias', label: 'Férias' },
              ]}
            />
            <Input
              label="De"
              type="date"
              value={ausDesde}
              onChange={(e) => setAusDesde(e.target.value)}
            />
            <Input label="Até" type="date" value={ausAte} onChange={(e) => setAusAte(e.target.value)} />
            <Input
              label="Motivo (opcional)"
              value={ausMotivo}
              onChange={(e) => setAusMotivo(e.target.value)}
            />
            <Button type="button" disabled={enviandoAus} onClick={() => void solicitarAusencia()}>
              Solicitar
            </Button>
          </div>
          <ul className="mt-4 space-y-2 text-sm">
            {ausencias.length === 0 ? (
              <li className="text-slate-500">Nenhum pedido de ausência.</li>
            ) : (
              ausencias.map((a) => (
                <li
                  key={a.id}
                  className="rounded-lg border border-slate-200 px-3 py-2 dark:border-slate-800"
                >
                  <span className="font-medium">
                    {a.tipo === 'ferias' ? 'Férias' : 'Folga programada'}
                  </span>{' '}
                  · {a.desde} → {a.ate} · <span className="capitalize">{a.estado}</span>
                  {a.motivo ? <p className="text-slate-600 dark:text-slate-300">{a.motivo}</p> : null}
                  {a.decisao_motivo ? (
                    <p className="text-xs text-slate-500">Decisão: {a.decisao_motivo}</p>
                  ) : null}
                </li>
              ))
            )}
          </ul>
        </Card>
      </div>

      <PontoAjudaModal open={ajudaAberta} onClose={() => setAjudaAberta(false)} />
      <PontoBatidaMapaModal
        open={mapaAberto != null}
        onClose={() => setMapaAberto(null)}
        latitude={mapaAberto?.lat ?? 0}
        longitude={mapaAberto?.lon ?? 0}
        titulo={mapaAberto?.label ?? 'Localização'}
      />
    </PageContainer>
  )
}
