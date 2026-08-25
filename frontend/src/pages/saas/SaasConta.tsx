import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { saasOpsConta, ApiError, type SaasOpsConta } from '../../api/client'
import { interpretarFalhaCarregamento, mensagemFalhaParaToast } from '../../api/errorMessage'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { CarregamentoFalhou } from '../../components/ui/CarregamentoFalhou'
import { ConfirmDialog } from '../../components/ui/ConfirmDialog'
import { useToast } from '../../components/ui/Toast'
import { VoltarButton } from '../../components/ui/VoltarButton'
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
  const voltarAnterior = useVoltarAnterior(SAAS_LICENCAS_PATH)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [forbidden, setForbidden] = useState(false)
  const [indisponivel, setIndisponivel] = useState(false)
  const [falha, setFalha] = useState<{ titulo: string; detalhe?: string } | null>(null)
  const [estado, setEstado] = useState<SaasOpsConta.McpEstado | null>(null)
  const [plaintext, setPlaintext] = useState<string | null>(null)
  const [confirmarGerar, setConfirmarGerar] = useState(false)
  const [confirmarRevogar, setConfirmarRevogar] = useState(false)

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

  async function gerar() {
    setBusy(true)
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
      setBusy(false)
      setConfirmarGerar(false)
    }
  }

  async function revogar() {
    setBusy(true)
    try {
      const row = await saasOpsConta.revogarMcpToken()
      setEstado(row)
      setPlaintext(null)
      toast.showSuccess('Token Cursor revogado.')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível revogar o token.'))
    } finally {
      setBusy(false)
      setConfirmarRevogar(false)
    }
  }

  async function copiar() {
    if (!plaintext) return
    try {
      await navigator.clipboard.writeText(plaintext)
      toast.showSuccess('Token copiado.')
    } catch {
      toast.showError('Não foi possível copiar. Seleccione o token e copie manualmente.')
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
        detail="O token Cursor só existe no control-plane DeskRudder."
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
    <div className="mx-auto max-w-2xl space-y-4">
      <VoltarButton onClick={voltarAnterior} />
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
                Gerir equipe
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
                loading={busy}
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
                <Button type="button" variant="danger" loading={busy} onClick={() => setConfirmarRevogar(true)}>
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
        message="O token que está no Cursor deixa de funcionar. Terá de colar o novo valor no mcp.json."
        confirmLabel="Regenerar"
        variant="danger"
        loading={busy}
        onConfirm={() => void gerar()}
        onCancel={() => setConfirmarGerar(false)}
      />
      <ConfirmDialog
        open={confirmarRevogar}
        title="Revogar token Cursor?"
        message="O Cursor deixa de autenticar nesta conta até gerar um token novo."
        confirmLabel="Revogar"
        variant="danger"
        loading={busy}
        onConfirm={() => void revogar()}
        onCancel={() => setConfirmarRevogar(false)}
      />
    </div>
  )
}
