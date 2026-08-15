import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ApiError, chatInterno } from '../../api/client'
import { chatInternoLink } from '../../lib/chatHubPaths'
import { useChatHub } from '../../contexts/ChatHubContext'
import { SemPermissao } from '../SemPermissao'

export function ChatInternoSetorCanal() {
  const { setorId: setorIdParam } = useParams()
  const setorId = Number(setorIdParam)
  const navigate = useNavigate()
  const { abrirChat } = useChatHub()
  const [forbidden, setForbidden] = useState(false)

  useEffect(() => {
    if (!Number.isFinite(setorId) || setorId <= 0) {
      navigate('/chat/interno', { replace: true })
      return
    }
    let cancelled = false
    ;(async () => {
      try {
        const canal = await chatInterno.obterCanalSetor(setorId)
        if (!cancelled) {
          abrirChat('interno', canal.id)
          navigate(chatInternoLink(), { replace: true })
        }
      } catch (err) {
        if (!cancelled && err instanceof ApiError && err.status === 403) {
          setForbidden(true)
          return
        }
        if (!cancelled) navigate('/chat/interno', { replace: true })
      }
    })()
    return () => {
      cancelled = true
    }
  }, [setorId, navigate, abrirChat])

  if (forbidden) {
    return (
      <div className="mx-auto max-w-3xl p-4">
        <SemPermissao
          title="Sem permissão para este canal"
          detail="Você não está vinculado a este setor."
          voltarPara="/chat/interno"
          voltarLabel="Voltar ao inbox"
        />
      </div>
    )
  }

  return (
    <div className="flex h-48 items-center justify-center text-sm text-slate-400 animate-pulse">
      Abrindo canal do setor…
    </div>
  )
}
