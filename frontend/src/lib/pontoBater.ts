/** Batida de ponto compartilhada (Meu Ponto + chip da navbar). */

import { ponto, type Ponto } from '../api/client'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { isCapacitorNative } from './capacitorNative'
import { geolocationSupported, getCurrentPosition, type GeoError } from './geolocation'
import { avisarPontoEstadoMudou } from './pontoEstadoEvent'
import {
  countPendingPontoBatidas,
  enqueuePontoBatida,
  isLikelyOfflineError,
} from './pontoOfflineQueue'
import { aplicarBatidaOptimista } from './pontoOptimistic'

export type AcaoPrincipalPonto = {
  tipo: Ponto.Tipo
  rotulo: string
  dica: string
}

export function acaoPrincipalPonto(emJornada: boolean, emPausa: boolean): AcaoPrincipalPonto {
  if (emPausa) {
    return {
      tipo: 'pausa_fim',
      rotulo: 'Bater ponto',
      dica: 'Registra a volta. O próximo toque encerra o período.',
    }
  }
  if (!emJornada) {
    return {
      tipo: 'entrada',
      rotulo: 'Bater ponto',
      dica: 'Cada toque registra o próximo horário do dia. A volta do intervalo é uma nova entrada.',
    }
  }
  return {
    tipo: 'saida',
    rotulo: 'Bater ponto',
    dica: 'Cada toque registra o próximo horário do dia. A volta do intervalo é uma nova entrada.',
  }
}

export type ToastLikePonto = {
  showSuccess: (msg: string) => void
  showError: (msg: string) => void
  showWarning: (msg: string) => void
}

export type BaterPontoResultado =
  | { ok: true; offline: boolean; estadoOptimista: Ponto.EstadoMe | null; batida?: Ponto.Batida }
  | { ok: false; offline: false }

export type BaterPontoOpcoes = {
  estado: Ponto.EstadoMe | null
  /** Preferência do usuário (checkbox). Ignorado se política for obrigatória/recomendada. */
  incluirLocalizacao?: boolean
  settings?: Ponto.SettingsPublic | null
  toast: ToastLikePonto
  /** Se true, busca settings na hora quando não informado. */
  carregarSettingsSeFaltar?: boolean
}

function deveIncluirGeo(
  settings: Ponto.SettingsPublic | null | undefined,
  incluirLocalizacao: boolean,
): { incluir: boolean; obrigatoria: boolean } {
  const politica = settings?.politica_geolocalizacao ?? 'opcional'
  const temLocais = !!settings?.tem_locais_ativos
  const obrigatoria = politica === 'obrigatoria' && temLocais
  const recomendada = politica === 'recomendada' && temLocais
  return {
    incluir: obrigatoria || (recomendada ? true : incluirLocalizacao),
    obrigatoria,
  }
}

/**
 * Registra a próxima batida do dia conforme o estado atual.
 * Atualiza o chip via `avisarPontoEstadoMudou`.
 */
export async function baterProximoPonto(opcoes: BaterPontoOpcoes): Promise<BaterPontoResultado> {
  const { estado, toast } = opcoes
  if (!estado) {
    toast.showError('Estado do ponto ainda não carregou. Tente de novo.')
    return { ok: false, offline: false }
  }

  let settings = opcoes.settings ?? null
  if (!settings && opcoes.carregarSettingsSeFaltar !== false) {
    try {
      settings = await ponto.meSettings()
    } catch {
      settings = null
    }
  }

  const { incluir, obrigatoria } = deveIncluirGeo(settings, opcoes.incluirLocalizacao ?? false)
  const acao = acaoPrincipalPonto(!!estado.em_jornada, !!estado.em_pausa)
  const tipo = acao.tipo
  const fechouPausaAuto = tipo === 'saida' && !!estado.em_pausa
  const origem = isCapacitorNative() ? 'mobile' : 'web'

  let geo: { latitude: number; longitude: number; accuracy_metros: number } | undefined

  if (incluir && geolocationSupported()) {
    try {
      const pos = await getCurrentPosition()
      geo = {
        latitude: pos.latitude,
        longitude: pos.longitude,
        accuracy_metros: pos.accuracy,
      }
    } catch (geoErr) {
      const msg = (geoErr as GeoError)?.message || 'Localização indisponível'
      if (obrigatoria) {
        toast.showError(`${msg} A geolocalização é obrigatória nesta instância.`)
        return { ok: false, offline: false }
      }
      toast.showWarning(`${msg} O ponto será registado sem localização.`)
    }
  }

  const aplicarOffline = (): BaterPontoResultado => {
    enqueuePontoBatida({ tipo, ...geo })
    const next = aplicarBatidaOptimista(estado, tipo)
    if (next) avisarPontoEstadoMudou(next)
    return { ok: true, offline: true, estadoOptimista: next }
  }

  if (!navigator.onLine) {
    const r = aplicarOffline()
    toast.showWarning('Sem ligação — batida guardada offline. Será enviada ao voltar online.')
    return r
  }

  try {
    const batida = await ponto.bater({
      tipo,
      origem,
      ...(geo ?? {}),
    })
    const imediato = aplicarBatidaOptimista(estado, tipo)
    if (imediato) avisarPontoEstadoMudou(imediato)
    else {
      try {
        const me = await ponto.me()
        avisarPontoEstadoMudou(me)
      } catch {
        avisarPontoEstadoMudou()
      }
    }

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
    return { ok: true, offline: false, estadoOptimista: imediato, batida }
  } catch (err) {
    if (isLikelyOfflineError(err)) {
      const r = aplicarOffline()
      toast.showWarning('Falha de rede — batida guardada offline.')
      return r
    }
    toast.showError(mensagemFalhaParaToast(err, 'Não foi possível bater o ponto.'))
    return { ok: false, offline: false }
  }
}

export function pendenciasOfflinePonto(): number {
  return countPendingPontoBatidas()
}
