import { useEffect, useState } from 'react'
import { fetchChatInternoMidiaBlob, type ChatInterno } from '../../api/client'

const ROTULO_SEM_LEGENDA = /^(📷 Imagem|🎬 Vídeo|🎵 Áudio|📄 Documento)$/

type Props = {
  conversaId: number
  mensagem: ChatInterno.Mensagem
  textoClaro?: boolean
}

export function ChatInternoConteudoMensagem({ conversaId, mensagem, textoClaro }: Props) {
  const tipo = (mensagem.tipo_midia || 'texto').toLowerCase()
  const [url, setUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState(false)

  useEffect(() => {
    if (!mensagem.midia_disponivel || tipo === 'texto') {
      setUrl(null)
      return
    }
    let cancelled = false
    setLoading(true)
    setErr(false)
    void fetchChatInternoMidiaBlob(conversaId, mensagem.id)
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
    }
  }, [conversaId, mensagem.id, mensagem.midia_disponivel, tipo])

  useEffect(() => {
    return () => {
      if (url) URL.revokeObjectURL(url)
    }
  }, [url])

  const legenda =
    mensagem.corpo && !ROTULO_SEM_LEGENDA.test(mensagem.corpo.trim()) ? mensagem.corpo : null

  if (tipo === 'texto' || !mensagem.tipo_midia || mensagem.tipo_midia === 'texto') {
    return (
      <p
        className={`whitespace-pre-wrap break-words [overflow-wrap:anywhere] ${
          textoClaro ? 'text-white' : 'text-slate-900 dark:text-slate-100'
        }`}
      >
        {mensagem.corpo}
      </p>
    )
  }

  if (!mensagem.midia_disponivel) {
    return <p className="text-sm italic opacity-70">{mensagem.corpo || 'Mídia indisponível'}</p>
  }

  if (loading || !url) {
    return <p className="text-xs animate-pulse opacity-50">Carregando mídia…</p>
  }

  if (err) {
    return <p className="text-xs italic opacity-50">Erro ao carregar mídia</p>
  }

  const mediaClass = 'max-h-64 max-w-full rounded-lg border border-black/5 shadow-sm'

  if (tipo === 'imagem') {
    return (
      <div className="space-y-1">
        <img src={url} alt="" className={`${mediaClass} cursor-zoom-in`} />
        {legenda && (
          <p className={`whitespace-pre-wrap break-words text-sm [overflow-wrap:anywhere] ${textoClaro ? 'text-cyan-50' : ''}`}>
            {legenda}
          </p>
        )}
      </div>
    )
  }

  if (tipo === 'video') {
    return (
      <div className="space-y-1">
        <video src={url} controls className={mediaClass} />
        {legenda && <p className="whitespace-pre-wrap break-words text-sm [overflow-wrap:anywhere]">{legenda}</p>}
      </div>
    )
  }

  if (tipo === 'audio') {
    return (
      <div className="space-y-1">
        <audio src={url} controls className="max-w-full" />
        {legenda && <p className="whitespace-pre-wrap break-words text-sm [overflow-wrap:anywhere]">{legenda}</p>}
      </div>
    )
  }

  return (
    <div className="space-y-1">
      <a
        href={url}
        download={mensagem.nome_arquivo || 'arquivo'}
        className={`inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm underline ${
          textoClaro
            ? 'border-cyan-400/40 text-cyan-50 hover:bg-cyan-500/20'
            : 'border-slate-200 bg-white text-slate-800 hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100'
        }`}
      >
        📄 {mensagem.nome_arquivo || 'Documento'}
      </a>
      {legenda && <p className="whitespace-pre-wrap break-words text-sm [overflow-wrap:anywhere]">{legenda}</p>}
    </div>
  )
}
