import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ApiError, saasModulos, saasPlanos, type SaasCatalogo } from '../../api/client'
import { Card } from '../../components/ui/Card'
import { Input } from '../../components/ui/Input'
import { Button } from '../../components/ui/Button'
import { useToast } from '../../components/ui/Toast'
import { useVoltarAnterior } from '../../hooks/useVoltarAnterior'
import { FormSection } from '../../components/ui/FormSection'
import { InlineCadastroFooter } from '../../components/ui/InlineCadastroPanel'
import { CadastroFormPageShell } from '../../components/ui/CadastroFormPageShell'
import { SemPermissao } from '../SemPermissao'
import { CarregamentoFalhou } from '../../components/ui/CarregamentoFalhou'
import { interpretarFalhaCarregamento, mensagemFalhaParaToast } from '../../api/errorMessage'

function formatPreco(v: number): string {
  return `R$ ${v.toLocaleString('pt-BR', { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`
}

export function SaasPlanoForm() {
  const { id } = useParams<{ id?: string }>()
  const navigate = useNavigate()
  const toast = useToast()
  const voltarAnterior = useVoltarAnterior('/saas/planos')
  const isEdit = id != null
  const planoId = id ? parseInt(id, 10) : NaN

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [forbidden, setForbidden] = useState(false)
  const [indisponivel, setIndisponivel] = useState(false)
  const [inexistente, setInexistente] = useState<{ detalhe?: string } | null>(null)

  const [codigo, setCodigo] = useState('')
  const [nome, setNome] = useState('')
  const [descricao, setDescricao] = useState('')
  const [ordem, setOrdem] = useState('0')
  const [usuariosInclusos, setUsuariosInclusos] = useState('3')
  const [precoUsuarioExtra, setPrecoUsuarioExtra] = useState('10')
  const [ativo, setAtivo] = useState(true)
  const [moduloIds, setModuloIds] = useState<number[]>([])
  const [modulos, setModulos] = useState<SaasCatalogo.Modulo[]>([])

  const precoModulos = useMemo(() => {
    return Math.round(
      modulos
        .filter((m) => moduloIds.includes(m.id))
        .reduce((acc, m) => acc + Number(m.preco_mensal || 0), 0) * 100,
    ) / 100
  }, [modulos, moduloIds])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    saasModulos
      .list()
      .then((mods) => {
        if (!cancelled) setModulos(mods)
      })
      .catch(() => {
        /* lista vazia */
      })

    if (!isEdit) {
      setLoading(false)
      return () => {
        cancelled = true
      }
    }
    if (!id || Number.isNaN(planoId)) {
      setInexistente({ detalhe: 'Identificador inválido.' })
      setLoading(false)
      return () => {
        cancelled = true
      }
    }
    saasPlanos
      .get(planoId)
      .then((p) => {
        if (cancelled) return
        setCodigo(p.codigo)
        setNome(p.nome)
        setDescricao(p.descricao ?? '')
        setOrdem(String(p.ordem ?? 0))
        setUsuariosInclusos(String(p.usuarios_inclusos ?? 3))
        setPrecoUsuarioExtra(
          p.preco_usuario_extra != null ? String(p.preco_usuario_extra) : '10',
        )
        setAtivo(p.ativo)
        setModuloIds(p.modulos.map((m) => m.id))
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
          if (detail.toLowerCase().includes('não disponível')) setIndisponivel(true)
          else setInexistente({})
          return
        }
        const m = interpretarFalhaCarregamento(err, 'Plano não encontrado.')
        toast.showWarning([m.titulo, m.detalhe].filter(Boolean).join(' '))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [id, isEdit, planoId, toast])

  function toggleModulo(mid: number) {
    setModuloIds((prev) => (prev.includes(mid) ? prev.filter((x) => x !== mid) : [...prev, mid]))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      const ordemN = parseInt(ordem, 10)
      const inclusosN = parseInt(usuariosInclusos, 10)
      const extraN = Number(precoUsuarioExtra)
      const payload = {
        nome: nome.trim(),
        descricao: descricao.trim() || null,
        ordem: Number.isFinite(ordemN) ? ordemN : 0,
        usuarios_inclusos: Number.isFinite(inclusosN) ? inclusosN : 3,
        preco_usuario_extra: Number.isFinite(extraN) ? extraN : 10,
        modulo_ids: moduloIds,
      }
      if (isEdit && !Number.isNaN(planoId)) {
        await saasPlanos.update(planoId, payload)
        toast.showSuccess('Plano atualizado.')
        navigate(`/saas/planos/${planoId}`, { replace: true })
      } else {
        const created = await saasPlanos.create({
          codigo: codigo.trim().toLowerCase(),
          ...payload,
        })
        toast.showSuccess('Plano criado.')
        navigate(`/saas/planos/${created.id}`, { replace: true })
      }
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível salvar o plano.'))
    } finally {
      setSaving(false)
    }
  }

  async function toggleAtivo() {
    if (!isEdit || Number.isNaN(planoId)) return
    setSaving(true)
    try {
      if (ativo) await saasPlanos.desativar(planoId)
      else await saasPlanos.ativar(planoId)
      setAtivo(!ativo)
      toast.showSuccess(ativo ? 'Plano desativado.' : 'Plano ativado.')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível alterar o estado.'))
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
        title="Painel SaaS não disponível nesta instância."
        voltarPara="/"
        voltarLabel="Voltar para o Dashboard"
      />
    )
  }

  if (forbidden) {
    return (
      <SemPermissao
        title="Você não tem permissão para editar planos."
        voltarPara="/saas/planos"
        voltarLabel="Voltar para Planos"
      />
    )
  }

  if (inexistente) {
    return (
      <CarregamentoFalhou
        className="mx-auto w-full min-w-0 max-w-5xl space-y-4 pb-10"
        titulo="Plano não encontrado."
        detalhe={inexistente.detalhe}
        onVoltar={voltarAnterior}
      />
    )
  }

  return (
    <CadastroFormPageShell onVoltar={voltarAnterior}>
      <Card title={isEdit ? 'Editar plano' : 'Novo plano'}>
        <form onSubmit={handleSubmit}>
          <div className="space-y-6">
            <FormSection title="Identificação">
              <Input
                label="Código"
                value={codigo}
                onChange={(e) => setCodigo(e.target.value)}
                required
                disabled={isEdit}
                hint="Identificador estável (ex.: profissional). Não muda após criar."
              />
              <Input label="Nome" value={nome} onChange={(e) => setNome(e.target.value)} required />
              <Input
                label="Ordem"
                type="number"
                value={ordem}
                onChange={(e) => setOrdem(e.target.value)}
                hint="Menor aparece primeiro na lista"
              />
              <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900/40">
                <p className="font-medium text-slate-800 dark:text-slate-100">
                  Preço base (soma dos módulos): {formatPreco(precoModulos)}
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  Calculado automaticamente. Altere o preço em Módulos.
                </p>
              </div>
              <Input
                label="Usuários inclusos"
                type="number"
                min={0}
                value={usuariosInclusos}
                onChange={(e) => setUsuariosInclusos(e.target.value)}
                hint="Inclusos no preço dos módulos (padrão 3)"
              />
              <Input
                label="Preço por usuário extra (R$)"
                type="number"
                step="0.01"
                min={0}
                value={precoUsuarioExtra}
                onChange={(e) => setPrecoUsuarioExtra(e.target.value)}
                hint="Cobrado por usuário acima dos inclusos"
              />
              <label className="block space-y-1.5">
                <span className="text-sm font-medium text-slate-700 dark:text-slate-200">Descrição</span>
                <textarea
                  className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-sky-400 focus:outline-none focus:ring-2 focus:ring-sky-400/30 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
                  rows={2}
                  value={descricao}
                  onChange={(e) => setDescricao(e.target.value)}
                />
              </label>
              {isEdit ? (
                <div className="flex items-center gap-3">
                  <span
                    className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${
                      ativo
                        ? 'bg-emerald-50 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300'
                        : 'bg-slate-100 text-slate-600'
                    }`}
                  >
                    {ativo ? 'Ativo' : 'Inativo'}
                  </span>
                  <Button type="button" variant="secondary" disabled={saving} onClick={() => void toggleAtivo()}>
                    {ativo ? 'Desativar' : 'Ativar'}
                  </Button>
                </div>
              ) : null}
            </FormSection>
            <FormSection title="Módulos incluídos">
              <p className="text-sm text-slate-500 dark:text-slate-400">
                O preço do plano é a soma destes módulos. Na licença dá para ligar módulos extras (ex.: Essencial + ponto).
              </p>
              {modulos.length === 0 ? (
                <p className="text-sm text-amber-700 dark:text-amber-300">
                  Nenhum módulo. Crie em{' '}
                  <button
                    type="button"
                    className="font-medium underline"
                    onClick={() => navigate('/saas/modulos')}
                  >
                    Módulos
                  </button>
                  .
                </p>
              ) : (
                <ul className="space-y-2">
                  {modulos.map((m) => (
                    <li key={m.id}>
                      <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-slate-200 px-3 py-2 dark:border-slate-700">
                        <input
                          type="checkbox"
                          className="mt-1"
                          checked={moduloIds.includes(m.id)}
                          onChange={() => toggleModulo(m.id)}
                          disabled={!m.ativo && !moduloIds.includes(m.id)}
                        />
                        <span className="min-w-0 flex-1">
                          <span className="flex flex-wrap items-baseline justify-between gap-2">
                            <span className="text-sm font-medium text-slate-800 dark:text-slate-100">
                              {m.nome}
                              {!m.ativo ? (
                                <span className="ml-2 text-xs font-normal text-slate-400">(inativo)</span>
                              ) : null}
                            </span>
                            <span className="text-xs tabular-nums text-slate-600 dark:text-slate-300">
                              {m.preco_mensal != null ? formatPreco(Number(m.preco_mensal)) : '—'}
                            </span>
                          </span>
                          <span className="font-mono text-xs text-slate-500">{m.codigo}</span>
                        </span>
                      </label>
                    </li>
                  ))}
                </ul>
              )}
            </FormSection>
          </div>
          <InlineCadastroFooter onCancel={voltarAnterior} saving={saving} />
        </form>
      </Card>
    </CadastroFormPageShell>
  )
}
