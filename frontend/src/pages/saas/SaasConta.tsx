import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  atendentes,
  saasOpsConta,
  ApiError,
  persistAuthTokens,
  type SaasOpsConta,
} from '../../api/client'
import { interpretarFalhaCarregamento, mensagemFalhaParaToast } from '../../api/errorMessage'
import { Button } from '../../components/ui/Button'
import { CadastroFormPageShell } from '../../components/ui/CadastroFormPageShell'
import { Card } from '../../components/ui/Card'
import { CarregamentoFalhou } from '../../components/ui/CarregamentoFalhou'
import { ConfirmDialog } from '../../components/ui/ConfirmDialog'
import { IconEye, IconEyeOff } from '../../components/ui/IconEye'
import { Input } from '../../components/ui/Input'
import { useToast } from '../../components/ui/Toast'
import { useAuth } from '../../contexts/AuthContext'
import { useVoltarAnterior } from '../../hooks/useVoltarAnterior'
import { SemPermissao } from '../SemPermissao'
import { SAAS_LICENCAS_PATH } from '../../lib/saasControlPlane'

function formatWhen(iso: string | null | undefined): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
  } catch {
    return iso
  }
}

export function SaasConta() {
  const toast = useToast()
  const { user, refreshUser } = useAuth()
  const voltarAnterior = useVoltarAnterior(SAAS_LICENCAS_PATH)

  const [loading, setLoading] = useState(true)
  const [busyPerfil, setBusyPerfil] = useState(false)
  const [busySenha, setBusySenha] = useState(false)
  const [busyToken, setBusyToken] = useState(false)
  const [forbidden, setForbidden] = useState(false)
  const [indisponivel, setIndisponivel] = useState(false)
  const [falha, setFalha] = useState<{ titulo: string; detalhe?: string } | null>(null)
  const [estado, setEstado] = useState<SaasOpsConta.McpEstado | null>(null)
  const [plaintext, setPlaintext] = useState<string | null>(null)
  const [confirmarGerar, setConfirmarGerar] = useState(false)
  const [confirmarRevogar, setConfirmarRevogar] = useState(false)

  const [nome, setNome] = useState('')
  const [email, setEmail] = useState('')

  const [senhaAtual, setSenhaAtual] = useState('')
  const [senhaNova, setSenhaNova] = useState('')
  const [senhaConf, setSenhaConf] = useState('')
  const [mostrarAtual, setMostrarAtual] = useState(false)
  const [mostrarNova, setMostrarNova] = useState(false)
  const [mostrarConf, setMostrarConf] = useState(false)

  useEffect(() => {
    if (!user) return
    setNome(user.nome ?? '')
    setEmail(user.email ?? '')
  }, [user])

  const carregar = useCallback(() => {
    setLoading(true)
    setForbidden(false)
    setIndisponivel(false)
    setFalha(null)
    saasOpsConta
      .mcpToken()
      .then(setEstado)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 403) {
          setForbidden(true)
          return
        }
        if (err instanceof ApiError && err.status === 404) {
          setIndisponivel(true)
          return
        }
        setFalha(interpretarFalhaCarregamento(err, 'Não foi possível carregar a conta.'))
      })
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    carregar()
  }, [carregar])

  async function salvarPerfil(e: React.FormEvent) {
    e.preventDefault()
    if (!nome.trim() || !email.trim()) {
      toast.showError('Informe nome e e-mail.')
      return
    }
    setBusyPerfil(true)
    try {
      const row = await saasOpsConta.atualizarPerfil({
        nome: nome.trim(),
        email: email.trim(),
      })
      if (row.access_token) {
        persistAuthTokens({
          access_token: row.access_token,
          refresh_token: row.refresh_token,
        })
      }
      setNome(row.nome)
      setEmail(row.email)
      await refreshUser()
      toast.showSuccess('Dados da conta atualizados.')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível salvar os dados.'))
    } finally {
      setBusyPerfil(false)
    }
  }

  async function salvarSenha(e: React.FormEvent) {
    e.preventDefault()
    if (senhaNova.length < 8) {
      toast.showError('A nova senha deve ter pelo menos 8 caracteres.')
      return
    }
    if (senhaNova !== senhaConf) {
      toast.showError('A confirmação não coincide com a nova senha.')
      return
    }
    setBusySenha(true)
    try {
      await atendentes.trocarSenha(senhaAtual, senhaNova)
      setSenhaAtual('')
      setSenhaNova('')
      setSenhaConf('')
      await refreshUser()
      toast.showSuccess('Senha alterada.')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível alterar a senha.'))
    } finally {
      setBusySenha(false)
    }
  }

  async function gerar() {
    setBusyToken(true)
    try {
      const row = await saasOpsConta.gerarMcpToken()
      setEstado({ configurado: row.configurado, gerado_em: row.gerado_em })
      setPlaintext(row.token)
      toast.showSuccess(
        estado?.configurado
          ? 'Token regenerado. O anterior deixa de funcionar no Cursor.'
          : 'Token gerado. Copie agora — não vamos mostrar de novo.',
      )
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível gerar o token.'))
    } finally {
      setBusyToken(false)
      setConfirmarGerar(false)
    }
  }

  async function revogar() {
    setBusyToken(true)
    try {
      const row = await saasOpsConta.revogarMcpToken()
      setEstado(row)
      setPlaintext(null)
      toast.showSuccess('Token Cursor revogado.')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível revogar o token.'))
    } finally {
      setBusyToken(false)
      setConfirmarRevogar(false)
    }
  }

  async function copiar() {
    if (!plaintext) return
    try {
      await navigator.clipboard.writeText(plaintext)
      toast.showSuccess('Token copiado.')
    } catch {
      toast.showError('Não foi possível copiar. Selecione o token e copie manualmente.')
    }
  }

  if (forbidden) {
    return (
      <SemPermissao
        title="Conta exclusiva da equipe SaaS."
        detail="Entre com a conta ops em /login/admin."
        voltarPara="/login/admin"
        voltarLabel="Voltar ao login admin"
      />
    )
  }
  if (indisponivel) {
    return (
      <SemPermissao
        title="Painel SaaS não disponível nesta instância."
        detail="A conta e o token Cursor só existem no control-plane DeskRudder."
        voltarPara="/login/admin"
        voltarLabel="Voltar ao login admin"
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
      <Card title="Dados da conta" description="Nome e e-mail usados no login do painel admin (/login/admin).">
        <form onSubmit={(ev) => void salvarPerfil(ev)} className="space-y-4">
          <Input label="Nome" value={nome} onChange={(ev) => setNome(ev.target.value)} required />
          <Input
            label="E-mail"
            type="email"
            value={email}
            onChange={(ev) => setEmail(ev.target.value)}
            required
            autoComplete="username"
          />
          <div className="flex justify-end">
            <Button type="submit" loading={busyPerfil}>
              Salvar dados
            </Button>
          </div>
        </form>
      </Card>

      <Card title="Alterar senha" description="Informe a senha atual e defina uma nova (mínimo 8 caracteres).">
        <form onSubmit={(ev) => void salvarSenha(ev)} className="space-y-4" noValidate>
          <Input
            label="Senha atual"
            type={mostrarAtual ? 'text' : 'password'}
            value={senhaAtual}
            onChange={(ev) => setSenhaAtual(ev.target.value)}
            autoComplete="current-password"
            required
            endAdornment={
              <button
                type="button"
                onClick={() => setMostrarAtual((v) => !v)}
                className="inline-flex size-9 items-center justify-center rounded-md text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400/30 dark:text-slate-400 dark:hover:bg-white/10 dark:hover:text-slate-200"
                aria-label={mostrarAtual ? 'Ocultar senha atual' : 'Mostrar senha atual'}
                aria-pressed={mostrarAtual}
              >
                {mostrarAtual ? <IconEyeOff ariaHidden={false} /> : <IconEye ariaHidden={false} />}
              </button>
            }
          />
          <Input
            label="Nova senha"
            type={mostrarNova ? 'text' : 'password'}
            value={senhaNova}
            onChange={(ev) => setSenhaNova(ev.target.value)}
            autoComplete="new-password"
            minLength={8}
            required
            endAdornment={
              <button
                type="button"
                onClick={() => setMostrarNova((v) => !v)}
                className="inline-flex size-9 items-center justify-center rounded-md text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400/30 dark:text-slate-400 dark:hover:bg-white/10 dark:hover:text-slate-200"
                aria-label={mostrarNova ? 'Ocultar nova senha' : 'Mostrar nova senha'}
                aria-pressed={mostrarNova}
              >
                {mostrarNova ? <IconEyeOff ariaHidden={false} /> : <IconEye ariaHidden={false} />}
              </button>
            }
          />
          <Input
            label="Confirmar nova senha"
            type={mostrarConf ? 'text' : 'password'}
            value={senhaConf}
            onChange={(ev) => setSenhaConf(ev.target.value)}
            autoComplete="new-password"
            minLength={8}
            required
            endAdornment={
              <button
                type="button"
                onClick={() => setMostrarConf((v) => !v)}
                className="inline-flex size-9 items-center justify-center rounded-md text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400/30 dark:text-slate-400 dark:hover:bg-white/10 dark:hover:text-slate-200"
                aria-label={mostrarConf ? 'Ocultar confirmação' : 'Mostrar confirmação'}
                aria-pressed={mostrarConf}
              >
                {mostrarConf ? <IconEyeOff ariaHidden={false} /> : <IconEye ariaHidden={false} />}
              </button>
            }
          />
          <div className="flex justify-end">
            <Button type="submit" loading={busySenha}>
              Alterar senha
            </Button>
          </div>
        </form>
      </Card>

      <Card
        title="Integração Cursor"
        description="O token identifica a sua conta ops nas sugestões (recusar, comentar, ligar issue). Cada pessoa gera o próprio. Novas contas são criadas em Usuários."
      >
        {loading || !estado ? (
          <p className="text-sm text-slate-500">Carregando…</p>
        ) : (
          <div className="space-y-4">
            <p className="text-sm text-slate-600 dark:text-slate-400">
              {estado.configurado
                ? `Token ativo. Gerado em ${formatWhen(estado.gerado_em)}.`
                : 'Ainda não há token nesta conta.'}{' '}
              <Link to="/saas/usuarios" className="font-medium text-sky-700 underline dark:text-sky-300">
                Gerenciar equipe
              </Link>
            </p>
            {plaintext ? (
              <div className="space-y-2">
                <label htmlFor="mcp-token-plain" className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                  Copie agora — não vamos mostrar o valor completo de novo
                </label>
                <textarea
                  id="mcp-token-plain"
                  readOnly
                  value={plaintext}
                  rows={3}
                  className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 font-mono text-xs text-slate-800 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
                />
                <Button type="button" variant="secondary" onClick={() => void copiar()}>
                  Copiar token
                </Button>
                <p className="text-xs text-slate-500">
                  No Cursor: <code className="rounded bg-slate-100 px-1 dark:bg-slate-800">.cursor/mcp.json</code> →{' '}
                  <code className="rounded bg-slate-100 px-1 dark:bg-slate-800">DESKRUDDER_MCP_TOKEN</code>. Depois
                  Settings → MCP → habilitar deskrudder-saas.
                </p>
              </div>
            ) : null}
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                loading={busyToken}
                onClick={() => {
                  if (estado.configurado) {
                    setConfirmarGerar(true)
                    return
                  }
                  void gerar()
                }}
              >
                {estado.configurado ? 'Regenerar token' : 'Gerar token'}
              </Button>
              {estado.configurado ? (
                <Button type="button" variant="danger" loading={busyToken} onClick={() => setConfirmarRevogar(true)}>
                  Revogar
                </Button>
              ) : null}
            </div>
          </div>
        )}
      </Card>

      <ConfirmDialog
        open={confirmarGerar}
        title="Regenerar token Cursor?"
        message="O token que está no Cursor deixa de funcionar. Você terá de colar o novo valor no mcp.json."
        confirmLabel="Regenerar"
        variant="danger"
        loading={busyToken}
        onConfirm={() => void gerar()}
        onCancel={() => setConfirmarGerar(false)}
      />
      <ConfirmDialog
        open={confirmarRevogar}
        title="Revogar token Cursor?"
        message="O Cursor deixa de autenticar nesta conta até gerar um token novo."
        confirmLabel="Revogar"
        variant="danger"
        loading={busyToken}
        onConfirm={() => void revogar()}
        onCancel={() => setConfirmarRevogar(false)}
      />
      </div>
    </CadastroFormPageShell>
  )
}
