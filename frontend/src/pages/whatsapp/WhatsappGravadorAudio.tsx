import { useCallback, useEffect, useRef, useState } from 'react'

import { Button } from '../../components/ui/Button'
import {
  TAMANHO_MIN_AUDIO_BYTES,
  criarMediaRecorder,
  ficheiroDeBlobGravacao,
} from '../../lib/gravacaoAudio'

type Props = {
  disabled?: boolean
  onConcluido: (file: File) => void
  onCancelar: () => void
}

export function WhatsappGravadorAudio({ disabled, onConcluido, onCancelar }: Props) {
  const [gravando, setGravando] = useState(false)
  const [segundos, setSegundos] = useState(0)
  const [erro, setErro] = useState<string | null>(null)
  const recorderRef = useRef<MediaRecorder | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const timerRef = useRef<number | null>(null)
  const canceladoRef = useRef(false)
  const onConcluidoRef = useRef(onConcluido)

  useEffect(() => {
    onConcluidoRef.current = onConcluido
  }, [onConcluido])

  const pararStream = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null
    if (timerRef.current != null) {
      window.clearInterval(timerRef.current)
      timerRef.current = null
    }
  }, [])

  const pararRecorder = useCallback(() => {
    const rec = recorderRef.current
    if (!rec || rec.state === 'inactive') return
    try {
      if (rec.state === 'recording') rec.requestData()
    } catch {
      /* ignore */
    }
    try {
      rec.stop()
    } catch {
      /* ignore */
    }
  }, [])

  useEffect(() => () => {
    canceladoRef.current = true
    const rec = recorderRef.current
    if (rec && rec.state !== 'inactive') {
      pararRecorder()
    } else {
      pararStream()
    }
  }, [pararRecorder, pararStream])

  async function iniciar() {
    if (disabled || gravando) return
    setErro(null)
    canceladoRef.current = false
    chunksRef.current = []
    if (!navigator.mediaDevices?.getUserMedia) {
      setErro('Microfone não suportado neste browser (use HTTPS).')
      return
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          channelCount: 1,
        },
      })
      streamRef.current = stream
      let recorder: MediaRecorder
      try {
        recorder = criarMediaRecorder(stream)
      } catch {
        stream.getTracks().forEach((t) => t.stop())
        streamRef.current = null
        setErro('Gravação de áudio não suportada neste browser.')
        return
      }
      recorderRef.current = recorder
      recorder.ondataavailable = (ev) => {
        if (canceladoRef.current) return
        if (ev.data && ev.data.size > 0) chunksRef.current.push(ev.data)
      }
      recorder.onerror = () => {
        setErro('Falha na gravação. Tente novamente.')
        setGravando(false)
        setSegundos(0)
        pararStream()
      }
      recorder.onstop = () => {
        pararStream()
        recorderRef.current = null
        if (canceladoRef.current) {
          chunksRef.current = []
          setGravando(false)
          setSegundos(0)
          return
        }
        const mime = recorder.mimeType || chunksRef.current[0]?.type || 'audio/webm'
        const blob = new Blob(chunksRef.current, { type: mime })
        chunksRef.current = []
        if (blob.size < TAMANHO_MIN_AUDIO_BYTES) {
          setErro('Gravação vazia ou demasiado curta. Tente novamente.')
          setGravando(false)
          setSegundos(0)
          return
        }
        setGravando(false)
        setSegundos(0)
        onConcluidoRef.current(ficheiroDeBlobGravacao(blob))
      }
      recorder.start(250)
      setGravando(true)
      setSegundos(0)
      timerRef.current = window.setInterval(() => setSegundos((s) => s + 1), 1000)
    } catch {
      pararStream()
      setErro('Não foi possível aceder ao microfone. Verifique as permissões do browser.')
    }
  }

  function parar() {
    canceladoRef.current = false
    pararRecorder()
  }

  function cancelar() {
    canceladoRef.current = true
    if (gravando) {
      const rec = recorderRef.current
      if (rec && rec.state !== 'inactive') {
        pararRecorder()
      } else {
        pararStream()
        recorderRef.current = null
      }
      chunksRef.current = []
      setGravando(false)
      setSegundos(0)
    }
    onCancelar()
  }

  const mm = String(Math.floor(segundos / 60)).padStart(2, '0')
  const ss = String(segundos % 60).padStart(2, '0')

  return (
    <div className="mb-2 rounded-xl border border-rose-200 bg-rose-50/90 p-3 dark:border-rose-900/40 dark:bg-rose-950/20">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-xs font-bold text-rose-800 dark:text-rose-200">Gravar áudio</p>
          <p className="text-[11px] text-slate-600 dark:text-slate-400">
            {gravando ? `A gravar… ${mm}:${ss}` : 'Toque em gravar e fale ao microfone'}
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="ghost" className="h-8 text-xs" onClick={cancelar}>
            Cancelar
          </Button>
          {!gravando ? (
            <Button className="h-8 text-xs" disabled={disabled} onClick={() => void iniciar()}>
              ● Gravar
            </Button>
          ) : (
            <Button variant="danger" className="h-8 text-xs" onClick={parar}>
              ■ Parar
            </Button>
          )}
        </div>
      </div>
      {gravando && (
        <div className="mt-2 flex items-center gap-2">
          <span className="h-2 w-2 animate-pulse rounded-full bg-rose-500" />
          <span className="text-[10px] text-rose-700 dark:text-rose-300">Microfone activo</span>
        </div>
      )}
      {erro && <p className="mt-2 text-xs text-rose-700 dark:text-rose-300">{erro}</p>}
    </div>
  )
}
