import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { kbPublic, portalCliente, type PortalCliente, type Kb } from '../../api/client'
import { usePortalAuth } from '../../contexts/PortalAuthContext'
import { Button } from '../../components/ui/Button'
import { useToast } from '../../components/ui/Toast'
import { mensagemFalhaParaToast } from '../../api/errorMessage'

const fieldClass =
  'w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-900 shadow-sm focus:border-teal-500 focus:outline-none focus:ring-2 focus:ring-teal-500/25'

export function PortalTicketNovo() {
  const { user } = usePortalAuth()
  const empresas = user?.empresas ?? []
  const unicaEmpresa = empresas.length === 1 ? empresas[0].id : ''
  const [empresaId, setEmpresaId] = useState<number | ''>(unicaEmpresa)
  const [setorId, setSetorId] = useState<number | ''>('')
  const [setores, setSetores] = useState<PortalCliente.Setor[]>([])
  const [pdvs, setPdvs] = useState<PortalCliente.Pdv[]>([])
  const [pdvCodigo, setPdvCodigo] = useState('')
  const [assunto, setAssunto] = useState('')
  const [descricao, setDescricao] = useState('')
  const [sugestoes, setSugestoes] = useState<Kb.ArticleBrief[]>([])
  const [saving, setSaving] = useState(false)
  const [anexos, setAnexos] = useState<File[]>([])
  const toast = useToast()
  const navigate = useNavigate()

  useEffect(() => {
    if (empresas.length === 1) setEmpresaId(empresas[0].id)
  }, [empresas])

  useEffect(() => {
    portalCliente.listSetores().then(setSetores).catch(() => setSetores([]))
  }, [])

  useEffect(() => {
    if (empresaId === '') {
      setPdvs([])
      setPdvCodigo('')
      return
    }
    portalCliente
      .listPdvs(empresaId)
      .then(setPdvs)
      .catch(() => setPdvs([]))
  }, [empresaId])

  useEffect(() => {
    const q = assunto.trim()
    if (q.length < 4) {
      setSugestoes([])
      return
    }
    const t = window.setTimeout(() => {
      kbPublic
        .listArticles({ busca: q, limit: 4 })
        .then(setSugestoes)
        .catch(() => setSugestoes([]))
    }, 350)
    return () => window.clearTimeout(t)
  }, [assunto])

  const empresaOptions = useMemo(
    () => empresas.map((e) => ({ value: String(e.id), label: e.nome })),
    [empresas],
  )

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (empresaId === '') {
      toast.showError('Selecione a empresa.')
      return
    }
    if (assunto.trim().length < 3) {
      toast.showError('Informe um assunto com pelo menos 3 caracteres.')
      return
    }
    setSaving(true)
    try {
      const ticket = await portalCliente.createTicket({
        empresa_id: empresaId,
        setor_id: setorId === '' ? null : setorId,
        assunto: assunto.trim(),
        descricao: descricao.trim() || null,
        pdv_codigo: pdvCodigo.trim() || null,
      })
      for (const file of anexos) {
        try {
          await portalCliente.uploadAnexo(ticket.id, file)
        } catch {
          /* anexo opcional — ticket já criado */
        }
      }
      toast.showSuccess('Chamado aberto com sucesso.')
      navigate(`/portal/tickets/${ticket.id}`, { replace: true })
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível abrir o chamado.'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Novo chamado</h1>
        <p className="mt-1 text-sm text-slate-600">
          Descreva o problema com clareza — isso acelera o atendimento.
        </p>
      </div>

      {sugestoes.length > 0 ? (
        <div className="rounded-2xl border border-teal-200 bg-teal-50/60 p-4">
          <p className="text-sm font-semibold text-teal-900">Antes de abrir — isso pode ajudar</p>
          <ul className="mt-2 space-y-1.5">
            {sugestoes.map((a) => (
              <li key={a.id}>
                <Link
                  to={`/portal/ajuda/${a.slug}`}
                  className="text-sm font-medium text-teal-800 underline-offset-2 hover:underline"
                >
                  {a.titulo}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <form onSubmit={handleSubmit} className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        {empresas.length === 0 ? (
          <p className="text-sm text-rose-700">
            Nenhuma empresa vinculada à sua conta. Peça ao suporte para ajustar o cadastro.
          </p>
        ) : (
          <label className="block">
            <span className="mb-1.5 block text-sm font-medium text-slate-700">Empresa</span>
            <select
              className={fieldClass}
              value={empresaId === '' ? '' : String(empresaId)}
              onChange={(e) => setEmpresaId(e.target.value ? Number(e.target.value) : '')}
              required
              disabled={empresas.length === 1}
            >
              {empresas.length > 1 ? <option value="">Selecione…</option> : null}
              {empresaOptions.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </label>
        )}

        <label className="block">
          <span className="mb-1.5 block text-sm font-medium text-slate-700">Setor</span>
          <select
            className={fieldClass}
            value={setorId === '' ? '' : String(setorId)}
            onChange={(e) => setSetorId(e.target.value ? Number(e.target.value) : '')}
          >
            <option value="">Automático / padrão</option>
            {setores.map((s) => (
              <option key={s.id} value={s.id}>
                {s.nome}
              </option>
            ))}
          </select>
          <span className="mt-1 block text-xs text-slate-500">
            Se não souber, deixe em automático — a equipe roteia o chamado.
          </span>
        </label>

        {pdvs.length > 0 ? (
          <label className="block">
            <span className="mb-1.5 block text-sm font-medium text-slate-700">PDV (opcional)</span>
            <select
              className={fieldClass}
              value={pdvCodigo}
              onChange={(e) => setPdvCodigo(e.target.value)}
            >
              <option value="">Nenhum / não se aplica</option>
              {pdvs.map((p) => (
                <option key={p.id} value={p.codigo}>
                  {p.codigo}
                  {p.papel ? ` (${p.papel})` : ''}
                </option>
              ))}
            </select>
          </label>
        ) : null}

        <label className="block">
          <span className="mb-1.5 block text-sm font-medium text-slate-700">Assunto</span>
          <input
            className={fieldClass}
            value={assunto}
            onChange={(e) => setAssunto(e.target.value)}
            placeholder="Ex.: PDV 003 não imprime cupom"
            required
            minLength={3}
            maxLength={255}
          />
        </label>

        <label className="block">
          <span className="mb-1.5 block text-sm font-medium text-slate-700">Descrição</span>
          <textarea
            className={`${fieldClass} min-h-32 resize-y`}
            value={descricao}
            onChange={(e) => setDescricao(e.target.value)}
            placeholder="O que aconteceu, desde quando, e o que já tentou fazer…"
            maxLength={20000}
          />
        </label>

        <label className="block">
          <span className="mb-1.5 block text-sm font-medium text-slate-700">Anexos (opcional)</span>
          <input
            type="file"
            multiple
            className="block w-full text-sm text-slate-600 file:mr-3 file:rounded-lg file:border-0 file:bg-teal-50 file:px-3 file:py-2 file:text-sm file:font-medium file:text-teal-800 hover:file:bg-teal-100"
            onChange={(e) => setAnexos(Array.from(e.target.files || []))}
          />
          {anexos.length > 0 ? (
            <p className="mt-1 text-xs text-slate-500">{anexos.length} ficheiro(s) selecionado(s)</p>
          ) : null}
        </label>

        <div className="flex flex-wrap gap-2 pt-1">
          <Button type="submit" disabled={saving || empresas.length === 0}>
            {saving ? 'Abrindo…' : 'Abrir chamado'}
          </Button>
          <Link
            to="/portal/tickets"
            className="inline-flex items-center rounded-xl border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            Cancelar
          </Link>
        </div>
      </form>
    </div>
  )
}
