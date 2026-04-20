import { useEffect, useState } from 'react'
import { whatsappSettings, type WhatsappSettings } from '../api/client'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { useToast } from '../components/ui/Toast'
import { mensagemFalhaParaToast } from '../api/errorMessage'

export function ConfigWhatsapp() {
  const toast = useToast()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [baseUrl, setBaseUrl] = useState('')
  const [instance, setInstance] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [webhookSecret, setWebhookSecret] = useState('')
  const [flags, setFlags] = useState({ has_api_key: false, has_webhook_secret: false })

  useEffect(() => {
    ;(async () => {
      setLoading(true)
      try {
        const r = await whatsappSettings.get()
        setBaseUrl(r.evolution_base_url || '')
        setInstance(r.evolution_instance_name || '')
        setFlags({ has_api_key: r.has_api_key, has_webhook_secret: r.has_webhook_secret })
        setApiKey('')
        setWebhookSecret('')
      } catch (err) {
        toast.showError(mensagemFalhaParaToast(err, 'Não foi possível carregar as configurações.'))
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  async function salvar(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      const patch: WhatsappSettings.Update = {
        evolution_base_url: baseUrl.trim() || null,
        evolution_instance_name: instance.trim() || null,
      }
      if (apiKey.trim()) patch.evolution_api_key = apiKey.trim()
      if (webhookSecret.trim()) patch.webhook_secret = webhookSecret.trim()
      const r = await whatsappSettings.patch(patch)
      setFlags({ has_api_key: r.has_api_key, has_webhook_secret: r.has_webhook_secret })
      setApiKey('')
      setWebhookSecret('')
      toast.showSuccess('Configurações salvas.')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err))
    } finally {
      setSaving(false)
    }
  }

  async function testar() {
    try {
      const r = await whatsappSettings.testar()
      if (r.ok) {
        toast.showSuccess('Conexão com a Evolution API OK.')
      } else {
        toast.showWarning(r.detalhe || 'Falha no teste de conexão.')
      }
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err))
    }
  }

  if (loading) {
    return <p className="text-slate-500 dark:text-slate-400">Carregando…</p>
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6 pb-10">
      <div>
        <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-100">WhatsApp (Evolution API)</h1>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
          Credenciais da instância Evolution. A API key não é exibida após salvar — informe novamente apenas para alterar.
        </p>
      </div>

      <Card className="p-6">
        <form onSubmit={salvar} className="space-y-4">
          <div>
            <label className="text-sm font-medium text-slate-700 dark:text-slate-300">URL base da Evolution</label>
            <Input
              className="mt-1"
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              placeholder="https://evolution.seudominio.com"
              autoComplete="off"
            />
          </div>
          <div>
            <label className="text-sm font-medium text-slate-700 dark:text-slate-300">Nome da instância</label>
            <Input
              className="mt-1"
              value={instance}
              onChange={(e) => setInstance(e.target.value)}
              placeholder="ex.: dx-connect"
              autoComplete="off"
            />
          </div>
          <div>
            <label className="text-sm font-medium text-slate-700 dark:text-slate-300">API key</label>
            <Input
              className="mt-1"
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder={flags.has_api_key ? '•••••••• (deixe em branco para manter)' : 'Obrigatória na primeira configuração'}
              autoComplete="new-password"
            />
          </div>
          <div>
            <label className="text-sm font-medium text-slate-700 dark:text-slate-300">Segredo do webhook (opcional)</label>
            <Input
              className="mt-1"
              type="password"
              value={webhookSecret}
              onChange={(e) => setWebhookSecret(e.target.value)}
              placeholder={
                flags.has_webhook_secret
                  ? '•••••••• (deixe em branco para manter)'
                  : 'Recomendado: mesmo valor no header X-Dx-Webhook-Secret ou apikey na Evolution'
              }
              autoComplete="new-password"
            />
          </div>
          <div className="flex flex-wrap gap-2 pt-2">
            <Button type="submit" loading={saving}>
              Salvar
            </Button>
            <Button type="button" variant="secondary" onClick={() => void testar()}>
              Testar conexão
            </Button>
          </div>
        </form>
      </Card>

      <Card className="p-4 text-sm text-slate-600 dark:text-slate-400">
        <p className="font-medium text-slate-800 dark:text-slate-200">Webhook na Evolution</p>
        <p className="mt-2">
          URL de callback: <code className="rounded bg-slate-100 px-1 dark:bg-slate-800">POST /v1/webhooks/evolution</code>{' '}
          (host completo da API DX Connect + esse path).
        </p>
        <p className="mt-2">Consulte também o ficheiro de documentação no repositório: docs/WHATSAPP_EVOLUTION.md</p>
      </Card>
    </div>
  )
}
