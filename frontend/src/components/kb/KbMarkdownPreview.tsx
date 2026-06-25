import ReactMarkdown from 'react-markdown'
import { API_VERSION_PREFIX, resolvedApiBaseUrl } from '../../api/client'

type Props = {
  markdown: string
  className?: string
  emptyLabel?: string
}

function resolveMarkdownUrl(url: string): string {
  if (url.startsWith('/v1/')) {
    return `${resolvedApiBaseUrl()}${url}`
  }
  if (url.startsWith(`${API_VERSION_PREFIX}/`)) {
    return `${resolvedApiBaseUrl()}${url}`
  }
  return url
}

export function KbMarkdownPreview({ markdown, className = '', emptyLabel = 'Sem conteúdo.' }: Props) {
  const text = markdown.trim()
  if (!text) {
    return <p className="text-sm italic text-slate-500 dark:text-slate-400">{emptyLabel}</p>
  }
  return (
    <div className={`kb-markdown ${className}`.trim()}>
      <ReactMarkdown
        urlTransform={resolveMarkdownUrl}
        components={{
          img: ({ src, alt, ...props }) => (
            <img src={src ? resolveMarkdownUrl(src) : undefined} alt={alt ?? ''} loading="lazy" {...props} />
          ),
        }}
      >
        {markdown}
      </ReactMarkdown>
    </div>
  )
}
