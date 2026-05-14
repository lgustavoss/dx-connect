import { useState, useEffect, useMemo, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError, tickets, empresas, setores, type Empresas, type Setores } from '../api/client'
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
import { SemPermissao } from './SemPermissao'
import { mensagemFalhaParaToast } from '../api/errorMessage'

const MAX_ANEXO_BYTES = 25 * 1024 * 1024
const MAX_ANEXOS_COUNT = 10

export function TicketNovo() {
  const { isAdmin } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()
  const voltarAnterior = useVoltarAnterior('/tickets')
  const [forbidden, setForbidden] = useState(false)

  const [empresasList, setEmpresasList] = useState<Empresas.EmpresaListaItem[]>([])
  const [setoresList, setSetoresList] = useState<Setores.Setor[]>([])
  const [empresaId, setEmpresaId] = useState<number | ''>('')
  const [setorId, setSetorId] = useState<number | ''>('')
  const [assunto, setAssunto] = useState('')
  const [descricao, setDescricao] = useState('')
  const [anexosSelecionados, setAnexosSelecionados] = useState<File[]>([])
  const [loading, setLoading] = useState(false)
  const anexosInputRef = useRef<HTMLInputElement>(null)

  /** Setores já vêm filtrados pelo backend (#38); não restringir por `user.setor_ids` no cliente (evita perder homônimos). */
  const setoresFiltrados = useMemo(() => {
    const ativos = setoresList.filter((s) => s.ativo)
    return [...ativos].sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'))
  }, [setoresList])

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
    setForbidden(false)
    coletarTodasPaginas<Empresas.EmpresaListaItem>((o, l) => empresas.list({ offset: o, limit: l }))
      .then(setEmpresasList)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 403) {
          toast.showWarning('Você não tem permissão para listar empresas.')
          setEmpresasList([])
          setForbidden(true)
          return
        }
        toast.showWarning(mensagemFalhaParaToast(err, 'Não encontramos empresas para abrir o chamado.'))
        setEmpresasList([])
      })
    coletarTodasPaginas<Setores.Setor>((o, l) => setores.list({ incluir_inativos: true, offset: o, limit: l }))
      .then(setSetoresList)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 403) {
          toast.showWarning('Você não tem permissão para listar setores.')
          setSetoresList([])
          setForbidden(true)
          return
        }
        toast.showWarning(mensagemFalhaParaToast(err))
        setSetoresList([])
      })
  }, [])

  useEffect(() => {
    if (setorId === '') return
    if (!setoresFiltrados.some((s) => s.id === setorId)) {
      setSetorId('')
    }
  }, [setoresFiltrados, setorId])

  function onSelecionarAnexos(ev: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(ev.target.files ?? [])
    ev.target.value = ''
    if (files.length === 0) return

    const ok: File[] = []
    for (const f of files) {
      if (f.size <= 0) continue
      if (f.size > MAX_ANEXO_BYTES) {
        toast.showWarning(`O arquivo \"${f.name}\" excede 25 MB e foi ignorado.`)
        continue
      }
      ok.push(f)
    }
    if (ok.length === 0) return

    setAnexosSelecionados((prev) => {
      const next = [...prev, ...ok]
      if (next.length > MAX_ANEXOS_COUNT) {
        toast.showWarning(`Máximo de ${MAX_ANEXOS_COUNT} anexos por abertura. Alguns arquivos foram ignorados.`)
        return next.slice(0, MAX_ANEXOS_COUNT)
      }
      return next
    })
  }

  function removerAnexo(idx: number) {
    setAnexosSelecionados((prev) => prev.filter((_, i) => i !== idx))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!empresaId || !setorId || !assunto.trim() || !descricao.trim()) {
      toast.showWarning('Preencha empresa, setor, assunto e o relato do problema.')
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
      if (anexosSelecionados.length > 0) {
        let ok = 0
        for (const f of anexosSelecionados) {
          try {
            await tickets.uploadAnexo(created.id, f)
            ok += 1
          } catch (err) {
            toast.showWarning(mensagemFalhaParaToast(err, `Falha ao enviar anexo \"${f.name}\".`))
          }
        }
        toast.showSuccess(ok > 0 ? `Ticket criado com ${ok} anexo(s).` : 'Ticket criado.')
      } else {
        toast.showSuccess('Ticket criado.')
      }
      navigate(`/tickets/${created.id}`)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível localizar os dados para criar o ticket.'))
    } finally {
      setLoading(false)
    }
  }

  const semSetorPermitido = !isAdmin && setoresFiltrados.length === 0
  const semEmpresasNoEscopo = !isAdmin && !semSetorPermitido && empresasList.length === 0

  if (forbidden) {
    return (
      <div className="mx-auto max-w-3xl space-y-6 pb-10">
        <SemPermissao
          title="Você não tem permissão para abrir tickets."
          detail="Seu usuário não conseguiu carregar setores/empresas necessários para criar um chamado. Peça ao administrador para ajustar seu perfil e vínculos de setor."
          voltarPara="/tickets"
          voltarLabel="Voltar para Tickets"
        />
      </div>
    )
  }

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

      {semEmpresasNoEscopo && (
        <div className="rounded-lg border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-950 dark:border-sky-800/60 dark:bg-sky-950/40 dark:text-sky-100">
          Ainda não há empresas listáveis no seu escopo: a API só mostra clientes de redes que já tiveram ticket nos setores
          que você atende. Peça a um administrador para registrar o primeiro chamado dessa rede (ou ajustar cadastro), ou
          use uma empresa que já apareça na lista de tickets.
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
                disabled={semSetorPermitido || semEmpresasNoEscopo}
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
                  disabled={semSetorPermitido || semEmpresasNoEscopo}
                />
                {!isAdmin && setoresFiltrados.length > 0 && (
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                    Lista conforme os setores que você atende no sistema (inclui homônimos no cadastro).
                  </p>
                )}
              </div>
            </FormSection>

            <FormSection title="Solicitação">
              <Input
                label="Assunto (resumo) *"
                value={assunto}
                onChange={(e) => setAssunto(e.target.value)}
                required
                disabled={semSetorPermitido || semEmpresasNoEscopo}
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
                  disabled={semSetorPermitido || semEmpresasNoEscopo}
                  className="w-full rounded-xl border-0 bg-white px-3 py-2 text-sm shadow-sm ring-1 ring-slate-200/90 focus:outline-none focus:ring-2 focus:ring-slate-400/35 dark:bg-slate-900 dark:text-slate-100 dark:ring-slate-700"
                />
              </div>

              <div className="mt-4">
                <label
                  htmlFor="ticket-novo-anexos"
                  className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300"
                >
                  Anexos (opcional)
                </label>
                <div className="flex flex-wrap items-center gap-3">
                  <input
                    ref={anexosInputRef}
                    id="ticket-novo-anexos"
                    type="file"
                    multiple
                    className="sr-only"
                    onChange={onSelecionarAnexos}
                    disabled={semSetorPermitido || semEmpresasNoEscopo || loading}
                    aria-label="Selecionar arquivos para anexar ao ticket"
                  />
                  <Button
                    type="button"
                    variant="secondary"
                    disabled={semSetorPermitido || semEmpresasNoEscopo || loading}
                    onClick={() => anexosInputRef.current?.click()}
                    className="inline-flex items-center gap-2"
                  >
                    <svg className="size-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"
                      />
                    </svg>
                    Adicionar arquivos
                  </Button>
                  {anexosSelecionados.length > 0 ? (
                    <span className="text-xs font-medium text-slate-600 dark:text-slate-300">
                      {anexosSelecionados.length} arquivo(s) na fila
                    </span>
                  ) : (
                    <span className="text-xs text-slate-500 dark:text-slate-400">Nenhum arquivo selecionado</span>
                  )}
                </div>
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                  Até {MAX_ANEXOS_COUNT} arquivo(s), no máximo 25 MB cada. Alguns tipos podem ser bloqueados por segurança.
                </p>

                {anexosSelecionados.length > 0 && (
                  <div className="mt-2 rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm text-slate-800 dark:border-slate-800 dark:bg-slate-950/40 dark:text-slate-100">
                    <div className="mb-2 font-medium">Arquivos selecionados</div>
                    <ul className="space-y-2">
                      {anexosSelecionados.map((f, idx) => (
                        <li key={`${f.name}-${f.size}-${idx}`} className="flex items-center justify-between gap-3">
                          <span className="min-w-0 truncate">
                            {f.name}{' '}
                            <span className="text-xs text-slate-500 dark:text-slate-400">
                              ({Math.ceil(f.size / 1024)} KB)
                            </span>
                          </span>
                          <button
                            type="button"
                            onClick={() => removerAnexo(idx)}
                            className="shrink-0 rounded-md px-2 py-1 text-xs font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-900 dark:hover:text-slate-100"
                          >
                            Remover
                          </button>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </FormSection>
          </div>

          <div className="sticky bottom-0 -mx-6 mt-6 border-t border-slate-200 bg-white px-6 py-4 dark:border-slate-700 dark:bg-slate-900">
            <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
              <Button type="button" variant="secondary" onClick={voltarAnterior} className="w-full sm:w-auto">
                Cancelar
              </Button>
              <Button
                type="submit"
                loading={loading}
                disabled={semSetorPermitido || semEmpresasNoEscopo}
                className="w-full sm:w-auto"
              >
                Criar ticket
              </Button>
            </div>
          </div>
        </form>
      </Card>
    </div>
  )
}
