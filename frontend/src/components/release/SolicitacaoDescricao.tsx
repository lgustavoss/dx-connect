import { KbMarkdownPreview } from '../kb/KbMarkdownPreview'
import { solicitacoesMelhoria, type SolicitacoesMelhoria } from '../../api/client'

type Anexo = {
  id: number
  papel: string
  nome_original: string
  content_type?: string | null
  url: string
  tamanho_bytes?: number
}

function isImage(ct: string | null | undefined): boolean {
  return (ct || '').toLowerCase().startsWith('image/')
}

function isVideo(ct: string | null | undefined): boolean {
  return (ct || '').toLowerCase().startsWith('video/')
}

function isPdf(ct: string | null | undefined, nome: string): boolean {
  return (ct || '').toLowerCase() === 'application/pdf' || nome.toLowerCase().endsWith('.pdf')
}

export function SolicitacaoDescricao({
  descricao,
  anexos = [],
}: {
  descricao: string
  anexos?: Anexo[] | SolicitacoesMelhoria.Anexo[]
}) {
  const ficheiros = anexos.filter((a) => a.papel !== 'inline')
  return (
    <div className="space-y-4">
      <KbMarkdownPreview markdown={descricao} emptyLabel="Sem descrição." />
      {ficheiros.length > 0 ? (
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Anexos</p>
          <ul className="space-y-3">
            {ficheiros.map((a) => {
              const href = solicitacoesMelhoria.mediaUrl(a.url)
              if (isImage(a.content_type)) {
                return (
                  <li key={a.id}>
                    <p className="mb-1 text-xs text-slate-500">{a.nome_original}</p>
                    <img src={href} alt={a.nome_original} className="max-h-80 max-w-full rounded-lg" />
                  </li>
                )
              }
              if (isVideo(a.content_type)) {
                return (
                  <li key={a.id}>
                    <p className="mb-1 text-xs text-slate-500">{a.nome_original}</p>
                    <video className="max-h-80 w-full rounded-lg bg-black" src={href} controls preload="metadata" />
                  </li>
                )
              }
              return (
                <li key={a.id}>
                  <a
                    href={href}
                    target="_blank"
                    rel="noreferrer"
                    className="text-sm font-medium text-cyan-700 hover:underline dark:text-cyan-400"
                  >
                    {isPdf(a.content_type, a.nome_original) ? 'PDF: ' : ''}
                    {a.nome_original}
                  </a>
                </li>
              )
            })}
          </ul>
        </div>
      ) : null}
    </div>
  )
}
