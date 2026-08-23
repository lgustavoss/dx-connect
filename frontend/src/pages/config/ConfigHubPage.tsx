import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { PageContainer, PageHeader } from '../../components/ui/PageContainer'
import { Input } from '../../components/ui/Input'
import { CONFIG_GROUPS, configGroupIndexPath, configItemPath } from './configNav'

function normalize(s: string): string {
  return s
    .normalize('NFD')
    .replace(/\p{M}/gu, '')
    .toLowerCase()
}

/** Hub de Configurações com busca e cartões por domínio (#833). */
export function ConfigHubPage() {
  const [q, setQ] = useState('')
  const query = normalize(q.trim())

  const groups = useMemo(() => {
    if (!query) return CONFIG_GROUPS
    return CONFIG_GROUPS.map((g) => {
      const items = g.items.filter((item) => {
        const hay = normalize(
          [item.label, item.hint, ...item.keywords, g.label, g.description].join(' '),
        )
        return hay.includes(query)
      })
      return { ...g, items }
    }).filter((g) => g.items.length > 0)
  }, [query])

  return (
    <PageContainer>
      <PageHeader
        title="Configurações"
        subtitle="Encontre qualquer ajuste por domínio — ou pesquise por palavra."
      />

      <div className="relative w-full min-w-0 max-w-xl">
        <Input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Pesquisar (ex.: WhatsApp, SLA, proposta…)"
          className="pl-10"
          aria-label="Pesquisar configurações"
        />
        <span className="pointer-events-none absolute left-3 top-2.5 text-slate-400" aria-hidden>
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.3-4.3" />
          </svg>
        </span>
      </div>

      {groups.length === 0 ? (
        <p className="text-sm text-slate-500">Nenhum resultado para «{q.trim()}».</p>
      ) : (
        <div className="space-y-10">
          {groups.map((group) => (
            <section key={group.id} className="space-y-4">
              <div className="flex flex-wrap items-end justify-between gap-2 border-b border-slate-200 pb-2 dark:border-slate-800">
                <div>
                  <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">{group.label}</h2>
                  <p className="text-sm text-slate-500">{group.description}</p>
                </div>
                <Link
                  to={configGroupIndexPath(group)}
                  className="text-xs font-semibold text-cyan-700 hover:underline dark:text-cyan-400"
                >
                  Abrir secção →
                </Link>
              </div>
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                {group.items.map((item) => (
                  <Link
                    key={item.slug}
                    to={configItemPath(group, item)}
                    className="group rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-cyan-400/60 hover:ring-1 hover:ring-cyan-500/30 dark:border-slate-800 dark:bg-slate-900/80"
                  >
                    <h3 className="font-semibold text-slate-900 group-hover:text-cyan-700 dark:text-slate-100 dark:group-hover:text-cyan-300">
                      {item.label}
                    </h3>
                    <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{item.hint}</p>
                  </Link>
                ))}
              </div>
            </section>
          ))}
        </div>
      )}
    </PageContainer>
  )
}
