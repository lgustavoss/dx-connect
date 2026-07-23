import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { BrandLogo } from '../../brand'
import { saasPublic } from '../../api/client'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { isSaasControlPlaneFrontend } from '../../lib/saasControlPlane'
import { MarketingLayout } from './MarketingLayout'

export function TrialPage() {
  const enabled = isSaasControlPlaneFrontend()
  const [empresa, setEmpresa] = useState('')
  const [slug, setSlug] = useState('')
  const [contatoNome, setContatoNome] = useState('')
  const [contatoEmail, setContatoEmail] = useState('')
  const [notas, setNotas] = useState('')
  const [solicitarProv, setSolicitarProv] = useState(false)
  const [saving, setSaving] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  const [okMsg, setOkMsg] = useState<string | null>(null)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setErro(null)
    setOkMsg(null)
    setSaving(true)
    try {
      const res = await saasPublic.trial({
        empresa: empresa.trim(),
        slug: slug.trim().toLowerCase(),
        contato_nome: contatoNome.trim(),
        contato_email: contatoEmail.trim(),
        notas: notas.trim() || null,
        solicitar_provisionamento: solicitarProv,
      })
      setOkMsg(res.mensagem)
      setEmpresa('')
      setSlug('')
      setContatoNome('')
      setContatoEmail('')
      setNotas('')
      setSolicitarProv(false)
    } catch (err) {
      setErro(mensagemFalhaParaToast(err, 'Não foi possível enviar o pedido de trial.'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <MarketingLayout>
      <header className="border-b border-white/5 bg-[#071826]/85 backdrop-blur-xl">
        <div className="mx-auto flex w-full max-w-3xl items-center justify-between gap-4 px-5 py-4 sm:px-8">
          <Link to="/">
            <BrandLogo variant="full" size="md" markVariant="onDark" />
          </Link>
          <Link to="/" className="text-sm font-medium text-sky-300 hover:text-sky-200">
            Voltar à landing
          </Link>
        </div>
      </header>

      <main className="mx-auto w-full max-w-3xl px-5 py-12 sm:px-8">
        <h1 className="text-3xl font-bold tracking-tight text-white">Pedir trial DeskRudder</h1>
        <p className="mt-3 text-slate-300">
          Preencha os dados da sua empresa de suporte. A equipa DeskRudder analisa o pedido e entra em
          contacto.
        </p>

        {!enabled ? (
          <p className="mt-8 rounded-2xl border border-amber-400/30 bg-amber-400/10 px-4 py-3 text-sm text-amber-100">
            O formulário de trial só está ativo na instância comercial DeskRudder.
          </p>
        ) : (
          <form onSubmit={onSubmit} className="mt-8 space-y-5 rounded-2xl border border-white/10 bg-white/5 p-6">
            {erro ? (
              <p className="rounded-xl border border-red-400/30 bg-red-500/10 px-3 py-2 text-sm text-red-100">
                {erro}
              </p>
            ) : null}
            {okMsg ? (
              <p className="rounded-xl border border-emerald-400/30 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-100">
                {okMsg}
              </p>
            ) : null}

            <label className="block space-y-1.5">
              <span className="text-sm font-medium text-slate-200">Empresa</span>
              <input
                required
                value={empresa}
                onChange={(e) => setEmpresa(e.target.value)}
                className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white placeholder:text-slate-500 focus:border-sky-400/50 focus:outline-none focus:ring-2 focus:ring-sky-400/25"
              />
            </label>
            <label className="block space-y-1.5">
              <span className="text-sm font-medium text-slate-200">Slug desejado</span>
              <input
                required
                value={slug}
                onChange={(e) => setSlug(e.target.value)}
                placeholder="ex.: minha-empresa"
                className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 font-mono text-sm text-white placeholder:text-slate-500 focus:border-sky-400/50 focus:outline-none focus:ring-2 focus:ring-sky-400/25"
              />
              <span className="text-xs text-slate-400">Letras minúsculas, números e hífens.</span>
            </label>
            <div className="grid gap-5 sm:grid-cols-2">
              <label className="block space-y-1.5">
                <span className="text-sm font-medium text-slate-200">O seu nome</span>
                <input
                  required
                  value={contatoNome}
                  onChange={(e) => setContatoNome(e.target.value)}
                  className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white focus:border-sky-400/50 focus:outline-none focus:ring-2 focus:ring-sky-400/25"
                />
              </label>
              <label className="block space-y-1.5">
                <span className="text-sm font-medium text-slate-200">E-mail</span>
                <input
                  required
                  type="email"
                  value={contatoEmail}
                  onChange={(e) => setContatoEmail(e.target.value)}
                  className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white focus:border-sky-400/50 focus:outline-none focus:ring-2 focus:ring-sky-400/25"
                />
              </label>
            </div>
            <label className="block space-y-1.5">
              <span className="text-sm font-medium text-slate-200">Notas (opcional)</span>
              <textarea
                rows={3}
                value={notas}
                onChange={(e) => setNotas(e.target.value)}
                className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white focus:border-sky-400/50 focus:outline-none focus:ring-2 focus:ring-sky-400/25"
              />
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-300">
              <input
                type="checkbox"
                checked={solicitarProv}
                onChange={(e) => setSolicitarProv(e.target.checked)}
                className="rounded border-white/20"
              />
              Solicitar provisionamento da instância (fila para a equipa)
            </label>
            <button
              type="submit"
              disabled={saving}
              className="inline-flex items-center justify-center rounded-2xl bg-gradient-to-r from-sky-500 via-sky-400 to-cyan-400 px-6 py-3 text-sm font-semibold text-white shadow-lg disabled:opacity-60"
            >
              {saving ? 'A enviar…' : 'Enviar pedido de trial'}
            </button>
          </form>
        )}
      </main>
    </MarketingLayout>
  )
}
