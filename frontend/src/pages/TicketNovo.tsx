import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { tickets, empresas, setores, type Empresas, type Setores } from '../api/client'
import { coletarTodasPaginas } from '../api/collectPages'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { SelectComPesquisa } from '../components/ui/SelectComPesquisa'
import { Select } from '../components/ui/Select'
import { useToast } from '../components/ui/Toast'
import { useAuth } from '../contexts/AuthContext'
import { useVoltarAnterior } from '../hooks/useVoltarAnterior'
import { FormSection } from '../components/ui/FormSection'

export function TicketNovo() {
  const { isAdmin, user } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()
  const voltarAnterior = useVoltarAnterior('/tickets')

  const [empresasList, setEmpresasList] = useState<Empresas.EmpresaListaItem[]>([])
  const [setoresList, setSetoresList] = useState<Setores.Setor[]>([])
  const [empresaId, setEmpresaId] = useState<number | ''>('')
  const [setorId, setSetorId] = useState<number | ''>('')
  const [assunto, setAssunto] = useState('')
  const [descricao, setDescricao] = useState('')
  const [loading, setLoading] = useState(false)

  const setorIdsPermitidos = useMemo(() => {
    if (isAdmin) return null
    return new Set(user?.setor_ids ?? [])
  }, [isAdmin, user?.setor_ids])

  const setoresFiltrados = useMemo(() => {
    const ativos = setoresList.filter((s) => s.ativo)
    if (!setorIdsPermitidos) return ativos.sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'))
    return ativos
      .filter((s) => setorIdsPermitidos.has(s.id))
      .sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'))
  }, [setoresList, setorIdsPermitidos])

  const empresaItems = useMemo(
    () =>
      empresasList.map((e) => ({
        id: e.id,
        label: e.nome,
        createdAt: 'created_at' in e ? e.created_at : undefined,
      })),
    [empresasList],
  )

  useEffect(() => {
    coletarTodasPaginas<Empresas.EmpresaListaItem>((o, l) => empresas.list({ offset: o, limit: l })).then(
      setEmpresasList,
    )
    coletarTodasPaginas<Setores.Setor>((o, l) =>
      setores.list({ incluir_inativos: true, offset: o, limit: l }),
    ).then(setSetoresList)
  }, [])

  useEffect(() => {
    if (setorId === '') return
    if (!setoresFiltrados.some((s) => s.id === setorId)) {
      setSetorId('')
    }
  }, [setoresFiltrados, setorId])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!empresaId || !setorId || !assunto.trim() || !descricao.trim()) {
      toast.showWarning('Preencha empresa, setor, assunto e o relato do problema.')
      return
    }
    if (!isAdmin && !setorIdsPermitidos?.has(Number(setorId))) {
      toast.showWarning('Selecione um setor ao qual você tenha acesso.')
      return
    }
    setLoading(true)
    try {
      const created = await tickets.create({
        empresa_id: Number(empresaId),
        setor_id: Number(setorId),
        assunto: assunto.trim(),
        descricao: descricao.trim(),
      })
      toast.showSuccess('Ticket criado.')
      navigate(`/tickets/${created.id}`)
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Erro ao criar ticket'
      toast.showError(msg)
    } finally {
      setLoading(false)
    }
  }

  const semSetorPermitido = !isAdmin && setoresFiltrados.length === 0

  return (
    <div className="mx-auto max-w-3xl space-y-6 pb-10">
      <nav aria-label="breadcrumb" className="flex flex-wrap items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
        <button
          type="button"
          onClick={voltarAnterior}
          className="font-medium text-slate-600 hover:text-slate-900 dark:text-slate-300 dark:hover:text-slate-100"
        >
          ← Voltar
        </button>
        <span aria-hidden className="text-slate-300 dark:text-slate-600">
          /
        </span>
        <span className="font-semibold text-slate-800 dark:text-slate-100">Novo</span>
      </nav>

      <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100">Novo ticket</h1>

      {semSetorPermitido && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-800/60 dark:bg-amber-950/40 dark:text-amber-100">
          Você não está vinculado a nenhum setor ativo. Peça a um administrador para associar setores ao seu usuário
          antes de abrir tickets.
        </div>
      )}

      <Card title="Abrir ticket">
        <p className="mb-4 text-sm text-slate-600 dark:text-slate-400">
          O ticket entra na <strong>fila do setor</strong> (sem responsável). Qualquer atendente do setor pode abrir o chamado e usar{' '}
          <strong>Atribuir a mim</strong> para assumir o atendimento.
        </p>
        <form onSubmit={handleSubmit}>
          <div className="space-y-6">
            <FormSection title="Identificação">
              <SelectComPesquisa
                id="ticket-empresa"
                label="Empresa *"
                value={empresaId}
                onChange={(id) => setEmpresaId(id)}
                items={empresaItems}
                placeholder="Buscar empresa..."
                required
                disabled={semSetorPermitido}
                recentCount={10}
              />

              <div>
                <Select
                  id="ticket-setor"
                  label="Setor *"
                  value={setorId}
                  onChange={(v) => setSetorId(v === '' ? '' : Number(v))}
                  options={setoresFiltrados.map((s) => ({ value: s.id, label: s.nome }))}
                  includeEmpty
                  emptyLabel="Selecione"
                  placeholder="Selecione"
                  disabled={semSetorPermitido}
                />
                {!isAdmin && setoresFiltrados.length > 0 && (
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">Somente setores aos quais você está vinculado.</p>
                )}
              </div>
            </FormSection>

            <FormSection title="Solicitação">
              <Input
                label="Assunto (resumo) *"
                value={assunto}
                onChange={(e) => setAssunto(e.target.value)}
                required
                disabled={semSetorPermitido}
              />
              <div>
                <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">Relato do problema *</label>
                <p className="mb-2 text-xs text-slate-500 dark:text-slate-400">
                  Este texto entra como primeira mensagem do ticket (solicitação inicial).
                </p>
                <textarea
                  value={descricao}
                  onChange={(e) => setDescricao(e.target.value)}
                  spellCheck={false}
                  rows={5}
                  required
                  disabled={semSetorPermitido}
                  className="w-full rounded-xl border-0 bg-white px-3 py-2 text-sm shadow-sm ring-1 ring-slate-200/90 focus:outline-none focus:ring-2 focus:ring-slate-400/35 dark:bg-slate-900 dark:text-slate-100 dark:ring-slate-700"
                />
              </div>
            </FormSection>
          </div>

          <div className="sticky bottom-0 -mx-6 mt-6 border-t border-slate-200 bg-white px-6 py-4 dark:border-slate-700 dark:bg-slate-900">
            <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
              <Button type="button" variant="secondary" onClick={voltarAnterior} className="w-full sm:w-auto">
                Cancelar
              </Button>
              <Button type="submit" loading={loading} disabled={semSetorPermitido} className="w-full sm:w-auto">
                Criar ticket
              </Button>
            </div>
          </div>
        </form>
      </Card>
    </div>
  )
}
