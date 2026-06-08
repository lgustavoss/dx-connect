import { NavLink } from 'react-router-dom'

export type ConfigSectionTab = {
  to: string
  label: string
  end?: boolean
}

const tabClass = ({ isActive }: { isActive: boolean }) =>
  isActive
    ? 'border-b-2 border-sky-500 px-3 py-2.5 text-sm font-semibold text-slate-900 dark:border-sky-400 dark:text-white'
    : 'border-b-2 border-transparent px-3 py-2.5 text-sm font-medium text-slate-500 transition-colors hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200'

type Props = {
  tabs: ConfigSectionTab[]
  ariaLabel: string
}

export function ConfigSectionTabs({ tabs, ariaLabel }: Props) {
  return (
    <div className="border-b border-slate-200 dark:border-slate-700">
      <nav className="-mb-px flex flex-wrap gap-1" aria-label={ariaLabel}>
        {tabs.map((tab) => (
          <NavLink key={tab.to} to={tab.to} end={tab.end} className={tabClass}>
            {tab.label}
          </NavLink>
        ))}
      </nav>
    </div>
  )
}
