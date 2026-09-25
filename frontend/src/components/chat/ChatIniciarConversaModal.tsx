import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { setores, whatsappChats, type Setores, type WhatsappChats } from '../../api/client'
import { coletarTodasPaginas } from '../../api/collectPages'
import { Button } from '../../components/ui/Button'
import { Input, TEXTAREA_FIELD_CLASS } from '../../components/ui/Input'
import { SelectComPesquisa } from '../../components/ui/SelectComPesquisa'
import { useToast } from '../../components/ui/Toast'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { chatWhatsappLink } from '../../lib/chatHubPaths'
import { gravarChatAtivoSession } from '../../lib/chatAtivo'
import { useChatHubOpcional } from '../../contexts/ChatHubContext'
import { useAuth } from '../../contexts/AuthContext'

type Props = {
  open: boolean
  onClose: () => void
  contato?: WhatsappChats.Contato | null
  /** Número pré-preenchido (retomar / avulso) */
  telefoneInicial?: string | null
  funcionarioId?: number | null
  /** Empresas do funcionário (retomar histórico / chat com vínculo) */
  empresas?: WhatsappChats.EmpresaOpcao[] | null
  titulo?: string
}

export function ChatIniciarConversaModal({
  open,
  onClose,
  contato,
  telefoneInicial,
  funcionarioId,
  empresas,
  titulo,
}: Props) {
  const toast = useToast()
  const navigate = useNavigate()
  const hub = useChatHubOpcional()
  const { user } = useAuth()
  const [telefone, setTelefone] = useState('')
  const [mensagem, setMensagem] = useState('')
  const [empresaId, setEmpresaId] = useState<number | ''>('')
  const [setorId, setSetorId] = useState<number | ''>('')
  const [setoresLista, setSetoresLista] = useState<Setores.Setor[]>([])
  const [carregandoSetores, setCarregandoSetores] = useState(false)
  const [erroCargaSetores, setErroCargaSetores] = useState(false)
  const [salvando, setSalvando] = useState(false)

  const empresasLista = useMemo(() => {
    if (contato?.empresas?.length) return contato.empresas
    if (empresas?.length) return empresas
    return []
  }, [contato, empresas])

  const multiEmpresa = empresasLista.length > 1
  const precisaTelefone = !(contato?.telefone || telefoneInicial)
  const setorIds = user?.setor_ids ?? []
  const escolherSetor = setorIds.length > 1

  const setoresOpcoes = useMemo(() => {
    const ids = new Set(setorIds)
    return setoresLista
      .filter((s) => ids.has(s.id) && s.ativo !== false)
      .sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'))
  }, [setoresLista, setorIds])

  useEffect(() => {
    if (!open) return
    setTelefone(contato?.telefone || telefoneInicial || '')
    setMensagem('')
    setSetorId('')
    if (empresasLista.length === 1) {
      setEmpresaId(empresasLista[0].id)
    } else {
      setEmpresaId('')
    }
  }, [open, contato, telefoneInicial, empresasLista])

  useEffect(() => {
    if (!open || !escolherSetor) return
    let cancelado = false
    setCarregandoSetores(true)
    setErroCargaSetores(false)
    void coletarTodasPaginas<Setores.Setor>((o, l) =>
      setores.list({ incluir_inativos: false, offset: o, limit: l }),
    )
      .then((items) => {
        if (!cancelado) setSetoresLista(items)
      })
      .catch(() => {
        if (!cancelado) {
          setSetoresLista([])
          setErroCargaSetores(true)
        }
      })
      .finally(() => {
        if (!cancelado) setCarregandoSetores(false)
      })
    return () => {
      cancelado = true
    }
  }, [open, escolherSetor])

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
    if (escolherSetor && setorId === '') {
      toast.showWarning('Selecione o setor deste atendimento.')
      return
    }
    setSalvando(true)
    try {
      const chat = await whatsappChats.iniciar({
        funcionario_id: fid ?? undefined,
        telefone: digits || undefined,
        mensagem_inicial: mensagem.trim() || undefined,
        empresa_id: empresaId === '' ? undefined : Number(empresaId),
        setor_id: setorId === '' ? undefined : Number(setorId),
      })
      onClose()
      if (hub) hub.abrirChat('whatsapp', chat.id)
      else gravarChatAtivoSession({ canal: 'whatsapp', id: chat.id })
      navigate(chatWhatsappLink('contatos'))
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
          {titulo || (contato ? `Contactar ${contato.nome}` : 'Novo contato WhatsApp')}
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
          {multiEmpresa && (
            <div className="space-y-1">
              <SelectComPesquisa
                label="Empresa do atendimento (opcional)"
                value={empresaId}
                onChange={(id) => setEmpresaId(id)}
                items={empresasLista.map((e) => ({ id: e.id, label: e.nome }))}
                placeholder="Definir depois na conversa"
                hint="Digite parte do nome do posto"
                menuPlacement="inline"
              />
              <p className="text-[11px] text-slate-500">
                Se ainda não souber, pergunte ao cliente na conversa e vincule a empresa a qualquer
                momento antes de encerrar.
              </p>
            </div>
          )}
          {escolherSetor && (
            <div className="space-y-2">
              <p className="text-sm font-medium text-slate-700 dark:text-slate-200">Setor</p>
              <p className="text-[11px] text-slate-500">
                Você atende em mais de um setor. O nome escolhido aparece na assinatura enviada ao
                cliente.
              </p>
              <div role="radiogroup" aria-label="Setor do atendimento" className="flex flex-col gap-2">
                {carregandoSetores ? (
                  <p className="text-sm text-slate-500">Carregando setores…</p>
                ) : erroCargaSetores ? (
                  <p className="text-sm text-red-600 dark:text-red-400">
                    Não foi possível carregar os setores. Feche e tente de novo.
                  </p>
                ) : setoresOpcoes.length === 0 ? (
                  <p className="text-sm text-amber-700 dark:text-amber-300">
                    Nenhum setor ativo encontrado no seu vínculo. Peça a um admin para rever os setores
                    do seu usuário.
                  </p>
                ) : (
                  setoresOpcoes.map((s) => {
                    const selected = setorId === s.id
                    return (
                      <button
                        key={s.id}
                        type="button"
                        role="radio"
                        aria-checked={selected}
                        disabled={salvando}
                        onClick={() => setSetorId(s.id)}
                        className={`flex min-h-11 w-full items-center rounded-xl px-3 py-2.5 text-left text-sm ${
                          selected
                            ? 'bg-slate-900 font-medium text-white dark:bg-cyan-600'
                            : 'bg-slate-50 text-slate-800 ring-1 ring-slate-200 hover:bg-slate-100 dark:bg-slate-800/60 dark:text-slate-100 dark:ring-slate-700'
                        }`}
                      >
                        {s.nome}
                      </button>
                    )
                  })
                )}
              </div>
            </div>
          )}
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
          <Button type="button" variant="cancel" onClick={onClose} disabled={salvando}>
            Cancelar
          </Button>
          <Button
            type="button"
            onClick={() => void confirmar()}
            loading={salvando}
            disabled={
              escolherSetor &&
              (setorId === '' || carregandoSetores || erroCargaSetores || setoresOpcoes.length === 0)
            }
          >
            Iniciar conversa
          </Button>
        </div>
      </div>
    </div>
  )
}
