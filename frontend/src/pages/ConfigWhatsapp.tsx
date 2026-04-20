import { useCallback, useEffect, useState } from 'react'
import { QRCodeSVG } from 'qrcode.react'
import { whatsappSettings } from '../api/client'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { useToast } from '../components/ui/Toast'
import { mensagemFalhaParaToast } from '../api/errorMessage'

function renderQrPayload(data: Record<string, unknown> | null | undefined) {
  if (!data || typeof data !== 'object') return null
  const code = data.code
  if (typeof code === 'string' && code.length > 0) {
    return (
      <div className="flex justify-center rounded-lg bg-white p-4">
        <QRCodeSVG value={code} size={280} level="M" />
      </div>
    )
  }
  const raw = data.base64 ?? data.qrcode
  if (typeof raw === 'string') {
    if (raw.startsWith('data:image')) {
      return <img src={raw} alt="QR Code WhatsApp" className="mx-auto max-w-[280px] rounded-lg" />
    }
    if (raw.length > 80) {
      return (
        <img
          src={`data:image/png;base64,${raw}`}
          alt="QR Code WhatsApp"
          className="mx-auto max-w-[280px] rounded-lg"
        />
      )
    }
  }
  const pairing = data.pairingCode
  if (typeof pairing === 'string' && pairing.length > 0) {
    return (
      <p className="text-center font-mono text-lg tracking-widest text-slate-800 dark:text-slate-100">
        Código de pareamento: <span className="font-bold">{pairing}</span>
      </p>
    )
  }
  return (
    <pre className="max-h-56 overflow-auto rounded bg-slate-100 p-3 text-xs text-slate-800 dark:bg-slate-900 dark:text-slate-200">
      {JSON.stringify(data, null, 2)}
    </pre>
  )
}

export function ConfigWhatsapp() {
  const toast = useToast()
  const [loading, setLoading] = useState(true)
  const [flags, setFlags] = useState({
    evolution_embutida_disponivel: false,
  })
  const [qrPayload, setQrPayload] = useState<Record<string, unknown> | null>(null)
  const [provisionando, setProvisionando] = useState(false)

  const carregar = useCallback(async () => {
    setLoading(true)
    try {
      const r = await whatsappSettings.get()
      setFlags({
        evolution_embutida_disponivel: Boolean(r.evolution_embutida_disponivel),
      })
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível carregar as configurações.'))
    } finally {
      setLoading(false)
    }
  }, [toast])

  useEffect(() => {
    void carregar()
  }, [carregar])

  async function prepararEMostrarQr() {
    setProvisionando(true)
    try {
      const out = await whatsappSettings.provisionarEmbutido()
      const q = out.qrcode && typeof out.qrcode === 'object' ? (out.qrcode as Record<string, unknown>) : null
      setQrPayload(q)
      if (out.connect_erro) {
        toast.showWarning(`Provisionado; ao obter QR: ${out.connect_erro}. Use «Atualizar QR».`)
      } else {
        toast.showSuccess('Instância criada. Escaneie o QR Code com o WhatsApp no telemóvel.')
      }
      await carregar()
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Falha ao preparar a Evolution.'))
    } finally {
      setProvisionando(false)
    }
  }

  async function atualizarQr() {
    try {
      const q = await whatsappSettings.qrCode()
      setQrPayload(q)
      toast.showSuccess('QR atualizado.')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err))
    }
  }

  async function reporTudo() {
    if (!confirm('Apagar a instância na Evolution e limpar credenciais no DX Connect?')) return
    try {
      await whatsappSettings.reporEmbutido()
      setQrPayload(null)
      toast.showSuccess('Pode voltar a preparar a ligação.')
      await carregar()
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
        <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-100">WhatsApp · Evolution API</h1>
        <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
          A integração com o WhatsApp é feita pela{' '}
          <span className="font-medium text-slate-800 dark:text-slate-200">Evolution API</span>. O DX Connect usa-a
          para sessão, webhooks e envio de mensagens; aqui só gere o QR para associar o número ao atendimento.
        </p>
      </div>

      {flags.evolution_embutida_disponivel ? (
        <Card className="space-y-5 p-6 ring-1 ring-cyan-200/50 dark:ring-cyan-900/40">
          <div>
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Ligar o WhatsApp</h2>
            <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
              Carregue em «Preparar e mostrar QR Code» — a Evolution cria a sessão e regista o webhook. No telemóvel:
              WhatsApp → Aparelhos ligados → Ligar um aparelho → leia o QR. As mensagens aparecem em{' '}
              <span className="font-medium text-slate-700 dark:text-slate-300">Chat</span>.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button type="button" loading={provisionando} onClick={() => void prepararEMostrarQr()}>
              Preparar e mostrar QR Code
            </Button>
            <Button type="button" variant="secondary" onClick={() => void atualizarQr()}>
              Atualizar QR
            </Button>
            <Button type="button" variant="danger" onClick={() => void reporTudo()}>
              Desligar e recomeçar
            </Button>
          </div>
          {qrPayload && <div className="pt-1">{renderQrPayload(qrPayload)}</div>}
        </Card>
      ) : (
        <Card className="p-6 text-sm text-slate-600 dark:text-slate-400">
          <p className="font-medium text-slate-800 dark:text-slate-200">Pareamento por QR não disponível</p>
          <p className="mt-2 leading-relaxed">
            Neste servidor a Evolution API embutida não está configurada (variáveis de ambiente / Docker). Peça ao
            administrador que active o stack indicado na documentação do projeto para usar o fluxo por QR aqui.
          </p>
        </Card>
      )}
    </div>
  )
}
