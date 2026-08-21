import { Link } from 'react-router-dom'
import { useState } from 'react'
import type { System } from '../../api/client'
import { Card } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { BrandLogo } from '../../brand'
import { SolicitacaoMelhoriaModal } from './SolicitacaoMelhoriaModal'

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

export type ReleaseNotesViewProps = {
  backTo: string
  backLabel?: string
  title: string
  description: string
  brandCaption?: string
  versionLabel: string | null
  notes: System.ReleaseNotes | null
  loading?: boolean
  showBrandLogo?: boolean
  /** CTA sugestões (#802) — desligar no SaaS Sobre se não fizer sentido. */
  showSugestoesCta?: boolean
}

/** Lista partilhada de versão + histórico filtrado por produto (#674 / #675). */
export function ReleaseNotesView({
  backTo,
  backLabel = 'Voltar',
  title,
  description,
  brandCaption,
  versionLabel,
  notes,
  loading = false,
  showBrandLogo = true,
  showSugestoesCta = true,
}: ReleaseNotesViewProps) {
  const [modalAberto, setModalAberto] = useState(false)
  const pastReleases = (notes?.releases ?? []).filter((r) => r.version !== notes?.current?.version)

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
          to={backTo}
          className="inline-flex items-center gap-1 text-sm font-medium text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-100"
        >
          <span aria-hidden>←</span> {backLabel}
        </Link>
        <h1 className="mt-3 text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-50">{title}</h1>
        {showBrandLogo ? (
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <BrandLogo variant="full" size="md" />
          </div>
        ) : null}
        {brandCaption ? <p className="mt-3 text-sm text-slate-600 dark:text-slate-400">{brandCaption}</p> : null}
        <p className={`text-sm text-slate-600 dark:text-slate-400 ${brandCaption || showBrandLogo ? 'mt-2' : 'mt-3'}`}>
          {description}
        </p>
      </div>

      <Card className="space-y-2 p-5">
        <p className="text-sm font-medium text-slate-500 dark:text-slate-400">Versão atual</p>
        <p className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-50">
          {versionLabel ?? '—'}
        </p>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          CalVer do último deploy (mesma versão nos painéis DeskRudder e SaaS).
        </p>
        {showSugestoesCta ? (
          <div className="flex flex-wrap items-center gap-3 pt-2">
            <Button type="button" variant="primary" className="text-sm" onClick={() => setModalAberto(true)}>
              Enviar sugestão / relatar problema
            </Button>
            <Link
              to="/minhas-solicitacoes"
              className="text-sm font-medium text-cyan-700 hover:underline dark:text-cyan-400"
            >
              Minhas solicitações →
            </Link>
          </div>
        ) : null}
      </Card>

      <SolicitacaoMelhoriaModal
        open={modalAberto}
        versaoContexto={versionLabel}
        onClose={() => setModalAberto(false)}
      />

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
