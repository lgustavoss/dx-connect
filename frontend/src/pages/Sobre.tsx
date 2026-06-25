import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { system, type System } from '../api/client'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { Card } from '../components/ui/Card'
import { useToast } from '../components/ui/Toast'

const CATEGORY_LABEL: Record<string, string> = {
  melhorias: 'Melhorias',
  correcoes: 'Correções',
  interno: 'Interno / Infra',
}

function categoryClass(category: string): string {
  if (category === 'correcoes') {
    return 'bg-amber-50 text-amber-900 ring-amber-200/70 dark:bg-amber-950/40 dark:text-amber-100 dark:ring-amber-800/50'
  }
  if (category === 'interno') {
    return 'bg-slate-100 text-slate-700 ring-slate-200/80 dark:bg-slate-800/60 dark:text-slate-200 dark:ring-slate-700/60'
  }
  return 'bg-cyan-50 text-cyan-900 ring-cyan-200/70 dark:bg-cyan-950/40 dark:text-cyan-100 dark:ring-cyan-800/50'
}

function formatDate(value: string): string {
  const d = value.slice(0, 10)
  const [y, m, day] = d.split('-')
  if (!y || !m || !day) return value
  return `${day}/${m}/${y}`
}

function ChangeList({ items }: { items: System.ReleaseChange[] }) {
  if (!items.length) {
    return <p className="text-sm text-slate-500 dark:text-slate-400">Nenhum item registrado.</p>
  }
  return (
    <ul className="space-y-3">
      {items.map((item, idx) => (
        <li key={`${item.category}-${idx}`} className="flex items-start gap-3 text-sm leading-relaxed">
          <span
            className={`inline-flex min-w-[5.5rem] shrink-0 items-center justify-center self-start rounded-md px-2.5 py-1 text-center text-xs font-medium leading-none ring-1 ring-inset ${categoryClass(item.category)}`}
          >
            {CATEGORY_LABEL[item.category] ?? item.category}
          </span>
          <span className="min-w-0 flex-1 text-slate-700 dark:text-slate-200">{item.text}</span>
        </li>
      ))}
    </ul>
  )
}

function ReleaseBlock({ release }: { release: System.Release }) {
  return (
    <Card className="space-y-4 p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-50">{release.version_display}</h2>
        <time className="text-sm text-slate-500 dark:text-slate-400" dateTime={String(release.date)}>
          {formatDate(String(release.date))}
        </time>
      </div>
      <ChangeList items={release.changes} />
    </Card>
  )
}

export function Sobre() {
  const toast = useToast()
  const [loading, setLoading] = useState(true)
  const [info, setInfo] = useState<System.Info | null>(null)
  const [notes, setNotes] = useState<System.ReleaseNotes | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    Promise.all([system.info(), system.releaseNotes()])
      .then(([i, n]) => {
        if (!cancelled) {
          setInfo(i)
          setNotes(n)
        }
      })
      .catch((err) => {
        if (!cancelled) {
          toast.showError(mensagemFalhaParaToast(err, 'Não foi possível carregar informações da versão.'))
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [toast])

  const versionLabel =
    info?.version_display ??
    notes?.current_version_display ??
    (import.meta.env.VITE_APP_VERSION_DISPLAY as string | undefined) ??
    (import.meta.env.VITE_APP_VERSION as string | undefined) ??
    null

  const pastReleases = (notes?.releases ?? []).filter(
    (r) => r.version !== notes?.current?.version,
  )

  if (loading) {
    return (
      <div className="mx-auto max-w-3xl">
        <div className="h-56 animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-800/50" />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-3xl space-y-8 pb-10">
      <div>
        <Link
          to="/"
          className="inline-flex items-center gap-1 text-sm font-medium text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-100"
        >
          <span aria-hidden>←</span> Voltar
        </Link>
        <h1 className="mt-3 text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-50">Sobre</h1>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
          Consulte a versão em uso e o que mudou em cada atualização publicada.
        </p>
      </div>

      <Card className="space-y-2 p-5">
        <p className="text-sm font-medium text-slate-500 dark:text-slate-400">Versão atual</p>
        <p className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-50">
          {versionLabel ?? '—'}
        </p>
      </Card>

      {notes?.current ? (
        <section className="space-y-3">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-50">O que há de novo nesta versão</h2>
          <ReleaseBlock release={notes.current} />
        </section>
      ) : null}

      {pastReleases.length > 0 ? (
        <section className="space-y-3">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-50">Histórico</h2>
          <p className="text-sm text-slate-600 dark:text-slate-400">
            Atualizações publicadas em versões anteriores, do mais recente ao mais antigo.
          </p>
          <div className="space-y-4">
            {pastReleases
              .slice()
              .reverse()
              .map((release) => (
                <ReleaseBlock key={release.version} release={release} />
              ))}
          </div>
        </section>
      ) : null}
    </div>
  )
}
