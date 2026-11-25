import { useCallback, useEffect, useState } from 'react'
import { ApiError, cobrancaContas, type CobrancaContas } from '../api/client'
import { mensagemFalhaParaToast } from '../api/errorMessage'
import { ConfigListPageShell } from '../components/config/ConfigListPageShell'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { IconEye, IconEyeOff } from '../components/ui/IconEye'
import { Input } from '../components/ui/Input'
import { useToast } from '../components/ui/Toast'
import { useAuth } from '../contexts/AuthContext'
import { temPermissao } from '../lib/permissoes'
import { SemPermissao } from './SemPermissao'

type FormState = {
  id: number | null
  apelido: string
  bancoCodigo: string
  bancoNome: string
  agencia: string
  agenciaDv: string
  conta: string
  contaDv: string
  carteira: string
  titularNome: string
  titularDocumento: string
  ativo: boolean
  padrao: boolean
  notas: string
  token: string
  temToken: boolean
}

const FORM_VAZIO: FormState = {
  id: null,
  apelido: '',
  bancoCodigo: '',
  bancoNome: '',
  agencia: '',
  agenciaDv: '',
  conta: '',
  contaDv: '',
  carteira: '',
  titularNome: '',
  titularDocumento: '',
  ativo: true,
  padrao: false,
  notas: '',
  token: '',
  temToken: false,
}

function contaParaForm(c: CobrancaContas.Conta): FormState {
  return {
    id: c.id,
    apelido: c.apelido,
    bancoCodigo: c.banco_codigo || '',
    bancoNome: c.banco_nome || '',
    agencia: c.agencia || '',
    agenciaDv: c.agencia_dv || '',
    conta: c.conta || '',
    contaDv: c.conta_dv || '',
    carteira: c.carteira || '',
    titularNome: c.titular_nome || '',
    titularDocumento: c.titular_documento || '',
    ativo: c.ativo,
    padrao: c.padrao,
    notas: c.notas || '',
    token: '',
    temToken: c.tem_token,
  }
}

/** Configurações → Financeiro → Contas bancárias (#1392). */
export function ConfigContasBancarias({ embedded = false }: { embedded?: boolean }) {
  const toast = useToast()
  const { user } = useAuth()
  const podeEditar = temPermissao(user, 'faturamento.politica')
  const [items, setItems] = useState<CobrancaContas.Conta[]>([])
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [forbidden, setForbidden] = useState(false)
  const [form, setForm] = useState<FormState>(FORM_VAZIO)
  const [editando, setEditando] = useState(false)
  const [mostrarToken, setMostrarToken] = useState(false)

  const load = useCallback(() => {
    setLoading(true)
    setForbidden(false)
    cobrancaContas
      .listar()
      .then((lista) => setItems(lista.items))
      .catch((err: unknown) => {
        if (err instanceof ApiError && err.status === 403) {
          setForbidden(true)
          return
        }
        toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível carregar as contas.'))
      })
      .finally(() => setLoading(false))
  }, [toast])

  useEffect(() => {
    load()
  }, [load])

  function abrirNovo() {
    setForm(FORM_VAZIO)
    setEditando(true)
    setMostrarToken(false)
  }

  function abrirEdicao(c: CobrancaContas.Conta) {
    setForm(contaParaForm(c))
    setEditando(true)
    setMostrarToken(false)
  }

  function fecharForm() {
    setEditando(false)
    setForm(FORM_VAZIO)
    setMostrarToken(false)
  }

  async function salvar(e: React.FormEvent) {
    e.preventDefault()
    if (!form.apelido.trim()) {
      toast.showWarning('Informe o apelido da conta.')
      return
    }
    if (form.id == null && !form.token.trim()) {
      toast.showWarning('Informe o token do Boleto Cloud no primeiro cadastro.')
      return
    }
    const body: CobrancaContas.Upsert = {
      apelido: form.apelido.trim(),
      banco_codigo: form.bancoCodigo.trim() || null,
      banco_nome: form.bancoNome.trim() || null,
      agencia: form.agencia.trim() || null,
      agencia_dv: form.agenciaDv.trim() || null,
      conta: form.conta.trim() || null,
      conta_dv: form.contaDv.trim() || null,
      carteira: form.carteira.trim() || null,
      titular_nome: form.titularNome.trim() || null,
      titular_documento: form.titularDocumento.trim() || null,
      ativo: form.ativo,
      padrao: form.padrao,
      notas: form.notas.trim() || null,
      boleto_cloud_token: form.token.trim() || null,
    }
    setBusy(true)
    try {
      if (form.id == null) {
        await cobrancaContas.criar(body)
        toast.showSuccess('Conta bancária cadastrada.')
      } else {
        await cobrancaContas.atualizar(form.id, body)
        toast.showSuccess('Conta bancária atualizada.')
      }
      fecharForm()
      load()
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível salvar a conta.'))
    } finally {
      setBusy(false)
    }
  }

  async function desativar(id: number) {
    if (!window.confirm('Desativar esta conta bancária?')) return
    setBusy(true)
    try {
      await cobrancaContas.desativar(id)
      toast.showSuccess('Conta desativada.')
      if (form.id === id) fecharForm()
      load()
    } catch (err) {
      toast.showWarning(mensagemFalhaParaToast(err, 'Não foi possível desativar.'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <ConfigListPageShell
      embedded={embedded}
      forbidden={forbidden}
      denied={<SemPermissao title="Só quem gerencia faturamento altera as contas bancárias." />}
      title="Contas bancárias"
      subtitle="Dados do cedente e token da conta no Boleto Cloud. Usados na emissão de boletos desta instância."
      actions={
        podeEditar ? (
          <Button type="button" onClick={abrirNovo} disabled={editando || busy}>
            Nova conta
          </Button>
        ) : null
      }
    >
      <div className="space-y-4">
        <Card title="Contas cadastradas">
          {loading ? (
            <p className="text-sm text-slate-500">Carregando…</p>
          ) : items.length === 0 && !editando ? (
            <p className="text-sm text-slate-500">
              Nenhuma conta ainda. Cadastre a conta bancária e o token gerado no Boleto Cloud.
            </p>
          ) : (
            <ul className="divide-y divide-slate-200 dark:divide-slate-700">
              {items.map((c) => (
                <li
                  key={c.id}
                  className="flex flex-wrap items-center justify-between gap-3 py-3 first:pt-0 last:pb-0"
                >
                  <div className="min-w-0 space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium text-slate-900 dark:text-slate-50">
                        {c.apelido}
                      </span>
                      {c.padrao ? (
                        <span className="rounded-full bg-sky-100 px-2 py-0.5 text-xs font-semibold text-sky-800 dark:bg-sky-950/40 dark:text-sky-200">
                          Padrão
                        </span>
                      ) : null}
                      <span
                        className={[
                          'rounded-full px-2 py-0.5 text-xs font-semibold',
                          c.ativo
                            ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-200'
                            : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300',
                        ].join(' ')}
                      >
                        {c.ativo ? 'Ativa' : 'Inativa'}
                      </span>
                      <span
                        className={[
                          'rounded-full px-2 py-0.5 text-xs font-semibold',
                          c.tem_token
                            ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-200'
                            : 'bg-amber-100 text-amber-800 dark:bg-amber-950/40 dark:text-amber-200',
                        ].join(' ')}
                      >
                        {c.tem_token ? 'Token OK' : 'Token pendente'}
                      </span>
                    </div>
                    <p className="text-xs text-slate-500">
                      {[c.banco_nome || c.banco_codigo, c.agencia, c.conta]
                        .filter(Boolean)
                        .join(' · ') || 'Sem dados bancários'}
                    </p>
                  </div>
                  {podeEditar ? (
                    <div className="flex flex-wrap gap-2">
                      <Button
                        type="button"
                        variant="secondary"
                        disabled={editando || busy}
                        onClick={() => abrirEdicao(c)}
                      >
                        Editar
                      </Button>
                      {c.ativo ? (
                        <Button
                          type="button"
                          variant="secondary"
                          disabled={editando || busy}
                          onClick={() => void desativar(c.id)}
                        >
                          Desativar
                        </Button>
                      ) : null}
                    </div>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </Card>

        {editando && podeEditar ? (
          <Card title={form.id == null ? 'Nova conta' : `Editar conta #${form.id}`}>
            <form onSubmit={(e) => void salvar(e)} className="grid gap-4 sm:grid-cols-2">
              <div className="sm:col-span-2">
                <Input
                  label="Apelido"
                  value={form.apelido}
                  onChange={(e) => setForm((f) => ({ ...f, apelido: e.target.value }))}
                  required
                  autoComplete="off"
                />
              </div>
              <Input
                label="Código do banco"
                value={form.bancoCodigo}
                onChange={(e) => setForm((f) => ({ ...f, bancoCodigo: e.target.value }))}
                autoComplete="off"
              />
              <Input
                label="Nome do banco"
                value={form.bancoNome}
                onChange={(e) => setForm((f) => ({ ...f, bancoNome: e.target.value }))}
                autoComplete="off"
              />
              <Input
                label="Agência"
                value={form.agencia}
                onChange={(e) => setForm((f) => ({ ...f, agencia: e.target.value }))}
                autoComplete="off"
              />
              <Input
                label="DV agência"
                value={form.agenciaDv}
                onChange={(e) => setForm((f) => ({ ...f, agenciaDv: e.target.value }))}
                autoComplete="off"
              />
              <Input
                label="Conta"
                value={form.conta}
                onChange={(e) => setForm((f) => ({ ...f, conta: e.target.value }))}
                autoComplete="off"
              />
              <Input
                label="DV conta"
                value={form.contaDv}
                onChange={(e) => setForm((f) => ({ ...f, contaDv: e.target.value }))}
                autoComplete="off"
              />
              <Input
                label="Carteira"
                value={form.carteira}
                onChange={(e) => setForm((f) => ({ ...f, carteira: e.target.value }))}
                autoComplete="off"
              />
              <Input
                label="Titular"
                value={form.titularNome}
                onChange={(e) => setForm((f) => ({ ...f, titularNome: e.target.value }))}
                autoComplete="off"
              />
              <Input
                label="Documento do titular"
                value={form.titularDocumento}
                onChange={(e) => setForm((f) => ({ ...f, titularDocumento: e.target.value }))}
                autoComplete="off"
              />
              <div className="sm:col-span-2">
                <Input
                  label={
                    form.temToken
                      ? 'Token Boleto Cloud (deixe em branco para manter)'
                      : 'Token Boleto Cloud'
                  }
                  type={mostrarToken ? 'text' : 'password'}
                  value={form.token}
                  onChange={(e) => setForm((f) => ({ ...f, token: e.target.value }))}
                  autoComplete="new-password"
                  placeholder={form.temToken ? '••••••••' : 'token da conta'}
                  endAdornment={
                    <button
                      type="button"
                      onClick={() => setMostrarToken((v) => !v)}
                      className="inline-flex size-9 items-center justify-center rounded-md text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400/30 dark:text-slate-400 dark:hover:bg-white/10 dark:hover:text-slate-200"
                      aria-label={mostrarToken ? 'Ocultar token' : 'Mostrar token'}
                      aria-pressed={mostrarToken}
                    >
                      {mostrarToken ? <IconEyeOff /> : <IconEye />}
                    </button>
                  }
                />
              </div>
              <div className="sm:col-span-2">
                <Input
                  label="Notas"
                  value={form.notas}
                  onChange={(e) => setForm((f) => ({ ...f, notas: e.target.value }))}
                  autoComplete="off"
                />
              </div>
              <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-200">
                <input
                  type="checkbox"
                  checked={form.ativo}
                  onChange={(e) => setForm((f) => ({ ...f, ativo: e.target.checked }))}
                  className="size-4 rounded border-slate-300"
                />
                Conta ativa
              </label>
              <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-200">
                <input
                  type="checkbox"
                  checked={form.padrao}
                  onChange={(e) => setForm((f) => ({ ...f, padrao: e.target.checked }))}
                  className="size-4 rounded border-slate-300"
                />
                Conta padrão para emissão
              </label>
              <div className="flex flex-wrap justify-end gap-2 sm:col-span-2">
                <Button type="button" variant="secondary" onClick={fecharForm} disabled={busy}>
                  Cancelar
                </Button>
                <Button type="submit" loading={busy}>
                  Salvar
                </Button>
              </div>
            </form>
          </Card>
        ) : null}
      </div>
    </ConfigListPageShell>
  )
}
