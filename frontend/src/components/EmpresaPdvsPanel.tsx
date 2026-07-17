import { useCallback, useEffect, useState } from 'react'
import { empresaPdvs, pdvRotulos, pdvTiposAcessoRemoto, type EmpresaPdv, type PdvCatalogo } from '../api/client'
import { coletarTodasPaginas } from '../api/collectPages'
import { Button } from './ui/Button'
import { IconCopy } from './ui/IconCopy'
import { IconEye, IconEyeOff } from './ui/IconEye'
import { IconPencil } from './ui/IconPencil'
import { Input } from './ui/Input'
import { Select } from './ui/Select'
import { Switch } from './ui/Switch'
import { useToast } from './ui/Toast'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { useAuth } from '../contexts/AuthContext'

type Props = { empresaId: number }

const emptyForm = (): EmpresaPdv.Create => ({
  codigo: '',
  rotulo_id: 0,
  papel: 'principal',
  usa_tef: false,
  tipo_acesso_remoto_id: null,
  acesso_remoto_id: '',
  acesso_remoto_senha: '',
  observacoes: '',
  ativo: true,
})

export function EmpresaPdvsPanel({ empresaId }: Props) {
  const toast = useToast()
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'
  const [items, setItems] = useState<EmpresaPdv.Item[]>([])
  const [loading, setLoading] = useState(true)
  const [rotulos, setRotulos] = useState<PdvCatalogo.Item[]>([])
  const [tipos, setTipos] = useState<PdvCatalogo.Item[]>([])
  const [modalOpen, setModalOpen] = useState(false)
  const [editId, setEditId] = useState<number | null>(null)
  const [form, setForm] = useState<EmpresaPdv.Create>(emptyForm())
  const [saving, setSaving] = useState(false)
  const [senhaRevelada, setSenhaRevelada] = useState<{ pdvId: number; senha: string } | null>(null)
  const [revelandoPdvId, setRevelandoPdvId] = useState<number | null>(null)

  const load = useCallback(() => {
    setLoading(true)
    empresaPdvs
      .list(empresaId, { incluir_inativos: true })
      .then((r) => setItems(r.items))
      .catch((err) => toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível carregar os PDVs.')))
      .finally(() => setLoading(false))
  }, [empresaId, toast])

  useEffect(() => {
    load()
    coletarTodasPaginas<PdvCatalogo.Item>((o, l) => pdvRotulos.list({ offset: o, limit: l })).then(setRotulos)
    coletarTodasPaginas<PdvCatalogo.Item>((o, l) => pdvTiposAcessoRemoto.list({ offset: o, limit: l })).then(setTipos)
  }, [load])

  function abrirNovo() {
    setEditId(null)
    setForm({ ...emptyForm(), rotulo_id: rotulos[0]?.id ?? 0 })
    setSenhaRevelada(null)
    setModalOpen(true)
  }

  function abrirEditar(row: EmpresaPdv.Item) {
    setEditId(row.id)
    setForm({
      codigo: row.codigo,
      rotulo_id: row.rotulo_id,
      papel: row.papel,
      usa_tef: row.usa_tef,
      tipo_acesso_remoto_id: row.tipo_acesso_remoto_id ?? null,
      acesso_remoto_id: row.acesso_remoto_id ?? '',
      acesso_remoto_senha: '',
      observacoes: row.observacoes ?? '',
      ativo: row.ativo,
    })
    setSenhaRevelada(null)
    setModalOpen(true)
  }

  async function revelarSenha(pdvId: number) {
    if (!isAdmin) return
    if (senhaRevelada?.pdvId === pdvId) {
      setSenhaRevelada(null)
      return
    }
    setRevelandoPdvId(pdvId)
    try {
      const r = await empresaPdvs.revelarCredencial(empresaId, pdvId)
      setSenhaRevelada({ pdvId, senha: r.acesso_remoto_senha })
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível revelar a senha.'))
    } finally {
      setRevelandoPdvId(null)
    }
  }

  async function copiarTexto(texto: string, sucesso: string) {
    try {
      await navigator.clipboard.writeText(texto)
      toast.showSuccess(sucesso)
    } catch {
      toast.showError('Não foi possível copiar. Selecione o texto manualmente.')
    }
  }

  async function salvar() {
    if (!form.codigo.trim() || !form.rotulo_id) {
      toast.showWarning('Informe o código e o rótulo do PDV.')
      return
    }
    setSaving(true)
    try {
      if (editId) {
        const payload: EmpresaPdv.Update = {
          codigo: form.codigo.trim(),
          rotulo_id: form.rotulo_id,
          papel: form.papel,
          usa_tef: form.usa_tef,
          tipo_acesso_remoto_id: form.tipo_acesso_remoto_id,
          acesso_remoto_id: form.acesso_remoto_id || null,
          observacoes: form.observacoes || null,
          ativo: form.ativo,
        }
        if (form.acesso_remoto_senha?.trim()) payload.acesso_remoto_senha = form.acesso_remoto_senha.trim()
        await empresaPdvs.update(empresaId, editId, payload)
        toast.showSuccess('PDV atualizado.')
      } else {
        await empresaPdvs.create(empresaId, {
          ...form,
          codigo: form.codigo.trim(),
          acesso_remoto_id: form.acesso_remoto_id?.trim() || null,
          acesso_remoto_senha: form.acesso_remoto_senha?.trim() || null,
          observacoes: form.observacoes?.trim() || null,
        })
        toast.showSuccess('PDV cadastrado.')
      }
      setModalOpen(false)
      load()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível salvar o PDV.'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Terminais/pontos de venda desta empresa. O código (ex.: 001) identifica o ponto; pode ser alterado se a
          numeração mudar (único por empresa).
        </p>
        {isAdmin ? (
          <Button type="button" onClick={abrirNovo}>
            Novo PDV
          </Button>
        ) : null}
      </div>

      {loading && items.length === 0 ? (
        <p className="text-sm text-slate-500">Carregando PDVs…</p>
      ) : items.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 p-6 text-center dark:border-slate-600">
          <p className="text-sm text-slate-600 dark:text-slate-300">Nenhum PDV cadastrado.</p>
          {isAdmin ? (
            <Button type="button" className="mt-3" onClick={abrirNovo}>
              Cadastrar primeiro PDV
            </Button>
          ) : null}
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[800px] text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/60 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:border-slate-800 dark:bg-slate-800/40">
                <th className="px-4 py-3">Código</th>
                <th className="px-4 py-3">Rótulo</th>
                <th className="px-4 py-3">Papel</th>
                <th className="px-4 py-3">TEF</th>
                <th className="px-4 py-3">Acesso remoto</th>
                <th className="px-4 py-3">ID acesso</th>
                <th className="px-4 py-3">Senha acesso</th>
                <th className="px-4 py-3 text-right">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {items.map((row) => (
                <tr key={row.id} className={!row.ativo ? 'opacity-60' : undefined}>
                  <td className="px-4 py-3 font-mono font-medium">{row.codigo}</td>
                  <td className="px-4 py-3">{row.rotulo_nome ?? '—'}</td>
                  <td className="px-4 py-3 capitalize">{row.papel}</td>
                  <td className="px-4 py-3">{row.usa_tef ? 'Sim' : 'Não'}</td>
                  <td className="px-4 py-3 text-slate-600 dark:text-slate-300">
                    {row.tipo_acesso_remoto_nome ?? '—'}
                  </td>
                  <td className="px-4 py-3">
                    {row.acesso_remoto_id ? (
                      <span className="inline-flex items-center gap-1">
                        <span className="font-mono text-slate-700 dark:text-slate-200">{row.acesso_remoto_id}</span>
                        <button
                          type="button"
                          className="inline-flex size-7 shrink-0 items-center justify-center rounded-md text-slate-400 transition hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800 dark:hover:text-slate-200"
                          onClick={() => void copiarTexto(row.acesso_remoto_id!, 'ID de acesso copiado.')}
                          aria-label="Copiar ID de acesso remoto"
                          title="Copiar ID"
                        >
                          <IconCopy className="size-4" ariaHidden={false} />
                        </button>
                      </span>
                    ) : (
                      <span className="text-slate-400">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {row.tem_senha_remota && isAdmin ? (
                      senhaRevelada?.pdvId === row.id ? (
                        <span className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-slate-50 px-2 py-0.5 font-mono text-xs text-slate-700 dark:border-slate-800 dark:bg-slate-800/80 dark:text-slate-200">
                          {senhaRevelada.senha}
                          <button
                            type="button"
                            className="rounded p-0.5 text-slate-400 transition hover:text-slate-600 dark:hover:text-slate-200"
                            onClick={() => void copiarTexto(senhaRevelada.senha, 'Senha copiada.')}
                            aria-label="Copiar senha de acesso remoto"
                            title="Copiar senha"
                          >
                            <IconCopy className="size-3.5" ariaHidden={false} />
                          </button>
                          <button
                            type="button"
                            className="rounded p-0.5 text-slate-400 transition hover:text-slate-600 dark:hover:text-slate-200"
                            onClick={() => setSenhaRevelada(null)}
                            aria-label="Ocultar senha"
                          >
                            <IconEyeOff className="size-3.5" ariaHidden={false} />
                          </button>
                        </span>
                      ) : (
                        <button
                          type="button"
                          className="inline-flex size-7 shrink-0 items-center justify-center rounded-md text-slate-400 transition hover:bg-slate-100 hover:text-slate-600 disabled:opacity-50 dark:hover:bg-slate-800 dark:hover:text-slate-200"
                          onClick={() => void revelarSenha(row.id)}
                          disabled={revelandoPdvId === row.id}
                          aria-label="Revelar senha de acesso remoto"
                          title="Revelar senha"
                        >
                          {revelandoPdvId === row.id ? (
                            <span className="size-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />
                          ) : (
                            <IconEye className="size-4" ariaHidden={false} />
                          )}
                        </button>
                      )
                    ) : row.tem_senha_remota ? (
                      <span className="text-slate-400">••••</span>
                    ) : (
                      <span className="text-slate-400">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {isAdmin ? (
                      <Button
                        type="button"
                        variant="ghost"
                        className="!px-2 !py-2"
                        onClick={() => abrirEditar(row)}
                        aria-label={`Editar PDV ${row.codigo}`}
                      >
                        <IconPencil ariaHidden={false} />
                      </Button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {modalOpen && isAdmin ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-slate-200 bg-white p-6 shadow-xl dark:border-slate-800 dark:bg-slate-900">
            <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-50">
              {editId ? 'Editar PDV' : 'Novo PDV'}
            </h3>
            <div className="mt-4 space-y-4">
              <Input
                label="Código (ex.: 001)"
                hint="Número do ponto na empresa. Ao trocar o equipamento principal, altere o código aqui (não use o prefixo «PDV»)."
                value={form.codigo}
                onChange={(e) => setForm((f) => ({ ...f, codigo: e.target.value }))}
                required
              />
              <div>
                <Select
                  label="Rótulo do dispositivo"
                  value={form.rotulo_id || ''}
                  onChange={(v) => setForm((f) => ({ ...f, rotulo_id: Number(v) }))}
                  options={rotulos.map((r) => ({ value: r.id, label: r.nome }))}
                />
                <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                  Tipo do equipamento (ex.: SRV/PDV), não o número do ponto.
                </p>
              </div>
              <Select
                label="Papel"
                value={form.papel}
                onChange={(v) => setForm((f) => ({ ...f, papel: v as 'principal' | 'auxiliar' }))}
                options={[
                  { value: 'principal', label: 'Principal' },
                  { value: 'auxiliar', label: 'Auxiliar' },
                ]}
              />
              <Switch bare checked={!!form.usa_tef} onCheckedChange={(v) => setForm((f) => ({ ...f, usa_tef: v }))} label="Usa TEF" />
              <Select
                label="Tipo de acesso remoto"
                value={form.tipo_acesso_remoto_id ?? ''}
                onChange={(v) =>
                  setForm((f) => ({ ...f, tipo_acesso_remoto_id: v === '' ? null : Number(v) }))
                }
                options={[{ value: '', label: '—' }, ...tipos.map((t) => ({ value: t.id, label: t.nome }))]}
              />
              <Input
                label="ID de acesso remoto"
                value={form.acesso_remoto_id ?? ''}
                onChange={(e) => setForm((f) => ({ ...f, acesso_remoto_id: e.target.value }))}
              />
              <Input
                label={editId ? 'Nova senha (deixe vazio para manter)' : 'Senha de acesso remoto'}
                type="password"
                value={form.acesso_remoto_senha ?? ''}
                onChange={(e) => setForm((f) => ({ ...f, acesso_remoto_senha: e.target.value }))}
              />
              <Input
                label="Observações"
                value={form.observacoes ?? ''}
                onChange={(e) => setForm((f) => ({ ...f, observacoes: e.target.value }))}
              />
              <Switch bare checked={form.ativo ?? true} onCheckedChange={(v) => setForm((f) => ({ ...f, ativo: v }))} label="Ativo" />
            </div>
            <div className="mt-6 flex justify-end gap-2">
              <Button type="button" variant="secondary" onClick={() => setModalOpen(false)}>
                Cancelar
              </Button>
              <Button type="button" loading={saving} onClick={() => void salvar()}>
                Salvar
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}
