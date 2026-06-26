import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ApiError, statusTicket } from '../api/client'
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

export function StatusTicketForm() {
  const { id } = useParams<{ id?: string }>()
  const navigate = useNavigate()
  const toast = useToast()
  const voltarAnterior = useVoltarAnterior('/status-ticket')

  const statusId = id ? parseInt(id, 10) : NaN
  const isEdit = id != null

  const [loading, setLoading] = useState(isEdit)
  const [saving, setSaving] = useState(false)
  const [forbidden, setForbidden] = useState(false)
  const [inexistente, setInexistente] = useState<{ detalhe?: string } | null>(null)
  const [nome, setNome] = useState('')
  const [slug, setSlug] = useState('')
  const [ordem, setOrdem] = useState(0)
  const [ativo, setAtivo] = useState(true)
  const [pausaSla, setPausaSla] = useState(false)

  useEffect(() => {
    if (isEdit) return
    statusTicket.list({ limit: 1, offset: 0 }).then(({ total }) => setOrdem(total))
  }, [isEdit])

  useEffect(() => {
    if (!isEdit) return
    if (!id || Number.isNaN(statusId)) {
      setInexistente({ detalhe: 'O identificador na URL é inválido.' })
      setLoading(false)
      return
    }
    let cancelled = false
    setLoading(true)
    setForbidden(false)
    setInexistente(null)
    statusTicket
      .get(statusId)
      .then((s) => {
        if (cancelled) return
        setNome(s.nome)
        setSlug(s.slug)
        setOrdem(s.ordem)
        setAtivo(s.ativo)
        setPausaSla(s.pausa_sla)
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
        const m = interpretarFalhaCarregamento(err, 'Status não encontrado.')
        toast.showWarning([m.titulo, m.detalhe].filter(Boolean).join(' '))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [id, isEdit, statusId, toast])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      if (isEdit && !Number.isNaN(statusId)) {
        await statusTicket.update(statusId, {
          nome: nome.trim(),
          slug: slug.trim(),
          ordem,
          ativo,
          pausa_sla: pausaSla,
        })
        toast.showSuccess('Status atualizado.')
        navigate(`/status-ticket/${statusId}`, { replace: true })
      } else {
        const created = await statusTicket.create({
          nome: nome.trim(),
          slug: slug.trim(),
          ordem,
          ativo,
          pausa_sla: pausaSla,
        })
        toast.showSuccess('Status cadastrado.')
        navigate(`/status-ticket/${created.id}`, { replace: true })
      }
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível salvar o status de ticket.'))
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <CadastroFormPageShell onVoltar={voltarAnterior}>
        <div className="h-64 animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-800/50" />
      </CadastroFormPageShell>
    )
  }

  if (forbidden) {
    return (
      <SemPermissao
        title="Você não tem permissão para editar status de ticket."
        voltarPara="/status-ticket"
        voltarLabel="Voltar para Status de ticket"
      />
    )
  }

  if (inexistente) {
    return (
      <CarregamentoFalhou
        className="mx-auto max-w-5xl space-y-4 pb-10"
        titulo="Status não encontrado."
        detalhe={inexistente.detalhe}
        onVoltar={voltarAnterior}
      />
    )
  }

  return (
    <CadastroFormPageShell onVoltar={voltarAnterior}>
      <Card title={isEdit ? 'Editar status' : 'Novo status'}>
        <form onSubmit={handleSubmit}>
          <div className="space-y-6">
            <FormSection title="Dados do status">
              <Input label="Nome" value={nome} onChange={(e) => setNome(e.target.value)} required />
              <Input
                label="Slug"
                value={slug}
                onChange={(e) => setSlug(e.target.value)}
                placeholder="ex: aguardando_atendimento"
                required
              />
              <Input label="Ordem" type="number" value={ordem} onChange={(e) => setOrdem(Number(e.target.value))} />
            </FormSection>
            <FormSection title="Situação no sistema">
              <Switch
                bare
                checked={ativo}
                onCheckedChange={setAtivo}
                label="Status ativo"
                showStatusPill
                statusOnText="Ativo"
                statusOffText="Inativo"
              />
              <Switch
                bare
                checked={pausaSla}
                onCheckedChange={setPausaSla}
                label="Pausa contagem do SLA"
                showStatusPill
                statusOnText="Pausa SLA"
                statusOffText="Conta SLA"
              />
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Enquanto o ticket estiver neste status, o relógio de SLA não avança (ex.: aguardando cliente).
              </p>
            </FormSection>
          </div>
          <InlineCadastroFooter onCancel={voltarAnterior} saving={saving} />
        </form>
      </Card>
    </CadastroFormPageShell>
  )
}
