import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ApiError, respostasProntas, setores, type Setores } from '../api/client'
import { coletarTodasPaginas } from '../api/collectPages'
import { Card } from '../components/ui/Card'
import { Input } from '../components/ui/Input'
import { Switch } from '../components/ui/Switch'
import { useToast } from '../components/ui/Toast'
import { useVoltarAnterior } from '../hooks/useVoltarAnterior'
import { FormSection } from '../components/ui/FormSection'
import { InlineCadastroFooter } from '../components/ui/InlineCadastroPanel'
import { CadastroFormPageShell } from '../components/ui/CadastroFormPageShell'
import { SemPermissao } from './SemPermissao'
import { CarregamentoFalhou } from '../components/ui/CarregamentoFalhou'
import { interpretarFalhaCarregamento, mensagemFalhaParaToast } from '../api/errorMessage'

export function RespostaProntaForm() {
  const { id } = useParams<{ id?: string }>()
  const navigate = useNavigate()
  const toast = useToast()
  const voltarAnterior = useVoltarAnterior('/respostas-prontas')

  const respostaId = id ? parseInt(id, 10) : NaN
  const isEdit = id != null

  const [loading, setLoading] = useState(isEdit)
  const [saving, setSaving] = useState(false)
  const [forbidden, setForbidden] = useState(false)
  const [inexistente, setInexistente] = useState<{ detalhe?: string } | null>(null)
  const [setoresOpts, setSetoresOpts] = useState<Setores.Setor[]>([])
  const [titulo, setTitulo] = useState('')
  const [corpo, setCorpo] = useState('')
  const [setorId, setSetorId] = useState('')
  const [ordemVal, setOrdemVal] = useState(0)
  const [ativo, setAtivo] = useState(true)

  useEffect(() => {
    coletarTodasPaginas<Setores.Setor>((o, l) =>
      setores.list({ incluir_inativos: true, offset: o, limit: l }),
    )
      .then(setSetoresOpts)
      .catch(() => setSetoresOpts([]))
  }, [])

  useEffect(() => {
    if (isEdit) return
    respostasProntas.list({ limit: 1, offset: 0 }).then(({ total }) => setOrdemVal(total))
  }, [isEdit])

  useEffect(() => {
    if (!isEdit) return
    if (!id || Number.isNaN(respostaId)) {
      setInexistente({ detalhe: 'O identificador na URL é inválido.' })
      setLoading(false)
      return
    }
    let cancelled = false
    setLoading(true)
    setForbidden(false)
    setInexistente(null)
    respostasProntas
      .get(respostaId)
      .then((item) => {
        if (cancelled) return
        setTitulo(item.titulo)
        setCorpo(item.corpo)
        setSetorId(item.setor_id != null ? String(item.setor_id) : '')
        setOrdemVal(item.ordem)
        setAtivo(item.ativo)
      })
      .catch((err) => {
        if (cancelled) return
        if (err instanceof ApiError && err.status === 403) {
          setForbidden(true)
          return
        }
        if (err instanceof ApiError && err.status === 404) {
          setInexistente({})
          return
        }
        const m = interpretarFalhaCarregamento(err, 'Resposta pronta não encontrada.')
        toast.showWarning([m.titulo, m.detalhe].filter(Boolean).join(' '))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [id, isEdit, respostaId, toast])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!titulo.trim() || !corpo.trim()) {
      toast.showError('Informe título e corpo.')
      return
    }
    setSaving(true)
    const payload = {
      titulo: titulo.trim(),
      corpo,
      setor_id: setorId ? Number(setorId) : null,
      ordem: ordemVal,
      ativo,
    }
    try {
      if (isEdit && !Number.isNaN(respostaId)) {
        await respostasProntas.update(respostaId, payload)
        toast.showSuccess('Resposta pronta atualizada.')
        navigate(`/respostas-prontas/${respostaId}`, { replace: true })
      } else {
        const created = await respostasProntas.create(payload)
        toast.showSuccess('Resposta pronta cadastrada.')
        navigate(`/respostas-prontas/${created.id}`, { replace: true })
      }
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível salvar.'))
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <CadastroFormPageShell onVoltar={voltarAnterior}>
        <div className="h-72 animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-800/50" />
      </CadastroFormPageShell>
    )
  }

  if (forbidden) {
    return (
      <SemPermissao
        title="Você não tem permissão para gerenciar respostas prontas."
        voltarPara="/respostas-prontas"
        voltarLabel="Voltar para Respostas prontas"
      />
    )
  }

  if (inexistente) {
    return (
      <CarregamentoFalhou
        className="mx-auto max-w-5xl space-y-4 pb-10"
        titulo="Resposta pronta não encontrada."
        detalhe={inexistente.detalhe}
        onVoltar={voltarAnterior}
      />
    )
  }

  return (
    <CadastroFormPageShell onVoltar={voltarAnterior}>
      <Card title={isEdit ? 'Editar resposta pronta' : 'Nova resposta pronta'}>
        <form onSubmit={handleSubmit}>
          <div className="space-y-6">
            <FormSection title="Conteúdo">
              <Input label="Título" value={titulo} onChange={(e) => setTitulo(e.target.value)} required />
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                Corpo
                <textarea
                  value={corpo}
                  onChange={(e) => setCorpo(e.target.value)}
                  rows={8}
                  required
                  className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
                />
              </label>
            </FormSection>
            <FormSection title="Escopo">
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                Setor (vazio = global)
                <select
                  value={setorId}
                  onChange={(e) => setSetorId(e.target.value)}
                  className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
                >
                  <option value="">Global — todos os setores</option>
                  {setoresOpts.map((s) => (
                    <option key={s.id} value={String(s.id)}>
                      {s.nome}
                    </option>
                  ))}
                </select>
              </label>
              <Input
                label="Ordem"
                type="number"
                value={String(ordemVal)}
                onChange={(e) => setOrdemVal(Number(e.target.value) || 0)}
              />
              <Switch
                bare
                checked={ativo}
                onCheckedChange={setAtivo}
                label="Resposta ativa"
                showStatusPill
                statusOnText="Ativo"
                statusOffText="Inativo"
              />
            </FormSection>
          </div>
          <InlineCadastroFooter onCancel={voltarAnterior} saving={saving} />
        </form>
      </Card>
    </CadastroFormPageShell>
  )
}
