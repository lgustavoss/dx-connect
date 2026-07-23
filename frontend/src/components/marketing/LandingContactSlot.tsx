import { useEffect, useId, useState, type FormEvent } from 'react'
import { saasPublic } from '../../api/client'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { landingMailtoHref } from '../../content/landing'
import { isSaasControlPlaneFrontend } from '../../lib/saasControlPlane'

type Variant = 'hero' | 'section'

type Props = {
  variant?: Variant
  label: string
  className?: string
}

/**
 * Slot de contacto comercial B2B (#516 / DR-06).
 * Control-plane: formulário → /v1/saas/public/contato (não usa /kb).
 * Sem control-plane: fallback mailto.
 */
export function LandingContactSlot({ variant = 'hero', label, className = '' }: Props) {
  const formEnabled = isSaasControlPlaneFrontend()
  const [open, setOpen] = useState(false)
  const titleId = useId()

  const base =
    variant === 'hero'
      ? 'group inline-flex items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-sky-500 via-sky-400 to-cyan-400 px-6 py-3.5 text-sm font-semibold text-white shadow-[0_16px_40px_rgba(14,165,233,0.25)] transition duration-200 hover:-translate-y-0.5 hover:shadow-[0_20px_50px_rgba(14,165,233,0.32)] focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-300 focus-visible:ring-offset-2 focus-visible:ring-offset-[#071826]'
      : 'group inline-flex items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-sky-500 via-sky-400 to-cyan-400 px-6 py-3 text-sm font-semibold text-white shadow-[0_10px_30px_rgba(14,165,233,0.2)] transition duration-200 hover:-translate-y-0.5 hover:shadow-[0_14px_35px_rgba(14,165,233,0.28)] focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-300'

  const ctaClass = `${base} ${className}`.trim()

  if (!formEnabled) {
    return (
      <a
        id={variant === 'section' ? 'contato-cta' : undefined}
        href={landingMailtoHref()}
        className={ctaClass}
        data-landing-contact-slot={variant}
      >
        <span>{label}</span>
        <ArrowIcon />
      </a>
    )
  }

  return (
    <>
      <button
        type="button"
        id={variant === 'section' ? 'contato-cta' : undefined}
        className={ctaClass}
        data-landing-contact-slot={variant}
        onClick={() => setOpen(true)}
      >
        <span>{label}</span>
        <ArrowIcon />
      </button>
      {open ? <ContatoComercialModal titleId={titleId} onClose={() => setOpen(false)} /> : null}
    </>
  )
}

function ArrowIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="none" className="size-4 transition duration-200 group-hover:translate-x-0.5" aria-hidden>
      <path d="M4 10h12M12 5l5 5-5 5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function ContatoComercialModal({ titleId, onClose }: { titleId: string; onClose: () => void }) {
  const [nome, setNome] = useState('')
  const [email, setEmail] = useState('')
  const [empresa, setEmpresa] = useState('')
  const [mensagem, setMensagem] = useState('')
  const [saving, setSaving] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  const [okMsg, setOkMsg] = useState<string | null>(null)

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setErro(null)
    setOkMsg(null)
    setSaving(true)
    try {
      const res = await saasPublic.contato({
        nome: nome.trim(),
        email: email.trim(),
        empresa: empresa.trim() || null,
        mensagem: mensagem.trim(),
      })
      setOkMsg(res.mensagem)
      setNome('')
      setEmail('')
      setEmpresa('')
      setMensagem('')
    } catch (err) {
      setErro(mensagemFalhaParaToast(err, 'Não foi possível enviar a mensagem.'))
    } finally {
      setSaving(false)
    }
  }

  const field =
    'w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white placeholder:text-slate-500 focus:border-sky-400/50 focus:outline-none focus:ring-2 focus:ring-sky-400/25'

  return (
    <div
      className="fixed inset-0 z-[100] flex items-end justify-center bg-black/70 p-4 backdrop-blur-sm sm:items-center"
      role="presentation"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="w-full max-w-lg rounded-2xl border border-white/10 bg-[#0b1c2b] p-5 shadow-2xl sm:p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 id={titleId} className="text-xl font-semibold text-white">
              Tire dúvidas sobre o DeskRudder
            </h2>
            <p className="mt-1 text-sm text-slate-300">Fale conosco — a equipa comercial responde por e-mail.</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg px-2 py-1 text-slate-400 hover:bg-white/5 hover:text-white"
            aria-label="Fechar"
          >
            ✕
          </button>
        </div>

        <form onSubmit={onSubmit} className="mt-5 space-y-4">
          {erro ? (
            <p className="rounded-xl border border-red-400/30 bg-red-500/10 px-3 py-2 text-sm text-red-100">{erro}</p>
          ) : null}
          {okMsg ? (
            <p className="rounded-xl border border-emerald-400/30 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-100">
              {okMsg}
            </p>
          ) : null}

          <label className="block space-y-1.5">
            <span className="text-sm font-medium text-slate-200">Nome</span>
            <input required value={nome} onChange={(e) => setNome(e.target.value)} className={field} />
          </label>
          <label className="block space-y-1.5">
            <span className="text-sm font-medium text-slate-200">E-mail</span>
            <input
              required
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className={field}
            />
          </label>
          <label className="block space-y-1.5">
            <span className="text-sm font-medium text-slate-200">Empresa (opcional)</span>
            <input value={empresa} onChange={(e) => setEmpresa(e.target.value)} className={field} />
          </label>
          <label className="block space-y-1.5">
            <span className="text-sm font-medium text-slate-200">Mensagem</span>
            <textarea
              required
              rows={4}
              value={mensagem}
              onChange={(e) => setMensagem(e.target.value)}
              placeholder="Como podemos ajudar?"
              className={field}
            />
          </label>
          <div className="flex flex-wrap justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="rounded-xl px-4 py-2 text-sm font-medium text-slate-300 hover:bg-white/5"
            >
              Fechar
            </button>
            <button
              type="submit"
              disabled={saving || !!okMsg}
              className="rounded-xl bg-gradient-to-r from-sky-500 to-cyan-400 px-5 py-2 text-sm font-semibold text-white disabled:opacity-60"
            >
              {saving ? 'A enviar…' : 'Enviar mensagem'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
