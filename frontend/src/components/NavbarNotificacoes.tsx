import { useEffect, useId, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { notificacoes, type Notificacoes } from '../api/client'
import { usePendenciasResumo } from '../hooks/useAlertaFilaSemResponsavel'

const POLL_ITENS_MS = 30_000

const bellIcon = (
  <svg className="size-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={1.75}
      d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
    />
  </svg>
)

function badgeText(n: number): string {
  if (n <= 0) return ''
  if (n > 99) return '99+'
  return String(n)
}

export function NavbarNotificacoes({ enabled }: { enabled: boolean }) {
  const resumo = usePendenciasResumo(enabled)
  const [aberto, setAberto] = useState(false)
  const [itens, setItens] = useState<Notificacoes.Item[]>([])
  const [loadingItens, setLoadingItens] = useState(false)
  const wrapRef = useRef<HTMLDivElement>(null)
  const menuId = useId()

  async function carregarItens() {
    if (!enabled) return
    setLoadingItens(true)
    try {
      const { itens: list } = await notificacoes.itens({ limit: 15 })
      setItens(list)
    } catch {
      setItens([])
    } finally {
      setLoadingItens(false)
    }
  }

  useEffect(() => {
    if (!aberto || !enabled) return
    void carregarItens()
    const id = window.setInterval(() => void carregarItens(), POLL_ITENS_MS)
    return () => window.clearInterval(id)
  }, [aberto, enabled])

  useEffect(() => {
    if (!aberto) return
    function onDoc(e: MouseEvent) {
      const el = wrapRef.current
      if (el && !el.contains(e.target as Node)) setAberto(false)
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [aberto])

  const total = resumo.total_pendencias
  const badge = badgeText(total)

  return (
    <div ref={wrapRef} className="relative">
      <button
        type="button"
        className="relative flex size-10 shrink-0 items-center justify-center rounded-lg text-slate-600 transition-colors hover:bg-slate-100 active:bg-slate-200 dark:text-slate-400 dark:hover:bg-slate-800 dark:active:bg-slate-700 touch-manipulation md:size-9"
        aria-label="Pendências"
        aria-expanded={aberto}
        aria-haspopup="true"
        aria-controls={aberto ? menuId : undefined}
        title="Pendências"
        onClick={() => setAberto((o) => !o)}
      >
        {bellIcon}
        {badge ? (
          <span className="absolute -right-0.5 -top-0.5 flex min-w-[1.125rem] justify-center rounded-full bg-rose-600 px-1 text-[10px] font-semibold leading-4 text-white shadow-sm dark:bg-rose-500">
            {badge}
          </span>
        ) : null}
      </button>

      {aberto ? (
        <div
          id={menuId}
          role="menu"
          className="absolute right-0 top-full z-50 mt-2 w-[min(100vw-2rem,22rem)] rounded-xl border border-slate-200/90 bg-white py-2 shadow-lg dark:border-slate-700 dark:bg-slate-900"
        >
          <div className="border-b border-slate-100 px-3 pb-2 dark:border-slate-800">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Pendências</p>
          </div>
          <div className="max-h-[min(70vh,24rem)] overflow-y-auto px-1 py-1">
            {loadingItens && itens.length === 0 ? (
              <p className="px-3 py-6 text-center text-sm text-slate-500 dark:text-slate-400">Carregando…</p>
            ) : itens.length === 0 ? (
              <p className="px-3 py-6 text-center text-sm text-slate-500 dark:text-slate-400">Sem pendências</p>
            ) : (
              <ul className="space-y-0.5">
                {itens.map((item, idx) => (
                  <li key={`${item.tipo}-${item.ticket_id ?? 'fila'}-${idx}`}>
                    <Link
                      role="menuitem"
                      to={item.href}
                      className="flex gap-2 rounded-lg px-2 py-2 text-left text-sm hover:bg-slate-50 dark:hover:bg-slate-800/80"
                      onClick={() => setAberto(false)}
                    >
                      <div className="min-w-0 flex-1">
                        <p className="truncate font-medium text-slate-900 dark:text-slate-100">{item.titulo}</p>
                        <p className="truncate text-xs text-slate-500 dark:text-slate-400">{item.descricao}</p>
                      </div>
                      <div className="flex shrink-0 flex-col items-end gap-1">
                        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700 dark:bg-slate-800 dark:text-slate-200">
                          {item.count}
                        </span>
                        <span className="text-xs font-medium text-cyan-600 dark:text-cyan-400">Ver</span>
                      </div>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </div>
          {(resumo.sem_responsavel_count > 0 || resumo.nao_lidas_count > 0) && (
            <div className="border-t border-slate-100 px-3 pt-2 text-[11px] text-slate-400 dark:border-slate-800 dark:text-slate-500">
              Fila: {resumo.sem_responsavel_count} · Não lidas: {resumo.nao_lidas_count}
            </div>
          )}
        </div>
      ) : null}
    </div>
  )
}
