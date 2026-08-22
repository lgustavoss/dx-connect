import { useCallback, useEffect, useState } from 'react'
import {
  ApiError,
  atendentes,
  redes,
  routingRules,
  setores,
  ticketClassificacao,
  type RoutingRules,
} from '../api/client'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { ConfigListPageShell } from '../components/config/ConfigListPageShell'
import { FiltroInativos } from '../components/ui/FiltroInativos'
import { useToast } from '../components/ui/Toast'
import { SemPermissao } from './SemPermissao'
import { mensagemFalhaParaToast } from '../api/errorMessage'

const CAMPOS: { value: RoutingRules.Campo; label: string }[] = [
  { value: 'email_from', label: 'Remetente (e-mail)' },
  { value: 'email_to', label: 'Destinatário (e-mail)' },
  { value: 'assunto', label: 'Assunto' },
  { value: 'canal', label: 'Canal' },
]

const OPERADORES: { value: RoutingRules.Operador; label: string }[] = [
  { value: 'contains', label: 'contém' },
  { value: 'equals', label: 'é igual a' },
  { value: 'regex', label: 'expressão regular' },
]

const PRIORIDADES: RoutingRules.Prioridade[] = ['baixa', 'normal', 'alta', 'urgente']

function condicaoVazia(): RoutingRules.Condicao {
  return { campo: 'assunto', operador: 'contains', valor: '' }
}

function formVazio(): RoutingRules.Create {
  return {
    nome: '',
    ativo: true,
    rede_id: null,
    condicoes: [condicaoVazia()],
    acoes: { setor_id: null },
  }
}

export function RoteamentoRegrasPage({ embedded = false }: { embedded?: boolean }) {
  const toast = useToast()
  const [list, setList] = useState<RoutingRules.Regra[]>([])
  const [loading, setLoading] = useState(true)
  const [forbidden, setForbidden] = useState(false)
  const [incluirInativos, setIncluirInativos] = useState(false)
  const [setorOpts, setSetorOpts] = useState<{ id: number; nome: string }[]>([])
  const [redeOpts, setRedeOpts] = useState<{ id: number; nome: string }[]>([])
  const [naturezaOpts, setNaturezaOpts] = useState<{ id: number; nome: string }[]>([])
  const [motivoOpts, setMotivoOpts] = useState<{ id: number; nome: string; natureza_id: number }[]>([])
  const [atendenteOpts, setAtendenteOpts] = useState<{ id: number; nome: string }[]>([])

  const [editId, setEditId] = useState<number | null>(null)
  const [form, setForm] = useState<RoutingRules.Create>(formVazio())
  const [saving, setSaving] = useState(false)

  const [simAssunto, setSimAssunto] = useState('')
  const [simFrom, setSimFrom] = useState('')
  const [simTo, setSimTo] = useState('')
  const [simCanal, setSimCanal] = useState<RoutingRules.Canal>('email')
  const [simResult, setSimResult] = useState<RoutingRules.Resultado | null>(null)

  const load = useCallback(() => {
    setLoading(true)
    setForbidden(false)
    routingRules
      .list({ incluir_inativos: incluirInativos })
      .then(setList)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 403) {
          setForbidden(true)
          setList([])
          return
        }
        toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível carregar as regras.'))
      })
      .finally(() => setLoading(false))
  }, [incluirInativos, toast])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    setores.list({ limit: 100 }).then(({ items }) => setSetorOpts(items.map((s) => ({ id: s.id, nome: s.nome }))))
    redes.list({ limit: 100 }).then(({ items }) => setRedeOpts(items.map((r) => ({ id: r.id, nome: r.nome }))))
    ticketClassificacao.listNaturezas({ limit: 100 }).then(({ items }) =>
      setNaturezaOpts(items.map((n) => ({ id: n.id, nome: n.nome }))),
    )
    ticketClassificacao.listMotivos({ limit: 300 }).then(({ items }) =>
      setMotivoOpts(items.map((m) => ({ id: m.id, nome: m.nome, natureza_id: m.natureza_id }))),
    )
    atendentes.list({ limit: 100 }).then(({ items }) =>
      setAtendenteOpts(items.map((a) => ({ id: a.id, nome: a.nome }))),
    )
  }, [])

  const motivosFiltrados = form.acoes.natureza_id
    ? motivoOpts.filter((m) => m.natureza_id === form.acoes.natureza_id)
    : motivoOpts

  function iniciarNova() {
    setEditId(null)
    setForm(formVazio())
  }

  function iniciarEdicao(regra: RoutingRules.Regra) {
    setEditId(regra.id)
    setForm({
      nome: regra.nome,
      ativo: regra.ativo,
      rede_id: regra.rede_id,
      condicoes: regra.condicoes.length ? regra.condicoes : [condicaoVazia()],
      acoes: { ...regra.acoes },
    })
  }

  async function salvar() {
    if (!form.nome.trim()) {
      toast.showWarning('Informe o nome da regra.')
      return
    }
    if (!form.condicoes.every((c) => c.valor.trim())) {
      toast.showWarning('Preencha o valor de todas as condições.')
      return
    }
    if (
      !form.acoes.setor_id &&
      !form.acoes.prioridade &&
      !form.acoes.motivo_id &&
      !form.acoes.natureza_id &&
      !form.acoes.atendente_id
    ) {
      toast.showWarning('Informe ao menos uma ação (setor, prioridade, natureza, motivo ou atendente).')
      return
    }
    setSaving(true)
    try {
      if (editId) {
        await routingRules.update(editId, form)
        toast.showSuccess('Regra atualizada.')
      } else {
        await routingRules.create(form)
        toast.showSuccess('Regra criada.')
      }
      setEditId(null)
      setForm(formVazio())
      load()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível salvar a regra.'))
    } finally {
      setSaving(false)
    }
  }

  async function excluir(id: number) {
    if (!window.confirm('Excluir esta regra de roteamento?')) return
    try {
      await routingRules.delete(id)
      toast.showSuccess('Regra excluída.')
      if (editId === id) iniciarNova()
      load()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível excluir.'))
    }
  }

  async function mover(idx: number, dir: -1 | 1) {
    const nova = [...list]
    const alvo = idx + dir
    if (alvo < 0 || alvo >= nova.length) return
    ;[nova[idx], nova[alvo]] = [nova[alvo], nova[idx]]
    const items = nova.map((r, i) => ({ id: r.id, ordem: i }))
    try {
      const atualizado = await routingRules.reorder(items)
      setList(atualizado)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível reordenar.'))
    }
  }

  async function simular() {
    try {
      const res = await routingRules.simulate({
        assunto: simAssunto || null,
        email_from: simFrom || null,
        email_to: simTo || null,
        canal: simCanal,
      })
      setSimResult(res)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Falha na simulação.'))
    }
  }

  const denied = (
    <SemPermissao
      title="Você não tem permissão para gerenciar roteamento."
      voltarPara="/"
      voltarLabel="Voltar para o Dashboard"
    />
  )

  return (
    <ConfigListPageShell
      embedded={embedded}
      forbidden={forbidden}
      denied={denied}
      title="Roteamento automático"
      subtitle="Regras avaliadas em ordem — a primeira que casar define setor, prioridade ou classificação."
      actions={<Button onClick={iniciarNova}>Nova regra</Button>}
    >
      <div className="flex flex-wrap items-center gap-3 mb-4">
        <FiltroInativos incluirInativos={incluirInativos} onChange={setIncluirInativos} />
      </div>

      <Card className="mb-6 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 dark:border-slate-800 text-left">
              <th className="p-2 w-20">Ordem</th>
              <th className="p-2">Nome</th>
              <th className="p-2">Escopo</th>
              <th className="p-2">Condições</th>
              <th className="p-2">Ações</th>
              <th className="p-2 w-32" />
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={6} className="p-4 text-slate-500">
                  Carregando…
                </td>
              </tr>
            ) : list.length === 0 ? (
              <tr>
                <td colSpan={6} className="p-4 text-slate-500">
                  Nenhuma regra cadastrada.
                </td>
              </tr>
            ) : (
              list.map((r, idx) => (
                <tr key={r.id} className="border-b border-slate-100 dark:border-slate-800">
                  <td className="p-2">
                    <div className="flex gap-1">
                      <Button type="button" variant="ghost" className="px-2 py-1" onClick={() => mover(idx, -1)} disabled={idx === 0}>
                        ↑
                      </Button>
                      <Button
                        type="button"
                        variant="ghost"
                        className="px-2 py-1"
                        onClick={() => mover(idx, 1)}
                        disabled={idx === list.length - 1}
                      >
                        ↓
                      </Button>
                    </div>
                  </td>
                  <td className="p-2">
                    <span className="font-medium">{r.nome}</span>
                    {!r.ativo ? (
                      <span className="ml-2 text-xs text-amber-600 dark:text-amber-400">inativa</span>
                    ) : null}
                  </td>
                  <td className="p-2">{r.rede_id ? `Rede #${r.rede_id}` : 'Global'}</td>
                  <td className="p-2 text-slate-600 dark:text-slate-400">
                    {r.condicoes.map((c, i) => (
                      <span key={i}>
                        {i > 0 ? ' e ' : ''}
                        {c.campo} {c.operador} «{c.valor}»
                      </span>
                    ))}
                  </td>
                  <td className="p-2 text-slate-600 dark:text-slate-400">
                    {r.acoes.setor_id ? `setor #${r.acoes.setor_id} ` : ''}
                    {r.acoes.prioridade ? `prioridade ${r.acoes.prioridade} ` : ''}
                    {r.acoes.natureza_id ? `natureza #${r.acoes.natureza_id} ` : ''}
                    {r.acoes.motivo_id ? `motivo #${r.acoes.motivo_id} ` : ''}
                    {r.acoes.atendente_id ? `atendente #${r.acoes.atendente_id}` : ''}
                  </td>
                  <td className="p-2">
                    <Button type="button" variant="ghost" className="px-2 py-1" onClick={() => iniciarEdicao(r)}>
                      Editar
                    </Button>
                    <Button type="button" variant="ghost" className="px-2 py-1" onClick={() => excluir(r.id)}>
                      Excluir
                    </Button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </Card>

      {(editId !== null || form.nome || form.condicoes[0]?.valor) && (
        <Card className="mb-6 p-4 space-y-4">
          <h3 className="font-semibold">{editId ? 'Editar regra' : 'Nova regra'}</h3>
          <div className="grid gap-3 md:grid-cols-2">
            <label className="block text-sm">
              Nome
              <input
                className="mt-1 w-full rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 px-2 py-1.5"
                value={form.nome}
                onChange={(e) => setForm((f) => ({ ...f, nome: e.target.value }))}
              />
            </label>
            <label className="block text-sm">
              Escopo (rede)
              <select
                className="mt-1 w-full rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 px-2 py-1.5"
                value={form.rede_id ?? ''}
                onChange={(e) =>
                  setForm((f) => ({ ...f, rede_id: e.target.value ? Number(e.target.value) : null }))
                }
              >
                <option value="">Global (todas as redes)</option>
                {redeOpts.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.nome}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div>
            <p className="text-sm font-medium mb-2">Condições (todas devem casar)</p>
            {form.condicoes.map((c, idx) => (
              <div key={idx} className="flex flex-wrap gap-2 mb-2 items-end">
                <select
                  className="rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 px-2 py-1.5 text-sm"
                  value={c.campo}
                  onChange={(e) => {
                    const campo = e.target.value as RoutingRules.Campo
                    setForm((f) => {
                      const condicoes = [...f.condicoes]
                      condicoes[idx] = { ...condicoes[idx], campo }
                      return { ...f, condicoes }
                    })
                  }}
                >
                  {CAMPOS.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
                <select
                  className="rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 px-2 py-1.5 text-sm"
                  value={c.operador}
                  onChange={(e) => {
                    const operador = e.target.value as RoutingRules.Operador
                    setForm((f) => {
                      const condicoes = [...f.condicoes]
                      condicoes[idx] = { ...condicoes[idx], operador }
                      return { ...f, condicoes }
                    })
                  }}
                >
                  {OPERADORES.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
                <input
                  className="flex-1 min-w-[120px] rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 px-2 py-1.5 text-sm"
                  placeholder="Valor"
                  value={c.valor}
                  onChange={(e) => {
                    const valor = e.target.value
                    setForm((f) => {
                      const condicoes = [...f.condicoes]
                      condicoes[idx] = { ...condicoes[idx], valor }
                      return { ...f, condicoes }
                    })
                  }}
                />
                {form.condicoes.length > 1 ? (
                  <Button
                    type="button"
                    variant="ghost"
                    className="px-2 py-1"
                    onClick={() =>
                      setForm((f) => ({ ...f, condicoes: f.condicoes.filter((_, i) => i !== idx) }))
                    }
                  >
                    Remover
                  </Button>
                ) : null}
              </div>
            ))}
            <Button
              type="button"
              variant="ghost"
              className="px-2 py-1"
              onClick={() => setForm((f) => ({ ...f, condicoes: [...f.condicoes, condicaoVazia()] }))}
            >
              + Condição
            </Button>
          </div>

          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            <label className="block text-sm">
              Setor destino
              <select
                className="mt-1 w-full rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 px-2 py-1.5"
                value={form.acoes.setor_id ?? ''}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    acoes: { ...f.acoes, setor_id: e.target.value ? Number(e.target.value) : null },
                  }))
                }
              >
                <option value="">—</option>
                {setorOpts.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.nome}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm">
              Prioridade
              <select
                className="mt-1 w-full rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 px-2 py-1.5"
                value={form.acoes.prioridade ?? ''}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    acoes: {
                      ...f.acoes,
                      prioridade: (e.target.value || null) as RoutingRules.Prioridade | null,
                    },
                  }))
                }
              >
                <option value="">—</option>
                {PRIORIDADES.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm">
              Atendente responsável
              <select
                className="mt-1 w-full rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 px-2 py-1.5"
                value={form.acoes.atendente_id ?? ''}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    acoes: { ...f.acoes, atendente_id: e.target.value ? Number(e.target.value) : null },
                  }))
                }
              >
                <option value="">—</option>
                {atendenteOpts.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.nome}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm">
              Natureza sugerida
              <select
                className="mt-1 w-full rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 px-2 py-1.5"
                value={form.acoes.natureza_id ?? ''}
                onChange={(e) => {
                  const natureza_id = e.target.value ? Number(e.target.value) : null
                  setForm((f) => ({
                    ...f,
                    acoes: {
                      ...f.acoes,
                      natureza_id,
                      motivo_id:
                        f.acoes.motivo_id &&
                        motivoOpts.find((m) => m.id === f.acoes.motivo_id)?.natureza_id !== natureza_id
                          ? null
                          : f.acoes.motivo_id,
                    },
                  }))
                }}
              >
                <option value="">—</option>
                {naturezaOpts.map((n) => (
                  <option key={n.id} value={n.id}>
                    {n.nome}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm md:col-span-2">
              Motivo sugerido
              <select
                className="mt-1 w-full rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 px-2 py-1.5"
                value={form.acoes.motivo_id ?? ''}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    acoes: { ...f.acoes, motivo_id: e.target.value ? Number(e.target.value) : null },
                  }))
                }
              >
                <option value="">—</option>
                {motivosFiltrados.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.nome}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.ativo !== false}
              onChange={(e) => setForm((f) => ({ ...f, ativo: e.target.checked }))}
            />
            Regra ativa
          </label>

          <div className="flex gap-2">
            <Button onClick={salvar} disabled={saving}>
              {saving ? 'Salvando…' : 'Salvar'}
            </Button>
            <Button type="button" variant="cancel" onClick={iniciarNova}>
              Cancelar
            </Button>
          </div>
        </Card>
      )}

      <Card className="p-4 space-y-3">
        <h3 className="font-semibold">Simular roteamento</h3>
        <p className="text-sm text-slate-600 dark:text-slate-400">
          Teste seco — não cria ticket. Chats WhatsApp não são afetados por estas regras.
        </p>
        <div className="grid gap-3 md:grid-cols-2">
          <input
            className="rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 px-2 py-1.5 text-sm"
            placeholder="Assunto"
            value={simAssunto}
            onChange={(e) => setSimAssunto(e.target.value)}
          />
          <input
            className="rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 px-2 py-1.5 text-sm"
            placeholder="Remetente"
            value={simFrom}
            onChange={(e) => setSimFrom(e.target.value)}
          />
          <input
            className="rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 px-2 py-1.5 text-sm"
            placeholder="Destinatário"
            value={simTo}
            onChange={(e) => setSimTo(e.target.value)}
          />
          <select
            className="rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 px-2 py-1.5 text-sm"
            value={simCanal}
            onChange={(e) => setSimCanal(e.target.value as RoutingRules.Canal)}
          >
            <option value="email">E-mail</option>
            <option value="manual">Manual</option>
          </select>
        </div>
        <Button type="button" onClick={simular}>
          Simular
        </Button>
        {simResult ? (
          <pre className="text-xs bg-slate-100 dark:bg-slate-800 p-3 rounded overflow-x-auto">
            {JSON.stringify(simResult, null, 2)}
          </pre>
        ) : null}
      </Card>
    </ConfigListPageShell>
  )
}
