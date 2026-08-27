import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { ApiError, saasClientes, saasModulos, saasPlanos, type SaasCatalogo } from '../../api/client'
import { Card } from '../../components/ui/Card'
import { Input } from '../../components/ui/Input'
import { Select } from '../../components/ui/Select'
import { useToast } from '../../components/ui/Toast'
import { useVoltarAnterior } from '../../hooks/useVoltarAnterior'
import { FormSection } from '../../components/ui/FormSection'
import { InlineCadastroFooter } from '../../components/ui/InlineCadastroPanel'
import { CadastroFormPageShell } from '../../components/ui/CadastroFormPageShell'
import { SemPermissao } from '../SemPermissao'
import { CarregamentoFalhou } from '../../components/ui/CarregamentoFalhou'
import { interpretarFalhaCarregamento, mensagemFalhaParaToast } from '../../api/errorMessage'
import {
  STATUS_CLIENTE_SAAS,
  type StatusClienteSaaS,
  saasBaseDomain,
  urlInstanciaFromSlug,
} from '../../lib/saasControlPlane'

function todayIso(): string {
  return new Date().toISOString().slice(0, 10)
}

function slugFromNome(nome: string): string {
  return nome
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 80)
}

export function SaasLicencaForm() {
  const { id } = useParams<{ id?: string }>()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const toast = useToast()
  const voltarAnterior = useVoltarAnterior('/saas/licencas')

  const clienteId = id ? parseInt(id, 10) : NaN
  const isEdit = id != null

  const [loading, setLoading] = useState(isEdit)
  const [saving, setSaving] = useState(false)
  const [forbidden, setForbidden] = useState(false)
  const [indisponivel, setIndisponivel] = useState(false)
  const [inexistente, setInexistente] = useState<{ detalhe?: string } | null>(null)

  const [nome, setNome] = useState('')
  const [slug, setSlug] = useState('')
  const [slugTouched, setSlugTouched] = useState(false)
  const [status, setStatus] = useState<StatusClienteSaaS>('trial')
  const [planoId, setPlanoId] = useState<number | ''>('')
  const [planosOpts, setPlanosOpts] = useState<SaasCatalogo.Plano[]>([])
  const [modulosOpts, setModulosOpts] = useState<SaasCatalogo.Modulo[]>([])
  const [moduloIds, setModuloIds] = useState<number[]>([])
  const [usuariosContratados, setUsuariosContratados] = useState('3')
  const [precoNegociado, setPrecoNegociado] = useState('')
  const [pendingSnap, setPendingSnap] = useState<string[] | null>(null)
  const [dataInicio, setDataInicio] = useState(todayIso)
  const [dataRenovacao, setDataRenovacao] = useState('')
  const [contatoNome, setContatoNome] = useState('')
  const [contatoEmail, setContatoEmail] = useState('')
  const [notas, setNotas] = useState('')
  const [leadComercialId, setLeadComercialId] = useState<number | null>(null)
  const [baseDomain, setBaseDomain] = useState(saasBaseDomain())

  function formatPreco(v: number): string {
    return `R$ ${v.toLocaleString('pt-BR', { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`
  }

  function toggleModulo(mid: number) {
    setModuloIds((prev) => (prev.includes(mid) ? prev.filter((x) => x !== mid) : [...prev, mid]))
  }

  useEffect(() => {
    if (isEdit) return
    const preNome = searchParams.get('nome')?.trim() || ''
    const preEmpresa = searchParams.get('empresa')?.trim() || ''
    const preEmail = searchParams.get('email')?.trim() || ''
    const preContato = searchParams.get('contato_nome')?.trim() || ''
    const preNotas = searchParams.get('notas')?.trim() || ''
    const preLead = searchParams.get('lead_id')?.trim() || ''
    const nomeInicial = preEmpresa || preNome
    if (nomeInicial) {
      setNome(nomeInicial)
      setSlug(slugFromNome(nomeInicial))
    }
    if (preContato || preNome) setContatoNome(preContato || preNome)
    if (preEmail) setContatoEmail(preEmail)
    if (preNotas) setNotas(preNotas)
    if (preLead) {
      const n = parseInt(preLead, 10)
      if (Number.isFinite(n)) setLeadComercialId(n)
    }
  }, [isEdit, searchParams])

  useEffect(() => {
    let cancelled = false
    saasClientes
      .resumo()
      .then((r) => {
        if (cancelled) return
        if (r.base_dominio_provisionamento) setBaseDomain(saasBaseDomain(r.base_dominio_provisionamento))
      })
      .catch(() => {
        /* domínio via env / default */
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    Promise.all([saasPlanos.list(), saasModulos.list()])
      .then(([planos, mods]) => {
        if (cancelled) return
        setPlanosOpts(planos)
        setModulosOpts(mods)
      })
      .catch(() => {
        /* selects vazios */
      })
    return () => {
      cancelled = true
    }
  }, [])

  const planoSelecionado = useMemo(
    () => (planoId === '' ? null : planosOpts.find((p) => p.id === Number(planoId)) ?? null),
    [planoId, planosOpts],
  )

  const inclusos = planoSelecionado?.usuarios_inclusos ?? 3
  const extraUnit = Number(planoSelecionado?.preco_usuario_extra ?? 10)
  const precoMods = useMemo(() => {
    return (
      Math.round(
        modulosOpts
          .filter((m) => moduloIds.includes(m.id))
          .reduce((acc, m) => acc + Number(m.preco_mensal || 0), 0) * 100,
      ) / 100
    )
  }, [modulosOpts, moduloIds])
  const usersN = parseInt(usuariosContratados, 10)
  const usersExtra = Number.isFinite(usersN) ? Math.max(0, usersN - inclusos) : 0
  const precoUsers = Math.round(usersExtra * extraUnit * 100) / 100
  const precoTotal = Math.round((precoMods + precoUsers) * 100) / 100

  function aplicarModulosDoPlano(pid: number | '') {
    if (pid === '') {
      setModuloIds([])
      return
    }
    const plano = planosOpts.find((p) => p.id === Number(pid))
    if (plano) setModuloIds(plano.modulos.map((m) => m.id))
  }

  useEffect(() => {
    if (pendingSnap == null) return
    if (!modulosOpts.length && !planosOpts.length) return
    if (pendingSnap.length && modulosOpts.length) {
      setModuloIds(modulosOpts.filter((m) => pendingSnap.includes(m.codigo)).map((m) => m.id))
    } else if (planoId !== '' && planosOpts.length) {
      aplicarModulosDoPlano(planoId)
    }
    setPendingSnap(null)
    // eslint-disable-next-line react-hooks/exhaustive-deps -- sync único após load da licença
  }, [pendingSnap, modulosOpts, planosOpts, planoId])

  useEffect(() => {
    if (!isEdit) return
    if (!id || Number.isNaN(clienteId)) {
      setInexistente({ detalhe: 'O identificador na URL é inválido.' })
      setLoading(false)
      return
    }
    let cancelled = false
    setLoading(true)
    setForbidden(false)
    setIndisponivel(false)
    setInexistente(null)
    saasClientes
      .get(clienteId)
      .then((c) => {
        if (cancelled) return
        setNome(c.nome)
        setSlug(c.slug)
        setSlugTouched(true)
        setStatus(c.status)
        setPlanoId(c.plano_id ?? '')
        setUsuariosContratados(
          c.max_usuarios != null
            ? String(c.max_usuarios)
            : String(c.usuarios_inclusos ?? 3),
        )
        setPrecoNegociado(
          c.preco_mensal_negociado != null ? String(c.preco_mensal_negociado) : '',
        )
        setPendingSnap(c.modulos_snapshot ?? [])
        setDataInicio(c.data_inicio.slice(0, 10))
        setDataRenovacao(c.data_renovacao ? c.data_renovacao.slice(0, 10) : '')
        setContatoNome(c.contato_nome ?? '')
        setContatoEmail(c.contato_email ?? '')
        setNotas(c.notas ?? '')
      })
      .catch((err) => {
        if (cancelled) return
        if (err instanceof ApiError && err.status === 403) {
          setForbidden(true)
          return
        }
        if (err instanceof ApiError && err.status === 404) {
          const detail =
            typeof err.body === 'object' && err.body && 'detail' in err.body
              ? String((err.body as { detail?: unknown }).detail ?? '')
              : ''
          if (detail.toLowerCase().includes('não disponível')) {
            setIndisponivel(true)
          } else {
            setInexistente({})
          }
          return
        }
        const m = interpretarFalhaCarregamento(err, 'Licença não encontrada.')
        toast.showWarning([m.titulo, m.detalhe].filter(Boolean).join(' '))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [clienteId, id, isEdit, toast])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      const urlAuto = urlInstanciaFromSlug(slug.trim().toLowerCase(), baseDomain) || null
      const usersParsed = parseInt(usuariosContratados, 10)
      const negociadoParsed =
        precoNegociado.trim() === '' ? null : Number(precoNegociado)
      const payload = {
        nome: nome.trim(),
        slug: slug.trim().toLowerCase(),
        status,
        plano_id: planoId === '' ? null : Number(planoId),
        modulo_ids: moduloIds,
        usuarios_contratados: Number.isFinite(usersParsed) ? usersParsed : null,
        preco_mensal_negociado:
          negociadoParsed != null && Number.isFinite(negociadoParsed) ? negociadoParsed : null,
        data_inicio: dataInicio,
        data_renovacao: dataRenovacao.trim() || null,
        instancia_url: urlAuto,
        contato_nome: contatoNome.trim() || null,
        contato_email: contatoEmail.trim() || null,
        notas: notas.trim() || null,
        ...(leadComercialId != null ? { lead_comercial_id: leadComercialId } : {}),
      }
      if (isEdit && !Number.isNaN(clienteId)) {
        await saasClientes.update(clienteId, payload)
        toast.showSuccess('Licença atualizada.')
        navigate(`/saas/licencas/${clienteId}`, { replace: true })
      } else {
        const created = await saasClientes.create(payload)
        toast.showSuccess('Licença cadastrada.')
        navigate(`/saas/licencas/${created.id}`, { replace: true })
      }
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível salvar a licença.'))
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <CadastroFormPageShell onVoltar={voltarAnterior}>
        <div className="h-48 animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-800/50" />
      </CadastroFormPageShell>
    )
  }

  if (indisponivel) {
    return (
      <SemPermissao
        title="Painel de licenças não disponível nesta instância."
        voltarPara="/"
        voltarLabel="Voltar para o Dashboard"
      />
    )
  }

  if (forbidden) {
    return (
      <SemPermissao
        title="Você não tem permissão para editar licenças SaaS."
        voltarPara="/saas/licencas"
        voltarLabel="Voltar para Licenças"
      />
    )
  }

  if (inexistente) {
    return (
      <CarregamentoFalhou
        className="mx-auto w-full min-w-0 max-w-5xl space-y-4 pb-10"
        titulo="Licença não encontrada."
        detalhe={inexistente.detalhe}
        onVoltar={voltarAnterior}
      />
    )
  }

  return (
    <CadastroFormPageShell onVoltar={voltarAnterior}>
      <Card title={isEdit ? 'Editar licença' : 'Nova licença SaaS'}>
        <form onSubmit={handleSubmit}>
          <div className="space-y-6">
            <FormSection title="Cliente">
              <Input
                label="Nome"
                value={nome}
                onChange={(e) => {
                  const v = e.target.value
                  setNome(v)
                  if (!isEdit && !slugTouched) setSlug(slugFromNome(v))
                }}
                required
              />
              <Input
                label="Nome da base (slug)"
                value={slug}
                onChange={(e) => {
                  setSlugTouched(true)
                  setSlug(e.target.value)
                }}
                required
                hint="Só o nome da base; o domínio é fixo (ex.: codewave → https://codewave.deskrudder.com.br/)"
              />
              <div className="space-y-1.5">
                <span className="text-sm font-medium text-slate-700 dark:text-slate-200">URL da instância</span>
                <p className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 font-mono text-sm text-slate-700 dark:border-slate-700 dark:bg-slate-900/50 dark:text-slate-200">
                  {urlInstanciaFromSlug(slug, baseDomain) || `https://{slug}.${baseDomain}/`}
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Gerada automaticamente a partir do nome da base. Não é editável.
                </p>
              </div>
              <Select
                label="Status"
                value={status}
                onChange={(v) => setStatus(String(v) as StatusClienteSaaS)}
                options={STATUS_CLIENTE_SAAS.map((s) => ({ value: s.value, label: s.label }))}
              />
              <Select
                label="Plano base"
                value={planoId}
                onChange={(v) => {
                  const next = v === '' ? '' : Number(v)
                  setPlanoId(next)
                  aplicarModulosDoPlano(next)
                  const plano = next === '' ? null : planosOpts.find((p) => p.id === next)
                  if (plano?.usuarios_inclusos != null) {
                    setUsuariosContratados(String(plano.usuarios_inclusos))
                  }
                }}
                includeEmpty
                emptyLabel="Sem plano"
                options={planosOpts
                  .filter((p) => p.ativo || p.id === planoId)
                  .map((p) => ({
                    value: p.id,
                    label: p.ativo ? p.nome : `${p.nome} (inativo)`,
                  }))}
              />
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Ao trocar o plano, os módulos do pacote são pré-selecionados. Você pode incluir
                módulos extras (ex.: Essencial + um módulo Enterprise).
              </p>
            </FormSection>
            <FormSection title="Módulos e usuários">
              <div className="space-y-2">
                <span className="text-sm font-medium text-slate-700 dark:text-slate-200">
                  Módulos contratados
                </span>
                <ul className="max-h-56 space-y-1 overflow-y-auto rounded-xl border border-slate-200 p-2 dark:border-slate-700">
                  {modulosOpts
                    .filter((m) => m.ativo || moduloIds.includes(m.id))
                    .map((m) => (
                      <li key={m.id}>
                        <label className="flex cursor-pointer items-center gap-2 rounded-lg px-2 py-1.5 text-sm hover:bg-slate-50 dark:hover:bg-slate-800/60">
                          <input
                            type="checkbox"
                            checked={moduloIds.includes(m.id)}
                            onChange={() => toggleModulo(m.id)}
                            className="rounded border-slate-300 text-sky-600 focus:ring-sky-400"
                          />
                          <span className="min-w-0 flex-1 text-slate-800 dark:text-slate-100">
                            {m.nome}
                            {!m.ativo ? (
                              <span className="ml-1 text-xs text-amber-600">(inativo)</span>
                            ) : null}
                          </span>
                          <span className="tabular-nums text-xs text-slate-500">
                            {formatPreco(Number(m.preco_mensal || 0))}
                          </span>
                        </label>
                      </li>
                    ))}
                </ul>
              </div>
              <Input
                label="Usuários contratados"
                type="number"
                min={0}
                value={usuariosContratados}
                onChange={(e) => setUsuariosContratados(e.target.value)}
                hint={`${inclusos} inclusos no plano; extras a ${formatPreco(extraUnit)}/mês cada.`}
              />
              <Input
                label="Valor mensal negociado (R$)"
                type="number"
                step="0.01"
                min={0}
                value={precoNegociado}
                onChange={(e) => setPrecoNegociado(e.target.value)}
                hint="Opcional. Se preenchido, vale na ficha comercial em vez da estimativa do catálogo."
              />
              <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900/40">
                <p className="font-medium text-slate-800 dark:text-slate-100">
                  {precoNegociado.trim() !== '' && Number.isFinite(Number(precoNegociado))
                    ? `Valor negociado: ${formatPreco(Number(precoNegociado))}`
                    : `Estimativa do catálogo: ${formatPreco(precoTotal)}`}
                </p>
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                  Catálogo: módulos {formatPreco(precoMods)}
                  {usersExtra > 0
                    ? ` + ${usersExtra} usuário(s) extra ${formatPreco(precoUsers)}`
                    : ''}
                  {precoNegociado.trim() !== '' ? ` (estimativa ${formatPreco(precoTotal)})` : ''}
                </p>
              </div>
            </FormSection>
            <FormSection title="Contato">
              <Input
                label="Nome do contato"
                value={contatoNome}
                onChange={(e) => setContatoNome(e.target.value)}
              />
              <Input
                label="E-mail do contato"
                type="email"
                value={contatoEmail}
                onChange={(e) => setContatoEmail(e.target.value)}
              />
            </FormSection>
            <FormSection title="Vigência">
              <Input
                label="Data de início"
                type="date"
                value={dataInicio}
                onChange={(e) => setDataInicio(e.target.value)}
                required
              />
              <Input
                label="Data de renovação"
                type="date"
                value={dataRenovacao}
                onChange={(e) => setDataRenovacao(e.target.value)}
              />
              <label className="block space-y-1.5">
                <span className="text-sm font-medium text-slate-700 dark:text-slate-200">Notas</span>
                <textarea
                  className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-sky-400 focus:outline-none focus:ring-2 focus:ring-sky-400/30 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
                  rows={3}
                  value={notas}
                  onChange={(e) => setNotas(e.target.value)}
                />
              </label>
            </FormSection>
          </div>
          <InlineCadastroFooter onCancel={voltarAnterior} saving={saving} />
        </form>
      </Card>
    </CadastroFormPageShell>
  )
}
