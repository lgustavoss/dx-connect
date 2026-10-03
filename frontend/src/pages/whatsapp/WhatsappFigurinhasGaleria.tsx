import { useEffect, useState } from 'react'

import { whatsappFigurinhas, type WhatsappFigurinhas } from '../../api/client'

type ItemGaleria = WhatsappFigurinhas.Figurinha & { url: string; blob: Blob }

type Props = {
  disabled: boolean
  onEnviar: (file: File) => void
}

function extensaoDoMimetype(mimetype: string): string {
  if (mimetype === 'image/png') return 'png'
  if (mimetype === 'image/gif') return 'gif'
  return 'webp'
}

/** Figurinhas salvas pelo próprio atendente (galeria pessoal). */
export function WhatsappFigurinhasGaleria({ disabled, onEnviar }: Props) {
  const [itens, setItens] = useState<ItemGaleria[]>([])
  const [carregando, setCarregando] = useState(true)
  const [erro, setErro] = useState<string | null>(null)

  useEffect(() => {
    let cancelado = false
    const urls: string[] = []
    void (async () => {
      try {
        const lista = await whatsappFigurinhas.listar()
        const carregados = await Promise.all(
          lista.map(async (f) => {
            try {
              const blob = await whatsappFigurinhas.arquivoBlob(f.id)
              const url = URL.createObjectURL(blob)
              urls.push(url)
              return { ...f, url, blob }
            } catch {
              return null
            }
          }),
        )
        if (!cancelado) setItens(carregados.filter((x): x is ItemGaleria => x != null))
      } catch {
        if (!cancelado) setErro('Não foi possível carregar suas figurinhas.')
      } finally {
        if (!cancelado) setCarregando(false)
      }
    })()
    return () => {
      cancelado = true
      urls.forEach((u) => URL.revokeObjectURL(u))
    }
  }, [])

  const remover = async (item: ItemGaleria) => {
    try {
      await whatsappFigurinhas.remover(item.id)
      setItens((prev) => prev.filter((x) => x.id !== item.id))
    } catch {
      setErro('Não foi possível remover a figurinha.')
    }
  }

  if (carregando) {
    return <p className="py-3 text-center text-xs text-slate-500 dark:text-slate-400">Carregando figurinhas…</p>
  }

  return (
    <div className="space-y-1">
      {erro && <p className="text-xs text-red-600 dark:text-red-400">{erro}</p>}
      {itens.length === 0 ? (
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Nenhuma figurinha salva. Passe o mouse sobre uma figurinha recebida na conversa e clique em
          «Adicionar às figurinhas».
        </p>
      ) : (
        <div className="grid max-h-48 grid-cols-4 gap-1 overflow-y-auto">
          {itens.map((item) => (
            <div key={item.id} className="group relative">
              <button
                type="button"
                disabled={disabled}
                title="Enviar figurinha"
                className="flex h-16 w-full items-center justify-center rounded-lg p-1 hover:bg-slate-100 disabled:opacity-40 dark:hover:bg-slate-800"
                onClick={() =>
                  onEnviar(
                    new File([item.blob], `figurinha-${item.id}.${extensaoDoMimetype(item.mimetype)}`, {
                      type: item.mimetype,
                    }),
                  )
                }
              >
                <img src={item.url} alt="Figurinha" className="max-h-full max-w-full object-contain" />
              </button>
              <button
                type="button"
                title="Remover das minhas figurinhas"
                aria-label="Remover das minhas figurinhas"
                className="absolute right-0 top-0 hidden h-5 w-5 items-center justify-center rounded-full bg-slate-700/80 text-[10px] leading-none text-white hover:bg-red-600 group-hover:flex"
                onClick={() => void remover(item)}
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
