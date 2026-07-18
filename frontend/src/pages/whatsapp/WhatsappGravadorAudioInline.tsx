import { useCallback, useEffect, useRef, useState } from 'react'
import { Button } from '../../components/ui/Button'

type Props = {
  disabled?: boolean
  onConcluido: (file: File) => void
  onCancelar: () => void
}

/** Gravação compacta integrada na barra de composição (#443). */
export function WhatsappGravadorAudioInline({ disabled, onConcluido, onCancelar }: Props) {
  const [gravando, setGravando] = useState(false)
  const [segundos, setSegundos] = useState(0)
  const [erro, setErro] = useState<string | null>(null)
  const recorderRef = useRef<MediaRecorder | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const timerRef = useRef<number | null>(null)
  const iniciouRef = useRef(false)
  const canceladoRef = useRef(false)

  const pararStream = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null
    if (timerRef.current != null) {
      window.clearInterval(timerRef.current)
      timerRef.current = null
    }
  }, [])

  useEffect(() => {
    if (disabled || iniciouRef.current) return
    iniciouRef.current = true
    canceladoRef.current = false
    void (async () => {
      setErro(null)
      chunksRef.current = []
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
        streamRef.current = stream
        const mime = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
          ? 'audio/webm;codecs=opus'
          : MediaRecorder.isTypeSupported('audio/webm')
            ? 'audio/webm'
            : ''
        const recorder = mime ? new MediaRecorder(stream, { mimeType: mime }) : new MediaRecorder(stream)
        recorderRef.current = recorder
        recorder.ondataavailable = (ev) => {
          if (canceladoRef.current) return
          if (ev.data.size > 0) chunksRef.current.push(ev.data)
        }
        recorder.onstop = () => {
          pararStream()
          if (canceladoRef.current) {
            chunksRef.current = []
            setGravando(false)
            return
          }
          const blob = new Blob(chunksRef.current, { type: recorder.mimeType || 'audio/webm' })
          if (blob.size === 0) {
            setErro('Gravação vazia.')
            setGravando(false)
            return
          }
          const ext = blob.type.includes('ogg') ? 'ogg' : 'webm'
          onConcluido(new File([blob], `audio-${Date.now()}.${ext}`, { type: blob.type || 'audio/webm' }))
        }
        recorder.start(250)
        setGravando(true)
        timerRef.current = window.setInterval(() => setSegundos((s) => s + 1), 1000)
      } catch {
        pararStream()
        setErro('Microfone indisponível.')
      }
    })()
    return () => {
      canceladoRef.current = true
      pararStream()
      const rec = recorderRef.current
      if (rec && rec.state !== 'inactive') rec.stop()
    }
  }, [disabled, onConcluido, pararStream])

  const mm = String(Math.floor(segundos / 60)).padStart(2, '0')
  const ss = String(segundos % 60).padStart(2, '0')

  function parar() {
    canceladoRef.current = false
    const rec = recorderRef.current
    if (rec && rec.state !== 'inactive') rec.stop()
    recorderRef.current = null
  }

  function cancelar() {
    canceladoRef.current = true
    chunksRef.current = []
    pararStream()
    const rec = recorderRef.current
    if (rec && rec.state !== 'inactive') rec.stop()
    recorderRef.current = null
    setGravando(false)
    onCancelar()
  }

  return (
    <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-rose-200 bg-rose-50/90 px-3 py-2 dark:border-rose-900/40 dark:bg-rose-950/20">
      <div className="flex items-center gap-2 text-xs">
        {gravando && <span className="h-2 w-2 animate-pulse rounded-full bg-rose-500" />}
        <span className="font-medium text-rose-800 dark:text-rose-200">
          {gravando ? `A gravar ${mm}:${ss}` : 'A preparar microfone…'}
        </span>
      </div>
      <div className="flex gap-2">
        <Button variant="ghost" className="h-8 text-xs" onClick={cancelar}>
          Cancelar
        </Button>
        <Button variant="danger" className="h-8 text-xs" disabled={!gravando} onClick={parar}>
          Enviar áudio
        </Button>
      </div>
      {erro && <p className="w-full text-xs text-rose-700 dark:text-rose-300">{erro}</p>}
    </div>
  )
}
