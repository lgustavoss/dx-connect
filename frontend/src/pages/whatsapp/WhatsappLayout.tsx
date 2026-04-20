import { Outlet, useLocation } from 'react-router-dom'

export function WhatsappLayout() {
  const loc = useLocation()
  if (/\/whatsapp\/c\//.test(loc.pathname)) {
    return <Outlet />
  }

  const isHistorico = loc.pathname.includes('/whatsapp/historico')

  return (
    <div className="mx-auto max-w-6xl space-y-4 pb-10">
      <div>
        <h1 className="text-xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">
          {isHistorico ? 'Histórico' : 'Atendendo'}
        </h1>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
          {isHistorico
            ? 'Todo o histórico de chats encerrados.'
            : 'Chats em espera na fila e os que está a tratar neste momento.'}
        </p>
      </div>
      <Outlet />
    </div>
  )
}
