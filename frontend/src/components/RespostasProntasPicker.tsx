import { useCallback, useEffect, useRef, useState } from 'react'
import { respostasProntas, type RespostasProntas } from '../api/client'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { Button } from './ui/Button'
import { Input } from './ui/Input'
import { useToast } from './ui/Toast'

type Props = {
  setorId: number
  disabled?: boolean
  onInserir: (texto: string) => void
  /** Ícone compacto para a barra do compositor WhatsApp. */
  modoComposer?: boolean
}

export function RespostasProntasPicker({ setorId, disabled, onInserir, modoComposer = false }: Props) {
  const toast = useToast()
  const [aberto, setAberto] = useState(false)
  const [busca, setBusca] = useState('')
  const [debouncedBusca, setDebouncedBusca] = useState('')
  const [itens, setItens] = useState<RespostasProntas.Resposta[]>([])
  const [loading, setLoading] = useState(false)
  const painelRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const t = setTimeout(() => setDebouncedBusca(busca.trim()), 300)
    return () => clearTimeout(t)
  }, [busca])

  const carregar = useCallback(() => {
    setLoading(true)
    respostasProntas
      .disponiveis(setorId, debouncedBusca || undefined)
      .then(setItens)
      .catch((err) => {
        toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível carregar respostas prontas.'))
        setItens([])
      })
      .finally(() => setLoading(false))
  }, [debouncedBusca, setorId, toast])

  useEffect(() => {
    if (!aberto) return
    carregar()
  }, [aberto, carregar])

  useEffect(() => {
    if (!aberto) return
    function onDocClick(e: MouseEvent) {
      if (painelRef.current && !painelRef.current.contains(e.target as Node)) {
        setAberto(false)
      }
    }
    document.addEventListener('mousedown', onDocClick)
    return () => document.removeEventListener('mousedown', onDocClick)
  }, [aberto])

  function escolher(item: RespostasProntas.Resposta) {
    onInserir(item.corpo)
    setAberto(false)
    setBusca('')
  }

  const icone = (
    <svg className="size-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  )

  return (
    <div className="relative" ref={painelRef}>
      {modoComposer ? (
        <button
          type="button"
          disabled={disabled}
          title="Respostas prontas"
          aria-label="Respostas prontas"
          aria-expanded={aberto}
          onClick={() => setAberto((v) => !v)}
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-slate-600 transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-40 dark:text-slate-300 dark:hover:bg-slate-800"
        >
          {icone}
        </button>
      ) : (
        <Button
          type="button"
          variant="secondary"
          disabled={disabled}
          onClick={() => setAberto((v) => !v)}
          className="inline-flex items-center gap-2 text-xs sm:text-sm"
        >
          {icone}
          Respostas prontas
        </Button>
      )}
      {aberto ? (
        <div className="absolute bottom-full left-0 z-30 mb-2 w-[min(100vw-2rem,22rem)] rounded-xl border border-slate-200 bg-white p-3 shadow-xl dark:border-slate-800 dark:bg-slate-900">
          <Input
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            placeholder="Buscar por título…"
            className="mb-2 text-sm"
            autoFocus
          />
          <div className="dx-scrollbar max-h-56 overflow-y-auto">
            {loading ? (
              <p className="py-4 text-center text-xs text-slate-500 dark:text-slate-400">Carregando…</p>
            ) : itens.length === 0 ? (
              <p className="py-4 text-center text-xs text-slate-500 dark:text-slate-400">Nenhuma resposta encontrada.</p>
            ) : (
              <ul className="space-y-1">
                {itens.map((item) => (
                  <li key={item.id}>
                    <button
                      type="button"
                      onClick={() => escolher(item)}
                      className="w-full rounded-lg px-2 py-2 text-left text-sm transition-colors hover:bg-slate-100 dark:hover:bg-slate-800"
                    >
                      <span className="font-medium text-slate-900 dark:text-slate-100">{item.titulo}</span>
                      {item.setor_nome ? (
                        <span className="ml-1 text-xs text-slate-500 dark:text-slate-400">· {item.setor_nome}</span>
                      ) : (
                        <span className="ml-1 text-xs text-slate-500 dark:text-slate-400">· Global</span>
                      )}
                      <p className="mt-0.5 line-clamp-2 text-xs text-slate-600 dark:text-slate-400">{item.corpo}</p>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      ) : null}
    </div>
  )
}
