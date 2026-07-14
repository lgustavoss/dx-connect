import { useEffect, useState } from 'react'
import { CustomAudioPlayer } from '../CustomAudioPlayer'
import type { Kb } from '../../api/client'

const ROTULO_SEM_LEGENDA = /^\[(Imagem|Áudio|Vídeo|Documento|Figurinha)\]/

type Props = {
  mensagem: Kb.PortalChatMensagem
  fetchMidia: () => Promise<Blob>
}

export function ChatMensagemMidia({ mensagem: m, fetchMidia }: Props) {
  const tipo = (m.tipo_midia || 'texto').toLowerCase()
  const [url, setUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState(false)

  useEffect(() => {
    if (!m.midia_disponivel || tipo === 'texto') {
      setUrl(null)
      return
    }
    let cancelled = false
    setLoading(true)
    setErr(false)
    void fetchMidia()
      .then((blob) => {
        if (cancelled) return
        setUrl(URL.createObjectURL(blob))
      })
      .catch(() => {
        if (!cancelled) setErr(true)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
      if (url) URL.revokeObjectURL(url)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- url revogado no cleanup
  }, [m.id, m.midia_disponivel, tipo])

  const legenda = m.corpo && !ROTULO_SEM_LEGENDA.test(m.corpo.trim()) ? m.corpo : null

  if (tipo === 'texto' || !m.tipo_midia) {
    return <span className="whitespace-pre-wrap">{m.corpo}</span>
  }
  if (!m.midia_disponivel) {
    return <span className="text-xs italic opacity-70">{m.corpo || 'Mídia não disponível'}</span>
  }
  if (loading || !url) return <span className="text-[10px] animate-pulse opacity-50">Carregando mídia…</span>
  if (err) return <span className="text-[10px] italic opacity-50">Erro ao carregar mídia</span>

  if (tipo === 'imagem' || tipo === 'figurinha') {
    return (
      <div className="space-y-1">
        <img src={url} alt="" className="max-h-48 max-w-full rounded-lg" />
        {legenda ? <p className="whitespace-pre-wrap text-xs">{legenda}</p> : null}
      </div>
    )
  }
  if (tipo === 'audio') {
    return (
      <div className="space-y-1">
        <CustomAudioPlayer src={url} />
        {legenda ? <p className="whitespace-pre-wrap text-xs">{legenda}</p> : null}
      </div>
    )
  }
  if (tipo === 'video') {
    return (
      <div className="space-y-1">
        <video src={url} controls className="max-h-48 max-w-full rounded-lg" />
        {legenda ? <p className="whitespace-pre-wrap text-xs">{legenda}</p> : null}
      </div>
    )
  }
  return (
    <a href={url} download className="text-xs underline">
      {m.corpo || 'Baixar ficheiro'}
    </a>
  )
}
