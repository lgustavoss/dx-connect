import { useRef, useState, useEffect } from 'react'

interface CustomAudioPlayerProps {
  src: string
}

export function CustomAudioPlayer({ src }: CustomAudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [duration, setDuration] = useState(0)
  const [currentTime, setCurrentTime] = useState(0)
  const [speed, setSpeed] = useState(1)

  useEffect(() => {
    const audio = new Audio(src)
    audioRef.current = audio

    const onTimeUpdate = () => setCurrentTime(audio.currentTime)
    const onLoadedMetadata = () => setDuration(audio.duration || 0)
    const onEnded = () => setIsPlaying(false)

    audio.addEventListener('timeupdate', onTimeUpdate)
    audio.addEventListener('loadedmetadata', onLoadedMetadata)
    audio.addEventListener('ended', onEnded)

    if (audio.readyState >= 1) {
      setDuration(audio.duration || 0)
    }

    return () => {
      audio.pause()
      audio.removeEventListener('timeupdate', onTimeUpdate)
      audio.removeEventListener('loadedmetadata', onLoadedMetadata)
      audio.removeEventListener('ended', onEnded)
    }
  }, [src])

  const togglePlay = () => {
    if (!audioRef.current) return
    if (isPlaying) {
      audioRef.current.pause()
      setIsPlaying(false)
    } else {
      audioRef.current.playbackRate = speed
      audioRef.current.play().catch(() => {})
      setIsPlaying(true)
    }
  }

  const changeSpeed = () => {
    const nextSpeed = speed === 1 ? 1.5 : speed === 1.5 ? 2 : 1
    setSpeed(nextSpeed)
    if (audioRef.current) {
      audioRef.current.playbackRate = nextSpeed
    }
  }

  const handleProgressChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newTime = Number(e.target.value)
    setCurrentTime(newTime)
    if (audioRef.current) {
      audioRef.current.currentTime = newTime
    }
  }

  const formatTime = (time: number) => {
    if (isNaN(time) || !isFinite(time)) return '0:00'
    const mins = Math.floor(time / 60)
    const secs = Math.floor(time % 60)
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`
  }

  return (
    <div className="flex items-center gap-3 bg-slate-100 dark:bg-slate-800/80 px-3 py-2 rounded-2xl w-full max-w-[280px] shadow-sm text-slate-800 dark:text-slate-200 border border-slate-200/40 dark:border-slate-700/50">
      <button
        type="button"
        onClick={togglePlay}
        className="w-9 h-9 rounded-full bg-cyan-600 hover:bg-cyan-700 text-white flex items-center justify-center transition-colors shadow-md shadow-cyan-600/20 shrink-0 cursor-pointer"
        title={isPlaying ? 'Pausar' : 'Ouvir'}
      >
        {isPlaying ? (
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
            <path d="M5.5 3.5A1.5 1.5 0 0 1 7 5v6a1.5 1.5 0 0 1-3 0V5a1.5 1.5 0 0 1 1.5-1.5zm5 0A1.5 1.5 0 0 1 12 5v6a1.5 1.5 0 0 1-3 0V5a1.5 1.5 0 0 1 1.5-1.5z" />
          </svg>
        ) : (
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16" className="ml-0.5">
            <path d="m11.596 8.697-6.363 3.692c-.54.313-1.233-.066-1.233-.697V4.308c0-.63.692-1.01 1.233-.696l6.363 3.692a.802.802 0 0 1 0 1.393z" />
          </svg>
        )}
      </button>

      <div className="flex-1 min-w-0 flex flex-col gap-0.5">
        <input
          type="range"
          min={0}
          max={duration || 100}
          value={currentTime}
          onChange={handleProgressChange}
          className="w-full h-1 bg-slate-300 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer accent-cyan-600 focus:outline-none"
        />
        <div className="flex justify-between text-[9px] text-slate-500 font-mono">
          <span>{formatTime(currentTime)}</span>
          <span>{formatTime(duration)}</span>
        </div>
      </div>

      <button
        type="button"
        onClick={changeSpeed}
        className="text-[10px] font-bold bg-slate-200 dark:bg-slate-700 hover:bg-slate-300 dark:hover:bg-slate-600 px-2 py-1 rounded-full shrink-0 transition-colors cursor-pointer"
        title="Alterar velocidade"
      >
        {speed}x
      </button>
    </div>
  )
}
