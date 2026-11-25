import { useCallback, useEffect, useState } from 'react'
import {
  ApiError,
  saasBoletoCloud,
  type SaasBoletoCloud,
} from '../../api/client'
import { interpretarFalhaCarregamento, mensagemFalhaParaToast } from '../../api/errorMessage'
import { Button } from '../../components/ui/Button'
import { CadastroFormPageShell } from '../../components/ui/CadastroFormPageShell'
import { Card } from '../../components/ui/Card'
import { CarregamentoFalhou } from '../../components/ui/CarregamentoFalhou'
import { IconEye, IconEyeOff } from '../../components/ui/IconEye'
import { Input } from '../../components/ui/Input'
import { useToast } from '../../components/ui/Toast'
import { useVoltarAnterior } from '../../hooks/useVoltarAnterior'
import { SemPermissao } from '../SemPermissao'
import { SAAS_LICENCAS_PATH } from '../../lib/saasControlPlane'

const URL_SANDBOX = 'https://sandbox.boletocloud.com/api/v1'

type FormState = {
  id: number | null
  apelido: string
  emailLogin: string
  apiBaseUrl: string
  faixaTeto: string
  notas: string
  ativo: boolean
  apiKey: string
  temApiKey: boolean
}

const FORM_VAZIO: FormState = {
  id: null,
  apelido: '',
  emailLogin: '',
  apiBaseUrl: URL_SANDBOX,
  faixaTeto: '',
  notas: '',
  ativo: true,
  apiKey: '',
  temApiKey: false,
}

function selo(ok: boolean, labelOk: string, labelOff: string) {
  return (
    <span
      className={[
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold',
        ok
          ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-200'
          : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300',
      ].join(' ')}
    >
      {ok ? labelOk : labelOff}
    </span>
  )
}

function poolParaForm(p: SaasBoletoCloud.Pool): FormState {
  return {
    id: p.id,
    apelido: p.apelido,
    emailLogin: p.email_login || '',
    apiBaseUrl: p.api_base_url || URL_SANDBOX,
    faixaTeto: p.faixa_teto != null ? String(p.faixa_teto) : '',
    notas: p.notas || '',
    ativo: p.ativo,
    apiKey: '',
    temApiKey: p.tem_api_key,
  }
}

export function SaasCobranca() {
  const toast = useToast()
  const voltarAnterior = useVoltarAnterior(SAAS_LICENCAS_PATH)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [busyTeste, setBusyTeste] = useState(false)
  const [forbidden, setForbidden] = useState(false)
  const [falha, setFalha] = useState<{ titulo: string; detalhe?: string } | null>(null)
  const [pools, setPools] = useState<SaasBoletoCloud.Pool[]>([])
  const [form, setForm] = useState<FormState>(FORM_VAZIO)
  const [mostrarKey, setMostrarKey] = useState(false)
  const [editando, setEditando] = useState(false)

  const carregar = useCallback(() => {
    setLoading(true)
    setForbidden(false)
    setFalha(null)
    saasBoletoCloud
      .listarPools()
      .then((lista) => {
        setPools(lista.items)
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 403) {
          setForbidden(true)
          return
        }
        if (err instanceof ApiError && err.status === 404) {
          setFalha({
            titulo: 'Cobrança indisponível nesta instância.',
            detalhe: 'Ative SAAS_CONTROL_PLANE no backend do control-plane.',
          })
          return
        }
        setFalha(interpretarFalhaCarregamento(err, 'Não foi possível carregar os pools.'))
      })
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    carregar()
  }, [carregar])

  function abrirNovo() {
    setForm(FORM_VAZIO)
    setEditando(true)
    setMostrarKey(false)
  }

  function abrirEdicao(p: SaasBoletoCloud.Pool) {
    setForm(poolParaForm(p))
    setEditando(true)
    setMostrarKey(false)
  }

  function fecharForm() {
    setEditando(false)
    setForm(FORM_VAZIO)
    setMostrarKey(false)
  }

  async function salvar(e: React.FormEvent) {
    e.preventDefault()
    if (!form.apelido.trim()) {
      toast.showError('Informe o apelido do pool.')
      return
    }
    if (!form.apiBaseUrl.trim().startsWith('https://')) {
      toast.showError('A URL base deve começar com https://')
      return
    }
    if (form.id == null && !form.apiKey.trim()) {
      toast.showError('Informe a API Key no cadastro do pool.')
      return
    }
    const faixa =
      form.faixaTeto.trim() === '' ? null : Number.parseInt(form.faixaTeto.trim(), 10)
    if (form.faixaTeto.trim() !== '' && (!Number.isFinite(faixa) || (faixa ?? 0) < 1)) {
      toast.showError('O teto da faixa deve ser um número inteiro positivo.')
      return
    }
    const body: SaasBoletoCloud.PoolUpsert = {
      apelido: form.apelido.trim(),
      email_login: form.emailLogin.trim() || null,
      api_base_url: form.apiBaseUrl.trim().replace(/\/$/, ''),
      faixa_teto: faixa,
      notas: form.notas.trim() || null,
      ativo: form.ativo,
      api_key: form.apiKey.trim() || null,
    }
    setBusy(true)
    try {
      if (form.id == null) {
        await saasBoletoCloud.criarPool(body)
        toast.showSuccess('Pool criado.')
      } else {
        await saasBoletoCloud.atualizarPool(form.id, body)
        toast.showSuccess('Pool atualizado.')
      }
      fecharForm()
      carregar()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err))
    } finally {
      setBusy(false)
    }
  }

  async function testar(poolId: number) {
    setBusyTeste(true)
    try {
      const r = await saasBoletoCloud.testarPool(poolId)
      if (r.ok) toast.showSuccess(r.mensagem)
      else toast.showError(r.mensagem)
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err))
    } finally {
      setBusyTeste(false)
    }
  }

  if (forbidden) {
    return (
      <SemPermissao
        title="Sem permissão para configurar cobrança."
        detail="É preciso conta Ops SaaS no painel admin."
        voltarPara={SAAS_LICENCAS_PATH}
        voltarLabel="Voltar às licenças"
      />
    )
  }

  if (falha) {
    return (
      <CarregamentoFalhou
        titulo={falha.titulo}
        detalhe={falha.detalhe}
        onVoltar={carregar}
        voltarLabel="Tentar novamente"
      />
    )
  }

  return (
    <CadastroFormPageShell onVoltar={voltarAnterior}>
      <div className="space-y-4">
        <Card
          title="Pools Boleto Cloud"
          description="Cada pool é uma conta (API Key) no Boleto Cloud. Vincule clientes às licenças; boletos já emitidos ficam na conta de origem se o cliente mudar de pool."
        >
          <div className="mb-4 flex flex-wrap justify-end gap-2">
            <Button type="button" onClick={abrirNovo} disabled={editando}>
              Novo pool
            </Button>
          </div>

          {loading ? (
            <p className="text-sm text-slate-500">Carregando…</p>
          ) : pools.length === 0 && !editando ? (
            <p className="text-sm text-slate-500">
              Nenhum pool cadastrado. Crie o primeiro com a API Key da conta no Boleto Cloud.
            </p>
          ) : (
            <ul className="divide-y divide-slate-200 dark:divide-slate-700">
              {pools.map((p) => (
                <li
                  key={p.id}
                  className="flex flex-wrap items-center justify-between gap-3 py-3 first:pt-0 last:pb-0"
                >
                  <div className="min-w-0 space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium text-slate-900 dark:text-slate-50">
                        {p.apelido}
                      </span>
                      {selo(p.tem_api_key, 'API Key OK', 'API Key pendente')}
                      {selo(p.ativo, 'Ativo', 'Inativo')}
                    </div>
                    <p className="text-xs text-slate-500">
                      {p.clientes_vinculados} cliente(s) vinculado(s)
                      {p.faixa_teto != null ? ` · teto ${p.faixa_teto}` : ''}
                      {p.email_login ? ` · ${p.email_login}` : ''}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      type="button"
                      variant="secondary"
                      loading={busyTeste}
                      disabled={!p.tem_api_key || !p.ativo}
                      onClick={() => void testar(p.id)}
                    >
                      Testar
                    </Button>
                    <Button
                      type="button"
                      variant="secondary"
                      disabled={editando}
                      onClick={() => abrirEdicao(p)}
                    >
                      Editar
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Card>

        {editando ? (
          <Card
            title={form.id == null ? 'Novo pool' : `Editar pool #${form.id}`}
            description="A API Key fica cifrada no control-plane e não é enviada às instâncias dos clientes."
          >
            <form onSubmit={(e) => void salvar(e)} className="space-y-4">
              <Input
                label="Apelido"
                value={form.apelido}
                onChange={(e) => setForm((f) => ({ ...f, apelido: e.target.value }))}
                placeholder="pool-a-sandbox"
                autoComplete="off"
                required
              />
              <Input
                label="E-mail de login (opcional)"
                value={form.emailLogin}
                onChange={(e) => setForm((f) => ({ ...f, emailLogin: e.target.value }))}
                placeholder="conta@boletocloud.com"
                autoComplete="off"
              />
              <Input
                label="URL base da API"
                value={form.apiBaseUrl}
                onChange={(e) => setForm((f) => ({ ...f, apiBaseUrl: e.target.value }))}
                placeholder={URL_SANDBOX}
                autoComplete="off"
                required
              />
              <Input
                label="Teto da faixa (boletos/mês)"
                value={form.faixaTeto}
                onChange={(e) => setForm((f) => ({ ...f, faixaTeto: e.target.value }))}
                placeholder="1000"
                inputMode="numeric"
                autoComplete="off"
              />
              <Input
                label={
                  form.temApiKey
                    ? 'API Key (deixe em branco para manter)'
                    : 'API Key'
                }
                type={mostrarKey ? 'text' : 'password'}
                value={form.apiKey}
                onChange={(e) => setForm((f) => ({ ...f, apiKey: e.target.value }))}
                autoComplete="new-password"
                placeholder={form.temApiKey ? '••••••••' : 'api-key_…'}
                endAdornment={
                  <button
                    type="button"
                    onClick={() => setMostrarKey((v) => !v)}
                    className="inline-flex size-9 items-center justify-center rounded-md text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400/30 dark:text-slate-400 dark:hover:bg-white/10 dark:hover:text-slate-200"
                    aria-label={mostrarKey ? 'Ocultar API Key' : 'Mostrar API Key'}
                    aria-pressed={mostrarKey}
                  >
                    {mostrarKey ? <IconEyeOff /> : <IconEye />}
                  </button>
                }
              />
              <Input
                label="Notas"
                value={form.notas}
                onChange={(e) => setForm((f) => ({ ...f, notas: e.target.value }))}
                placeholder="Observações internas"
                autoComplete="off"
              />
              <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-200">
                <input
                  type="checkbox"
                  checked={form.ativo}
                  onChange={(e) => setForm((f) => ({ ...f, ativo: e.target.checked }))}
                  className="size-4 rounded border-slate-300"
                />
                Pool ativo
              </label>
              <div className="flex flex-wrap justify-end gap-2">
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
    </CadastroFormPageShell>
  )
}
