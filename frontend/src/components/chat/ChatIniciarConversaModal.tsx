import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { whatsappChats, type WhatsappChats } from '../../api/client'
import { Button } from '../../components/ui/Button'
import { Input, TEXTAREA_FIELD_CLASS } from '../../components/ui/Input'
import { useToast } from '../../components/ui/Toast'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { chatWhatsappLink } from '../../lib/chatHubPaths'

type Props = {
  open: boolean
  onClose: () => void
  contato?: WhatsappChats.Contato | null
  /** Número pré-preenchido (retomar / avulso) */
  telefoneInicial?: string | null
  funcionarioId?: number | null
  titulo?: string
}

export function ChatIniciarConversaModal({
  open,
  onClose,
  contato,
  telefoneInicial,
  funcionarioId,
  titulo,
}: Props) {
  const toast = useToast()
  const navigate = useNavigate()
  const [telefone, setTelefone] = useState('')
  const [mensagem, setMensagem] = useState('')
  const [salvando, setSalvando] = useState(false)

  const precisaTelefone = !(contato?.telefone || telefoneInicial)

  useEffect(() => {
    if (!open) return
    setTelefone(contato?.telefone || telefoneInicial || '')
    setMensagem('')
  }, [open, contato, telefoneInicial])

  if (!open) return null

  async function confirmar() {
    const digits = telefone.replace(/\D/g, '')
    const fid = funcionarioId ?? contato?.id ?? null
    if (!fid && !digits) {
      toast.showWarning('Informe o número WhatsApp.')
      return
    }
    if (precisaTelefone && !digits) {
      toast.showWarning('Informe o número WhatsApp do contato.')
      return
    }
    setSalvando(true)
    try {
      const chat = await whatsappChats.iniciar({
        funcionario_id: fid ?? undefined,
        telefone: digits || undefined,
        mensagem_inicial: mensagem.trim() || undefined,
      })
      onClose()
      navigate(chatWhatsappLink(chat.id, 'contatos'))
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível iniciar a conversa.'))
    } finally {
      setSalvando(false)
    }
  }

  return (
    <div className="fixed inset-0 z-[120] flex items-end justify-center bg-black/50 p-4 sm:items-center" onClick={onClose}>
      <div
        className="w-full max-w-md rounded-2xl bg-white p-5 shadow-xl dark:bg-slate-900"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal
        aria-labelledby="iniciar-chat-titulo"
      >
        <h2 id="iniciar-chat-titulo" className="text-lg font-bold text-slate-900 dark:text-white">
          {titulo || (contato ? `Contactar ${contato.nome}` : 'Novo contacto WhatsApp')}
        </h2>
        {contato && (
          <p className="mt-1 text-xs text-slate-500">
            {contato.empresas.map((e) => e.nome).join(' · ') || contato.rede_nome || 'Sem empresa'}
          </p>
        )}

        <div className="mt-4 space-y-3">
          <Input
            label="WhatsApp"
            value={telefone}
            onChange={(e) => setTelefone(e.target.value)}
            placeholder="5511999999999"
          />
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-200">
            Mensagem inicial (opcional)
            <textarea
              value={mensagem}
              onChange={(e) => setMensagem(e.target.value)}
              rows={3}
              className={`mt-1 ${TEXTAREA_FIELD_CLASS}`}
              placeholder="Ex.: Olá, retorno sobre a sua demanda…"
            />
          </label>
        </div>

        <div className="mt-5 flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose} disabled={salvando}>
            Cancelar
          </Button>
          <Button type="button" onClick={() => void confirmar()} loading={salvando}>
            Iniciar conversa
          </Button>
        </div>
      </div>
    </div>
  )
}
