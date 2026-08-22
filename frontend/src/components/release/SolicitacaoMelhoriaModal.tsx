import { useEffect, useState } from 'react'
import { solicitacoesMelhoria, type SolicitacoesMelhoria } from '../../api/client'
import { mensagemFalhaParaToast } from '../../api/errorMessage'
import { Button } from '../ui/Button'
import { Input, TEXTAREA_FIELD_CLASS } from '../ui/Input'
import { Select } from '../ui/Select'
import { useToast } from '../ui/Toast'

type Props = {
  open: boolean
  versaoContexto?: string | null
  onClose: () => void
  onCriado?: (id: number) => void
}

/** Formulário para enviar sugestão / relatar problema a partir dos Release Notes (#802). */
export function SolicitacaoMelhoriaModal({ open, versaoContexto, onClose, onCriado }: Props) {
  const toast = useToast()
  const [tipo, setTipo] = useState<SolicitacoesMelhoria.Tipo>('sugestao')
  const [titulo, setTitulo] = useState('')
  const [descricao, setDescricao] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setTipo('sugestao')
    setTitulo('')
    setDescricao('')
    setErro(null)
  }, [open])

  if (!open) return null

  async function enviar() {
    setErro(null)
    const t = titulo.trim()
    const d = descricao.trim()
    if (t.length < 3) {
      setErro('Indique um título com pelo menos 3 caracteres.')
      return
    }
    if (d.length < 10) {
      setErro('Descreva o pedido com pelo menos 10 caracteres.')
      return
    }
    setEnviando(true)
    try {
      const row = await solicitacoesMelhoria.criar({
        tipo,
        titulo: t,
        descricao: d,
        versao_contexto: versaoContexto || null,
      })
      toast.showSuccess('Pedido enviado. Pode acompanhar em Minhas solicitações.')
      onCriado?.(row.id)
      onClose()
    } catch (err) {
      const msg = mensagemFalhaParaToast(err, 'Não foi possível enviar o pedido.')
      setErro(msg)
      toast.showError(msg)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-4 sm:items-center" role="dialog" aria-modal>
      <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl bg-white p-5 shadow-xl dark:bg-slate-900">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-50">Enviar sugestão ou relatar problema</h2>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Conte-nos o que gostaria de ver melhorado. A equipa analisa e responde pelo acompanhamento do pedido.
        </p>

        <div className="mt-4 space-y-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Tipo</label>
            <Select
              value={tipo}
              onChange={(v) => setTipo(String(v) as SolicitacoesMelhoria.Tipo)}
              options={[
                { value: 'sugestao', label: 'Sugestão de melhoria' },
                { value: 'problema', label: 'Relatar problema' },
              ]}
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Título</label>
            <Input value={titulo} onChange={(e) => setTitulo(e.target.value)} placeholder="Resumo em poucas palavras" maxLength={200} />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-300">Descrição</label>
            <textarea
              className={TEXTAREA_FIELD_CLASS}
              rows={5}
              value={descricao}
              onChange={(e) => setDescricao(e.target.value)}
              placeholder="Explique o contexto, o que esperava e o impacto no dia a dia."
              maxLength={8000}
            />
          </div>
          {erro ? <p className="text-sm text-rose-600 dark:text-rose-400">{erro}</p> : null}
        </div>

        <div className="mt-5 flex justify-end gap-2">
          <Button type="button" variant="cancel" onClick={onClose} disabled={enviando}>
            Cancelar
          </Button>
          <Button type="button" variant="primary" loading={enviando} onClick={() => void enviar()}>
            Enviar
          </Button>
        </div>
      </div>
    </div>
  )
}
