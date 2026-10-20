import { Button } from './ui/Button'
import { IconCopy } from './ui/IconCopy'
import { iniciarDownloadAppWindows, urlDownloadAppNaInstancia } from '../lib/desktopInstaller'

type Props = {
  onCopiar?: (texto: string, sucesso: string) => void
  /** Compacto para rodapé do login. */
  variante?: 'painel' | 'login'
}

/** Download do Setup do atendente (botão inicia o .exe; link curto `/app/download` para compartilhar). */
export function DesktopAppDownloadCard({ onCopiar, variante = 'painel' }: Props) {
  const linkCurto = urlDownloadAppNaInstancia()

  if (variante === 'login') {
    return (
      <p className="text-center text-sm text-slate-400">
        No computador do atendimento,{' '}
        <button
          type="button"
          className="font-medium text-cyan-400/90 underline-offset-2 hover:text-cyan-300 hover:underline"
          onClick={() => iniciarDownloadAppWindows()}
        >
          baixe o app DeskRudder para Windows
        </button>
        .
      </p>
    )
  }

  return (
    <section className="space-y-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 dark:border-slate-700 dark:bg-slate-800/40">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="max-w-3xl">
          <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-100">App para Windows</h2>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
            Instalador do DeskRudder no PC do atendente (painel + acesso remoto). O botão inicia o download nesta
            tela; o link curto serve para compartilhar.
          </p>
        </div>
        <Button
          type="button"
          variant="secondary"
          title="Baixar DeskRudder Setup para Windows"
          onClick={() => iniciarDownloadAppWindows()}
        >
          Baixar app Windows
        </Button>
      </div>
      {onCopiar ? (
        <div className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900">
          <div className="min-w-0 flex-1">
            <p className="text-xs font-medium text-slate-500 dark:text-slate-400">Link amigável</p>
            <p className="truncate font-mono text-sm text-slate-800 dark:text-slate-100" title={linkCurto}>
              {linkCurto}
            </p>
          </div>
          <button
            type="button"
            title="Copiar link"
            className="inline-flex size-9 shrink-0 items-center justify-center rounded-lg text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
            onClick={() => onCopiar(linkCurto, 'Link do app copiado.')}
          >
            <IconCopy className="size-4" />
          </button>
        </div>
      ) : null}
    </section>
  )
}
