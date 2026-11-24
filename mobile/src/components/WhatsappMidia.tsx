import { createElement, useEffect, useMemo, useState } from 'react'
import {
  ActivityIndicator,
  Image,
  Linking,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native'
import { setAudioModeAsync, useAudioPlayer, useAudioPlayerStatus } from 'expo-audio'
import { useVideoPlayer, VideoView } from 'expo-video'

import { whatsapp } from '../api/client'
import { type Cores } from '../lib/brand'
import { useCores } from '../lib/tema'
import { getMidiaUrl, resolveMidiaUrl } from '../lib/midiaCache'
import { Icon } from './Icon'

export function eTipoImagem(tipo?: string | null): boolean {
  const t = (tipo || '').toLowerCase()
  return t === 'imagem' || t === 'image' || t === 'figurinha' || t === 'sticker'
}

export function eTipoAudio(tipo?: string | null): boolean {
  const t = (tipo || '').toLowerCase()
  return t === 'audio' || t === 'ptt' || t === 'voice'
}

export function eTipoVideo(tipo?: string | null): boolean {
  return (tipo || '').toLowerCase() === 'video'
}

export function temArquivoMidia(tipo?: string | null): boolean {
  const t = (tipo || '').toLowerCase()
  return Boolean(t) && t !== 'texto'
}

function abrirUrl(url: string) {
  if (Platform.OS === 'web') {
    globalThis.open?.(url, '_blank', 'noopener,noreferrer')
    return
  }
  void Linking.openURL(url)
}

function formatarTempo(segundos: number): string {
  const s = Math.max(0, Math.floor(segundos || 0))
  const mm = String(Math.floor(s / 60)).padStart(2, '0')
  const ss = String(s % 60).padStart(2, '0')
  return `${mm}:${ss}`
}

function MidiaAudioNativo({ url, outbound }: { url: string; outbound: boolean }) {
  const styles = usarEstilos()
  const cores = useCores()
  const player = useAudioPlayer(url)
  const status = useAudioPlayerStatus(player)
  const cor = outbound ? cores.sobre : cores.text

  useEffect(() => {
    void setAudioModeAsync({ playsInSilentMode: true }).catch(() => {
      /* iOS silencioso — sem isso o áudio pode ficar mudo */
    })
  }, [])

  const tocando = status.playing
  const duracao = status.duration || 0
  const atual = status.currentTime || 0

  return (
    <View style={styles.audioRow}>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={tocando ? 'Pausar áudio' : 'Reproduzir áudio'}
        onPress={() => {
          if (tocando) player.pause()
          else {
            if (duracao > 0 && atual >= duracao - 0.25) {
              void player.seekTo(0)
            }
            player.play()
          }
        }}
        style={[styles.audioBotao, { backgroundColor: outbound ? 'rgba(255,255,255,0.2)' : cores.tealSoft }]}
      >
        <Icon name={tocando ? 'pause' : 'play'} size={18} color={outbound ? cores.sobre : cores.teal} />
      </Pressable>
      <Text style={[styles.audioTempo, { color: cor }]}>
        {formatarTempo(atual)} / {formatarTempo(duracao)}
      </Text>
    </View>
  )
}

function MidiaVideoNativo({ url }: { url: string }) {
  const styles = usarEstilos()
  const player = useVideoPlayer(url, (p) => {
    p.loop = false
  })
  return (
    <VideoView
      player={player}
      style={styles.video}
      nativeControls
      contentFit="contain"
      fullscreenOptions={{ enable: true }}
    />
  )
}

type Props = {
  chatId: number
  mensagemId: number
  tipo?: string | null
  disponivel?: boolean
  nome?: string | null
  caption?: string | null
  outbound: boolean
}

export function WhatsappMidia({ chatId, mensagemId, tipo, disponivel, nome, caption, outbound }: Props) {
  const styles = usarEstilos()
  const cores = useCores()
  const [url, setUrl] = useState<string | null>(() => getMidiaUrl(chatId, mensagemId))
  const [erro, setErro] = useState<string | null>(null)
  const [aCarregar, setACarregar] = useState(!url && disponivel !== false)

  useEffect(() => {
    if (url || disponivel === false) return
    let cancel = false
    setACarregar(true)
    resolveMidiaUrl(chatId, mensagemId, () => whatsapp.midiaBytes(chatId, mensagemId))
      .then((u) => {
        if (!cancel) setUrl(u)
      })
      .catch((e) => {
        if (!cancel) setErro(e instanceof Error ? e.message : 'Mídia indisponível')
      })
      .finally(() => {
        if (!cancel) setACarregar(false)
      })
    return () => {
      cancel = true
    }
  }, [chatId, mensagemId, url, disponivel])

  const cor = outbound ? cores.sobre : cores.text
  const captionEl = caption?.trim() ? (
    <Text style={[styles.caption, { color: cor }]}>{caption.trim()}</Text>
  ) : null

  if (disponivel === false) {
    return <Text style={[styles.aviso, { color: cor }]}>Mídia expirada</Text>
  }
  if (aCarregar) {
    return <ActivityIndicator color={outbound ? cores.sobre : cores.teal} style={{ marginVertical: 8 }} />
  }
  if (erro || !url) {
    return <Text style={[styles.aviso, { color: cor }]}>{erro || 'Mídia indisponível'}</Text>
  }

  if (eTipoImagem(tipo)) {
    return (
      <View>
        <Image source={{ uri: url }} style={styles.img} resizeMode="cover" />
        {captionEl}
      </View>
    )
  }

  if (eTipoAudio(tipo)) {
    if (Platform.OS === 'web') {
      return (
        <View>
          {createElement('audio', { src: url, controls: true, style: { width: 220, marginTop: 4 } })}
          {captionEl}
        </View>
      )
    }
    return (
      <View>
        <MidiaAudioNativo url={url} outbound={outbound} />
        {captionEl}
      </View>
    )
  }

  if (eTipoVideo(tipo)) {
    if (Platform.OS === 'web') {
      return (
        <View>
          {createElement('video', {
            src: url,
            controls: true,
            style: { width: 220, marginTop: 4, borderRadius: 8, backgroundColor: '#000' },
          })}
          {captionEl}
        </View>
      )
    }
    return (
      <View>
        <MidiaVideoNativo url={url} />
        {captionEl}
      </View>
    )
  }

  const rotulo = nome || 'Documento'
  return (
    <View>
      {Platform.OS === 'web' ? (
        createElement(
          'a',
          { href: url, target: '_blank', rel: 'noopener noreferrer', download: nome || undefined, style: { color: cor } },
          createElement(Text, { style: [styles.link, { color: cor }] }, rotulo),
        )
      ) : (
        <Pressable onPress={() => abrirUrl(url)}>
          <Text style={[styles.link, { color: cor }]}>{rotulo}</Text>
        </Pressable>
      )}
      {captionEl}
    </View>
  )
}

function usarEstilos() {
  const cores = useCores()
  return useMemo(() => criarEstilos(cores), [cores])
}

function criarEstilos(cores: Cores) {
  return StyleSheet.create({
    img: { width: 220, height: 220, borderRadius: 8, backgroundColor: '#00000022' },
    video: { width: 220, height: 160, borderRadius: 8, backgroundColor: '#000', marginTop: 4 },
    caption: { marginTop: 6, fontSize: 15, lineHeight: 20 },
    aviso: { fontSize: 14, fontStyle: 'italic', marginVertical: 4 },
    link: { fontSize: 15, fontWeight: '700', textDecorationLine: 'underline', marginVertical: 4 },
    audioRow: { flexDirection: 'row', alignItems: 'center', gap: 10, marginTop: 4, minWidth: 180 },
    audioBotao: {
      width: 36,
      height: 36,
      borderRadius: 18,
      alignItems: 'center',
      justifyContent: 'center',
    },
    audioTempo: { fontSize: 13, fontVariant: ['tabular-nums'], fontWeight: '600' },
  })
}
