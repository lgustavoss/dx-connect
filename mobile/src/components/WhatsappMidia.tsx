import { createElement, useEffect, useState } from 'react'
import { ActivityIndicator, Image, Linking, Platform, Pressable, StyleSheet, Text, View } from 'react-native'

import { whatsapp } from '../api/client'
import { colors } from '../lib/brand'
import { getMidiaUrl, resolveMidiaUrl } from '../lib/midiaCache'

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
  const [url, setUrl] = useState<string | null>(() => getMidiaUrl(chatId, mensagemId))
  const [erro, setErro] = useState<string | null>(null)
  const [aCarregar, setACarregar] = useState(!url && disponivel !== false)

  useEffect(() => {
    if (url || disponivel === false) return
    let cancel = false
    setACarregar(true)
    resolveMidiaUrl(chatId, mensagemId, () => whatsapp.midiaBlob(chatId, mensagemId))
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

  const cor = outbound ? colors.white : colors.text
  const captionEl = caption?.trim() ? (
    <Text style={[styles.caption, { color: cor }]}>{caption.trim()}</Text>
  ) : null

  if (disponivel === false) {
    return <Text style={[styles.aviso, { color: cor }]}>Mídia expirada</Text>
  }
  if (aCarregar) {
    return <ActivityIndicator color={outbound ? colors.white : colors.teal} style={{ marginVertical: 8 }} />
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

  if (eTipoAudio(tipo) && Platform.OS === 'web') {
    return (
      <View>
        {createElement('audio', { src: url, controls: true, style: { width: 220, marginTop: 4 } })}
        {captionEl}
      </View>
    )
  }

  if (eTipoVideo(tipo) && Platform.OS === 'web') {
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

  const rotulo = eTipoAudio(tipo) ? 'Áudio' : eTipoVideo(tipo) ? 'Vídeo' : nome || 'Documento'
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

const styles = StyleSheet.create({
  img: { width: 220, height: 220, borderRadius: 8, backgroundColor: '#00000022' },
  caption: { marginTop: 6, fontSize: 15, lineHeight: 20 },
  aviso: { fontSize: 14, fontStyle: 'italic', marginVertical: 4 },
  link: { fontSize: 15, fontWeight: '700', textDecorationLine: 'underline', marginVertical: 4 },
})
