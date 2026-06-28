import { useEffect, useState } from 'react'

type Props = {
  file: File
}

export function WhatsappPreviaAnexo({ file }: Props) {
  const [url, setUrl] = useState<string | null>(null)

  useEffect(() => {
    const u = URL.createObjectURL(file)
    setUrl(u)
    return () => URL.revokeObjectURL(u)
  }, [file])

  if (!url) return null

  if (file.type.startsWith('image/')) {
    return (
      <img
        src={url}
        alt=""
        className="mt-2 max-h-40 max-w-full rounded-lg border border-slate-200 object-contain dark:border-slate-700"
      />
    )
  }

  if (file.type.startsWith('video/')) {
    return <video controls src={url} className="mt-2 max-h-40 max-w-full rounded-lg border border-slate-200 dark:border-slate-700" />
  }

  if (file.type.startsWith('audio/')) {
    return <audio controls src={url} className="mt-2 w-full max-w-sm" />
  }

  return (
    <p className="mt-2 text-[11px] text-slate-500 dark:text-slate-400">
      {(file.size / 1024).toFixed(0)} KB • {file.type || 'ficheiro'}
    </p>
  )
}
