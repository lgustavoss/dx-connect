import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { publicCsat, type PublicCsat } from '../api/client'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { Button } from '../components/ui/Button'
import { useToast } from '../components/ui/Toast'

const STAR_PATH =
  'M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z'

const fieldClass =
  'w-full rounded-xl border border-white/10 bg-white/[0.06] px-3.5 py-3 text-[0.9375rem] text-slate-100 placeholder:text-slate-500 shadow-inner shadow-black/20 backdrop-blur-sm transition-colors focus:border-cyan-400/50 focus:outline-none focus:ring-2 focus:ring-cyan-400/25'

function EstrelaBtn({
  indice,
  nota,
  hover,
  onClick,
  onHover,
}: {
  indice: number
  nota: number
  hover: number
  onClick: () => void
  onHover: (n: number) => void
}) {
  const preenchida = indice <= (hover || nota)
  return (
    <button
      type="button"
      onClick={onClick}
      onMouseEnter={() => onHover(indice)}
      onMouseLeave={() => onHover(0)}
      className="rounded p-1 transition-transform hover:scale-110 focus:outline-none focus:ring-2 focus:ring-cyan-400/40"
      aria-label={`${indice} estrela${indice > 1 ? 's' : ''}`}
    >
      <svg width={36} height={36} viewBox="0 0 24 24" aria-hidden className={preenchida ? 'text-amber-400' : 'text-slate-600'}>
        {preenchida ? (
          <path fill="currentColor" d={STAR_PATH} />
        ) : (
          <path fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinejoin="round" d={STAR_PATH} />
        )}
      </svg>
    </button>
  )
}

function EstrelasFixas({ nota }: { nota: number }) {
  return (
    <span className="inline-flex items-center gap-0.5" aria-label={`Avaliação: ${nota} de 5`}>
      {Array.from({ length: 5 }, (_, i) => (
        <svg
          key={i}
          width={22}
          height={22}
          viewBox="0 0 24 24"
          aria-hidden
          className={i < nota ? 'text-amber-400' : 'text-slate-600'}
        >
          {i < nota ? (
            <path fill="currentColor" d={STAR_PATH} />
          ) : (
            <path fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinejoin="round" d={STAR_PATH} />
          )}
        </svg>
      ))}
    </span>
  )
}

export function AvaliarTicket() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')?.trim() ?? ''
  const [dados, setDados] = useState<PublicCsat.TicketCsat | null>(null)
  const [loading, setLoading] = useState(true)
  const [nota, setNota] = useState(0)
  const [hover, setHover] = useState(0)
  const [comentario, setComentario] = useState('')
  const [enviando, setEnviando] = useState(false)
  const { showError, showSuccess } = useToast()

  useEffect(() => {
    if (!token) {
      setLoading(false)
      return
    }
    let cancelled = false
    setLoading(true)
    publicCsat
      .get(token)
      .then((res) => {
        if (!cancelled) setDados(res)
      })
      .catch((err) => {
        if (!cancelled) {
          showError(mensagemFalhaParaToast(err, 'Não foi possível carregar a pesquisa.'))
          setDados({ status: 'invalido' })
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [token, showError])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!token || nota < 1) {
      showError('Selecione uma nota de 1 a 5 estrelas.')
      return
    }
    setEnviando(true)
    try {
      const res = await publicCsat.submit(token, {
        nota,
        comentario: comentario.trim() || null,
      })
      setDados(res)
      showSuccess('Obrigado pela sua avaliação!')
    } catch (err) {
      showError(mensagemFalhaParaToast(err, 'Não foi possível enviar a avaliação.'))
    } finally {
      setEnviando(false)
    }
  }

  const shell = (children: React.ReactNode) => (
    <div className="relative flex min-h-dvh flex-col items-center justify-center overflow-y-auto bg-[#050810] px-4 py-10 font-[family-name:'Plus_Jakarta_Sans',system-ui,sans-serif] text-slate-100 antialiased">
      <div className="mx-auto w-full max-w-[440px] space-y-6">{children}</div>
    </div>
  )

  if (!token) {
    return shell(
      <div className="text-center">
        <h1 className="text-xl font-semibold text-white">Link inválido</h1>
        <p className="mt-2 text-sm text-slate-400">O link de avaliação está incompleto ou expirou.</p>
      </div>,
    )
  }

  if (loading) {
    return shell(<p className="text-center text-sm text-slate-400">Carregando…</p>)
  }

  if (!dados || dados.status === 'invalido') {
    return shell(
      <div className="text-center">
        <h1 className="text-xl font-semibold text-white">Link inválido ou expirado</h1>
        <p className="mt-2 text-sm text-slate-400">Solicite um novo link ao suporte, se necessário.</p>
      </div>,
    )
  }

  if (dados.status === 'expirado') {
    return shell(
      <div className="text-center">
        <h1 className="text-xl font-semibold text-white">Prazo encerrado</h1>
        <p className="mt-2 text-sm text-slate-400">
          O link para avaliar o chamado {dados.protocolo ? `#${dados.protocolo}` : ''} expirou (24 horas).
        </p>
      </div>,
    )
  }

  if (dados.status === 'respondido' && dados.nota != null) {
    return shell(
      <div className="rounded-2xl border border-white/[0.08] bg-white/[0.03] p-6 text-center shadow-2xl shadow-black/40 backdrop-blur-md">
        <h1 className="text-xl font-semibold text-white">Avaliação registrada</h1>
        {dados.protocolo ? (
          <p className="mt-2 text-sm text-slate-400">Chamado {dados.protocolo}</p>
        ) : null}
        <div className="mt-4 flex justify-center">
          <EstrelasFixas nota={dados.nota} />
        </div>
        {dados.comentario ? (
          <p className="mt-4 rounded-lg bg-white/[0.04] px-3 py-2 text-left text-sm text-slate-300">{dados.comentario}</p>
        ) : null}
        <p className="mt-4 text-xs text-slate-500">Obrigado pelo seu feedback.</p>
      </div>,
    )
  }

  return shell(
    <>
      <header className="text-center">
        <h1 className="text-2xl font-semibold text-white">Como foi o atendimento?</h1>
        <p className="mt-2 text-sm text-slate-400">
          {dados.protocolo ? `Chamado ${dados.protocolo}` : 'Avalie sua experiência'}
          {dados.assunto ? ` — ${dados.assunto}` : ''}
        </p>
      </header>

      <div className="rounded-2xl border border-white/[0.08] bg-white/[0.03] p-5 shadow-2xl shadow-black/40 backdrop-blur-md sm:p-6">
        <form onSubmit={handleSubmit} className="space-y-5" noValidate>
          <div className="flex justify-center gap-1">
            {[1, 2, 3, 4, 5].map((n) => (
              <EstrelaBtn
                key={n}
                indice={n}
                nota={nota}
                hover={hover}
                onClick={() => setNota(n)}
                onHover={setHover}
              />
            ))}
          </div>
          <p className="text-center text-xs text-slate-500">1 = muito insatisfeito · 5 = excelente</p>

          <div>
            <label htmlFor="csat-comentario" className="mb-1.5 block text-sm font-medium text-slate-300">
              Comentário (opcional)
            </label>
            <textarea
              id="csat-comentario"
              rows={3}
              maxLength={2000}
              value={comentario}
              onChange={(e) => setComentario(e.target.value)}
              className={fieldClass}
              placeholder="Conte-nos mais sobre sua experiência…"
            />
          </div>

          <Button type="submit" className="w-full" disabled={enviando || nota < 1}>
            {enviando ? 'Enviando…' : 'Enviar avaliação'}
          </Button>
        </form>
      </div>
    </>,
  )
}
