import { useState, useEffect, useCallback } from 'react'
import { CabecalhoOrdenavel } from '../components/ui/CabecalhoOrdenavel'
import { useOrdenacaoLista } from '../hooks/useOrdenacaoLista'
import { ApiError, atendentes, setores, type Atendentes, type Setores } from '../api/client'
import { coletarTodasPaginas } from '../api/collectPages'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { IconEye, IconEyeOff } from '../components/ui/IconEye'
import { IconPencil } from '../components/ui/IconPencil'
import { FiltroInativos } from '../components/ui/FiltroInativos'
import { BarraBuscaPaginacao, PAGE_SIZE_PADRAO } from '../components/ui/BarraBuscaPaginacao'
import { Switch } from '../components/ui/Switch'
import { CheckboxField } from '../components/ui/CheckboxField'
import { Select } from '../components/ui/Select'
import { useToast } from '../components/ui/Toast'
import { FormSection } from '../components/ui/FormSection'
import { SemPermissao } from './SemPermissao'
import { mensagemFalhaParaToast } from '../api/errorMessage'

type ColunaAtendente = 'nome' | 'email' | 'role'

const roleLabel: Record<string, string> = { admin: 'Administrador', atendente: 'Atendente' }

export function Atendentes() {
  const toast = useToast()
  const { ordenarPor, ordem, aoOrdenarColuna, sortParams } = useOrdenacaoLista<ColunaAtendente>()
  const [list, setList] = useState<Atendentes.Atendente[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [busca, setBusca] = useState('')
  const [debouncedBusca, setDebouncedBusca] = useState('')
  const [setoresList, setSetoresList] = useState<Setores.Setor[]>([])
  const [loading, setLoading] = useState(true)
  const [incluirInativos, setIncluirInativos] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [email, setEmail] = useState('')
  const [nome, setNome] = useState('')
  const [senha, setSenha] = useState('')
  const [mostrarSenha, setMostrarSenha] = useState(false)
  const [role, setRole] = useState<'admin' | 'atendente'>('atendente')
  const [ativo, setAtivo] = useState(true)
  const [setorIds, setSetorIds] = useState<number[]>([])
  const [saving, setSaving] = useState(false)
  const [forbidden, setForbidden] = useState(false)

  useEffect(() => {
    if (!modalOpen) return
    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = prevOverflow
    }
  }, [modalOpen])

  useEffect(() => {
    const t = setTimeout(() => setDebouncedBusca(busca.trim()), 400)
    return () => clearTimeout(t)
  }, [busca])

  useEffect(() => {
    setPage(1)
  }, [debouncedBusca, incluirInativos, ordenarPor, ordem])

  const load = useCallback(() => {
    setLoading(true)
    setForbidden(false)
    atendentes
      .list({
        incluir_inativos: incluirInativos,
        busca: debouncedBusca || undefined,
        ...sortParams,
        offset: (page - 1) * PAGE_SIZE_PADRAO,
        limit: PAGE_SIZE_PADRAO,
      })
      .then(({ items, total: t }) => {
        setList(items)
        setTotal(t)
      })
      .catch((err) => {
        setList([])
        setTotal(0)
        if (err instanceof ApiError && err.status === 403) {
          setForbidden(true)
          return
        }
        toast.showError(mensagemFalhaParaToast(err, 'Não encontramos a lista de atendentes.'))
      })
      .finally(() => setLoading(false))
  }, [debouncedBusca, incluirInativos, page, sortParams, toast])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    coletarTodasPaginas<Setores.Setor>((o, l) =>
      setores.list({ incluir_inativos: true, offset: o, limit: l }),
    ).then(setSetoresList)
  }, [])

  function openCreate() {
    setEditingId(null)
    setEmail('')
    setNome('')
    setSenha('')
    setMostrarSenha(false)
    setRole('atendente')
    setAtivo(true)
    setSetorIds([])
    setModalOpen(true)
  }

  function openEdit(item: Atendentes.Atendente) {
    setEditingId(item.id)
    setEmail(item.email)
    setNome(item.nome)
    setSenha('')
    setMostrarSenha(false)
    setRole((item.role as 'admin') || 'atendente')
    setAtivo(item.ativo)
    setSetorIds(item.setor_ids ?? [])
    setModalOpen(true)
  }

  function toggleSetor(id: number) {
    setSetorIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      if (editingId) {
        await atendentes.update(editingId, {
          email,
          nome: nome.trim(),
          role,
          ativo,
          setor_ids: setorIds,
          ...(senha ? { senha } : {}),
        })
      } else {
        if (!senha) throw new Error('Senha obrigatória para novo atendente')
        await atendentes.create({
          email,
          nome: nome.trim(),
          senha,
          role,
          setor_ids: setorIds,
          ativo,
        })
      }
      toast.showSuccess(editingId ? 'Atendente atualizado.' : 'Atendente cadastrado.')
      setModalOpen(false)
      load()
    } catch (err) {
      toast.showError(err instanceof Error ? err.message : 'Erro')
    } finally {
      setSaving(false)
    }
  }

  if (forbidden) {
    return (
      <div className="mx-auto max-w-6xl space-y-6 pb-10">
        <SemPermissao
          title="Você não tem permissão para listar atendentes."
          detail="Se isso estiver incorreto, peça ao administrador para ajustar seu perfil."
          voltarPara="/"
          voltarLabel="Voltar para o Dashboard"
        />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6 pb-10">
      <div className="flex justify-between">
        <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100">Atendentes</h1>
        <Button onClick={openCreate}>Novo atendente</Button>
      </div>
      {!modalOpen && (
        <Card>
          <BarraBuscaPaginacao
            busca={busca}
            onBuscaChange={setBusca}
            placeholder="Buscar por nome ou e-mail"
            page={page}
            total={total}
            onPageChange={setPage}
            disabled={loading}
            extra={<FiltroInativos incluirInativos={incluirInativos} onChange={setIncluirInativos} />}
          />
        {loading ? (
          <p className="text-slate-500 dark:text-slate-400">Carregando...</p>
        ) : list.length === 0 ? (
          <p className="text-slate-500 dark:text-slate-400">Nenhum atendente encontrado.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/60 dark:border-slate-800 dark:bg-slate-800/40">
                  <CabecalhoOrdenavel coluna="nome" rotulo="Nome" ordenarPor={ordenarPor} ordem={ordem} aoOrdenar={aoOrdenarColuna} />
                  <CabecalhoOrdenavel coluna="email" rotulo="E-mail" ordenarPor={ordenarPor} ordem={ordem} aoOrdenar={aoOrdenarColuna} />
                  <CabecalhoOrdenavel coluna="role" rotulo="Perfil" ordenarPor={ordenarPor} ordem={ordem} aoOrdenar={aoOrdenarColuna} />
                  <th className="w-px px-4 py-3 text-right text-xs font-semibold uppercase text-slate-500 sm:px-6 dark:text-slate-400">
                    <span className="sr-only">Ações</span>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {list.map((a) => (
                  <tr
                    key={a.id}
                    role="button"
                    tabIndex={0}
                    onClick={() => openEdit(a)}
                    onKeyDown={(ev) => {
                      if (ev.key === 'Enter' || ev.key === ' ') {
                        ev.preventDefault()
                        openEdit(a)
                      }
                    }}
                    className="cursor-pointer transition-colors hover:bg-slate-50 dark:hover:bg-slate-800/50 focus:outline-none focus-visible:bg-slate-100/80 dark:focus-visible:bg-slate-800/60"
                  >
                    <td className="px-4 py-3.5 sm:px-6">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className={`font-medium ${a.ativo ? 'text-slate-800 dark:text-slate-100' : 'text-slate-400'}`}>{a.nome}</span>
                        {!a.ativo && (
                          <span className="shrink-0 rounded bg-slate-200 px-1.5 py-0.5 text-xs text-slate-600 dark:text-slate-400">Inativo</span>
                        )}
                      </div>
                    </td>
                    <td className="max-w-[14rem] truncate px-4 py-3.5 text-slate-600 sm:px-6 dark:text-slate-400" title={a.email}>
                      {a.email}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3.5 text-slate-600 sm:px-6 dark:text-slate-400">
                      {roleLabel[a.role] ?? a.role}
                    </td>
                    <td className="px-4 py-3.5 text-right sm:px-6" onClick={(ev) => ev.stopPropagation()}>
                      <Button variant="ghost" onClick={() => openEdit(a)} aria-label="Editar">
                        <IconPencil />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

        )}
        </Card>
      )}

      {modalOpen && (
        <div className="fixed inset-y-0 left-0 right-0 z-20 flex items-start justify-center bg-black/85 px-4 pb-6 pt-16 sm:px-6 md:left-[var(--sidebar-w)]">
          <Card title={editingId ? 'Editar atendente' : 'Novo atendente'} className="w-full max-w-md">
            <form onSubmit={handleSubmit}>
              <div className="space-y-6">
                <FormSection title="Dados do atendente">
                  <Input label="E-mail" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
                  <Input label="Nome" value={nome} onChange={(e) => setNome(e.target.value)} required />
                  <Input
                    label={editingId ? 'Nova senha (deixe em branco para manter)' : 'Senha'}
                    type={mostrarSenha ? 'text' : 'password'}
                    value={senha}
                    onChange={(e) => setSenha(e.target.value)}
                    required={!editingId}
                    endAdornment={
                      <button
                        type="button"
                        onClick={() => setMostrarSenha((v) => !v)}
                        className="inline-flex size-9 items-center justify-center rounded-md text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400/30 dark:text-slate-400 dark:hover:bg-slate-800/70 dark:hover:text-slate-200"
                        aria-label={mostrarSenha ? 'Ocultar senha' : 'Mostrar senha'}
                        aria-pressed={mostrarSenha}
                      >
                        {mostrarSenha ? <IconEyeOff ariaHidden={false} /> : <IconEye ariaHidden={false} />}
                      </button>
                    }
                  />
                  <Select
                    label="Perfil"
                    value={role}
                    onChange={(v) => setRole(v === 'admin' ? 'admin' : 'atendente')}
                    options={[
                      { value: 'atendente', label: 'Atendente' },
                      { value: 'admin', label: 'Administrador' },
                    ]}
                  />
                </FormSection>

                <FormSection title="Setores">
                  {role === 'admin' && (
                    <p className="mb-2 text-xs text-slate-500 dark:text-slate-400">
                      Opcional, mas recomendado: vincule administradores a setores para poderem ser responsáveis em tickets do setor.
                    </p>
                  )}
                  <div className="max-h-44 overflow-auto rounded-lg border border-slate-200 p-3 dark:border-slate-700/80">
                    <div className="flex flex-wrap gap-2">
                      {setoresList.map((s) => (
                        <CheckboxField
                          key={s.id}
                          checked={setorIds.includes(s.id)}
                          onChange={() => toggleSetor(s.id)}
                        >
                          {s.nome}
                        </CheckboxField>
                      ))}
                    </div>
                  </div>
                </FormSection>

                <FormSection title="Situação no sistema">
                  <Switch
                    bare
                    checked={ativo}
                    onCheckedChange={setAtivo}
                    label="Atendente ativo"
                    description="Inativos não acessam o sistema."
                    showStatusPill
                    statusOnText="Ativo"
                    statusOffText="Inativo"
                  />
                </FormSection>
              </div>

              <div className="sticky bottom-0 -mx-6 mt-6 border-t border-slate-200 bg-white px-6 py-4 dark:border-slate-700 dark:bg-slate-900">
                <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
                  <Button type="button" variant="secondary" className="w-full sm:w-auto" onClick={() => setModalOpen(false)}>
                    Cancelar
                  </Button>
                  <Button type="submit" loading={saving} className="w-full sm:w-auto">
                    Salvar
                  </Button>
                </div>
              </div>
            </form>
          </Card>
        </div>
      )}
    </div>
  )
}
