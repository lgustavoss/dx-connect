import { Link, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import type { System } from '../../api/client'
import { solicitacoesMelhoria, type SolicitacoesMelhoria } from '../../api/client'
import { Card } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { VoltarButton } from '../../components/ui/VoltarButton'
import { BrandLogo } from '../../brand'
import { PageContainer } from '../../components/ui/PageContainer'
import { SolicitacoesMelhoriaListaTable } from '../solicitacoes/SolicitacoesMelhoriaListaTable'
import { SolicitacoesMelhoriaListaSkeleton } from '../solicitacoes/SolicitacoesMelhoriaListaSkeleton'

const CATEGORY_LABEL: Record<string, string> = {
  melhorias: 'Melhorias',
  correcoes: 'Correções',
  interno: 'Interno / Infra',
}

const PRODUCT_LABEL: Record<string, string> = {
  deskrudder: 'Produto',
  saas: 'DevOps',
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

function productClass(product: string): string {
  if (product === 'saas') {
    return 'bg-violet-50 text-violet-900 ring-violet-200/70 dark:bg-violet-950/40 dark:text-violet-100 dark:ring-violet-800/50'
  }
  return 'bg-sky-50 text-sky-900 ring-sky-200/70 dark:bg-sky-950/40 dark:text-sky-100 dark:ring-sky-800/50'
}

function formatDate(value: string): string {
  const d = value.slice(0, 10)
  const [y, m, day] = d.split('-')
  if (!y || !m || !day) return value
  return `${day}/${m}/${y}`
}

function ChangeList({
  items,
  showProductTags,
}: {
  items: System.ReleaseChange[]
  showProductTags?: boolean
}) {
  if (!items.length) {
    return <p className="text-sm text-slate-500 dark:text-slate-400">Nenhum item registrado.</p>
  }
  return (
    <ul className="space-y-3">
      {items.map((item, idx) => {
        const productKey = (item.product ?? 'deskrudder').toLowerCase()
        return (
          <li key={`${item.category}-${idx}`} className="flex items-start gap-3 text-sm leading-relaxed">
            <span className="flex shrink-0 flex-wrap items-center gap-1.5 self-start">
              {showProductTags ? (
                <span
                  className={`inline-flex min-w-[4.75rem] items-center justify-center rounded-md px-2.5 py-1 text-center text-xs font-medium leading-none ring-1 ring-inset ${productClass(productKey)}`}
                >
                  {PRODUCT_LABEL[productKey] ?? item.product ?? 'Produto'}
                </span>
              ) : null}
              <span
                className={`inline-flex min-w-[5.5rem] items-center justify-center rounded-md px-2.5 py-1 text-center text-xs font-medium leading-none ring-1 ring-inset ${categoryClass(item.category)}`}
              >
                {CATEGORY_LABEL[item.category] ?? item.category}
              </span>
            </span>
            <span className="min-w-0 flex-1 text-slate-700 dark:text-slate-200">{item.text}</span>
          </li>
        )
      })}
    </ul>
  )
}

function ReleaseBlock({
  release,
  showProductTags,
}: {
  release: System.Release
  showProductTags?: boolean
}) {
  return (
    <Card className="space-y-4 p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-50">{release.version_display}</h2>
        <time className="text-sm text-slate-500 dark:text-slate-400" dateTime={String(release.date)}>
          {formatDate(String(release.date))}
        </time>
      </div>
      <ChangeList items={release.changes} showProductTags={showProductTags} />
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
  /** Painel ops (#920): etiqueta Produto / DevOps em cada bullet. */
  showProductTags?: boolean
}

/** Lista compartilhada de versão + histórico (#674 / #920). */

const PREVIEW_MINHAS = 5
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
  showProductTags = false,
}: ReleaseNotesViewProps) {
  const navigate = useNavigate()
  const [minhas, setMinhas] = useState<SolicitacoesMelhoria.ListaItem[]>([])
  const [loadingMinhas, setLoadingMinhas] = useState(showSugestoesCta)
  const pastReleases = (notes?.releases ?? []).filter((r) => r.version !== notes?.current?.version)

  useEffect(() => {
    if (!showSugestoesCta) return
    let cancelled = false
    setLoadingMinhas(true)
    void solicitacoesMelhoria
      .minhas()
      .then((rows) => {
        if (!cancelled) setMinhas(rows)
      })
      .catch(() => {
        if (!cancelled) setMinhas([])
      })
      .finally(() => {
        if (!cancelled) setLoadingMinhas(false)
      })
    return () => {
      cancelled = true
    }
  }, [showSugestoesCta])

  if (loading) {
    return (
      <PageContainer>
        <div className="h-56 animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-800/50" />
      </PageContainer>
    )
  }

  return (
    <PageContainer spacing="relaxed">
      <div>
        <VoltarButton onClick={() => navigate(backTo)} label={backLabel} />
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
            <Button
              type="button"
              variant="primary"
              className="text-sm"
              onClick={() => navigate('/sobre/nova-solicitacao')}
            >
              Enviar sugestão / relatar problema
            </Button>
            {loadingMinhas ? null : minhas.length > 0 ? (
              <Link
                to="/minhas-solicitacoes"
                className="text-sm font-medium text-cyan-700 hover:underline dark:text-cyan-400"
              >
                Minhas solicitações ({minhas.length})
              </Link>
            ) : null}
          </div>
        ) : null}
      </Card>

      {showSugestoesCta ? (
        <Card
          title="Minhas solicitações"
          description={
            loadingMinhas
              ? 'Carregando…'
              : minhas.length > 0
                ? `${Math.min(minhas.length, PREVIEW_MINHAS)} mais recente${minhas.length === 1 ? '' : 's'}`
                : undefined
          }
          titleActions={
            !loadingMinhas && minhas.length > PREVIEW_MINHAS ? (
              <Link
                to="/minhas-solicitacoes"
                className="text-sm font-medium text-cyan-700 hover:underline dark:text-cyan-400"
              >
                Ver todas →
              </Link>
            ) : null
          }
          bodyClassName={loadingMinhas || minhas.length > 0 ? 'overflow-x-auto p-0' : 'p-6'}
        >
          {loadingMinhas ? (
            <SolicitacoesMelhoriaListaSkeleton rows={PREVIEW_MINHAS} />
          ) : minhas.length === 0 ? (
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Você ainda não enviou nenhum pedido. Use o botão acima para sugerir uma melhoria ou relatar um problema.
            </p>
          ) : (
            <SolicitacoesMelhoriaListaTable
              items={minhas.slice(0, PREVIEW_MINHAS)}
              itemPath={(solicitacaoId) => `/minhas-solicitacoes/${solicitacaoId}`}
            />
          )}
        </Card>
      ) : null}

      {notes?.current ? (
        <section className="space-y-3">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-50">O que há de novo nesta versão</h2>
          <ReleaseBlock release={notes.current} showProductTags={showProductTags} />
        </section>
      ) : (
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Ainda não há notas de versão publicadas nesta instância.
        </p>
      )}

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
                <ReleaseBlock key={release.version} release={release} showProductTags={showProductTags} />
              ))}
          </div>
        </section>
      ) : null}
    </PageContainer>
  )
}
