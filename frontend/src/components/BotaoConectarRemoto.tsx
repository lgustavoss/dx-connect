import { useRef, useState, type MouseEvent, type ReactNode } from 'react'
import { conectarAcessoRemoto, urlConexaoDeskRudder } from '../lib/acessoRemotoConectar'
import { isDeskRudderDesktop } from '../lib/deskrudderDesktop'
import { IconeConectarRemoto } from './IconeConectarRemoto'
import { useToast } from './ui/Toast'

const ICONE_CLASS =
  'inline-flex size-8 items-center justify-center rounded-md text-slate-500 transition hover:bg-slate-100 hover:text-slate-800 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-slate-100'

const BOTAO_CLASS =
  'inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-slate-100 px-4 text-sm font-medium text-slate-800 hover:bg-slate-200 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-2 dark:bg-slate-800 dark:text-slate-100 dark:hover:bg-slate-700'

type ResultadoSenha = { senha: string | null; avisou: boolean }
type CacheSenha = { pronta: boolean } & ResultadoSenha

type Props = {
  rustdeskId: string
  carregarSenha?: () => Promise<ResultadoSenha>
  onAviso?: () => void
  title?: string
  ariaLabel?: string
  variant?: 'icone' | 'botao'
  className?: string
  children?: ReactNode
}

/** Conectar: link real `deskrudder://` — clique sintético em âncora criada via JS o Chrome ignora. */
export function BotaoConectarRemoto({
  rustdeskId,
  carregarSenha,
  onAviso,
  title = 'Conectar',
  ariaLabel,
  variant = 'icone',
  className = '',
  children,
}: Props) {
  const toast = useToast()
  const [senha, setSenha] = useState<string | null>(null)
  const [abrindo, setAbrindo] = useState(false)
  const cacheRef = useRef<CacheSenha>({
    pronta: !carregarSenha,
    senha: null,
    avisou: false,
  })
  const inflightRef = useRef<Promise<CacheSenha> | null>(null)

  function garantirSenha(): Promise<CacheSenha> {
    if (cacheRef.current.pronta || !carregarSenha) {
      return Promise.resolve(cacheRef.current)
    }
    if (!inflightRef.current) {
      inflightRef.current = carregarSenha().then((r) => {
        const cache: CacheSenha = { pronta: true, senha: r.senha, avisou: r.avisou }
        cacheRef.current = cache
        setSenha(r.senha)
        return cache
      })
    }
    return inflightRef.current
  }

  function toastNativo(cache: CacheSenha) {
    onAviso?.()
    if (!cache.avisou) {
      toast.showSuccess(
        cache.senha
          ? 'Acesso remoto aberto com o ID e a senha do cadastro (janela DeskRudder - Acesso Remoto).'
          : 'Acesso remoto aberto com este ID (janela DeskRudder - Acesso Remoto).',
      )
    }
  }

  function abrirViaJs() {
    setAbrindo(true)
    void (async () => {
      try {
        onAviso?.()
        const r = await garantirSenha()
        await conectarAcessoRemoto(rustdeskId, r.senha, toast, r.avisou)
      } finally {
        setAbrindo(false)
      }
    })()
  }

  function aoClicar(e: MouseEvent<HTMLAnchorElement>) {
    if (abrindo) {
      e.preventDefault()
      return
    }
    if (isDeskRudderDesktop()) {
      e.preventDefault()
      abrirViaJs()
      return
    }
    // Senha já no cache (hover/pointerdown): o href do React pode estar atrasado.
    // Atualiza o alvo no próprio gesto e deixa o Chrome seguir o <a>.
    if (cacheRef.current.pronta) {
      e.currentTarget.href = urlConexaoDeskRudder(rustdeskId, cacheRef.current.senha)
      toastNativo(cacheRef.current)
      return
    }
    e.preventDefault()
    abrirViaJs()
  }

  const href = urlConexaoDeskRudder(rustdeskId, senha)
  const base = variant === 'botao' ? BOTAO_CLASS : ICONE_CLASS
  const rotulo = ariaLabel ?? title
  const conteudo =
    children ??
    (variant === 'icone' ? <IconeConectarRemoto /> : abrindo ? 'Abrindo…' : 'Conectar')

  return (
    <a
      href={href}
      title={title}
      aria-label={rotulo}
      aria-busy={abrindo || undefined}
      className={`${base} ${abrindo ? 'pointer-events-none opacity-40' : ''} ${className}`.trim()}
      onPointerDown={() => void garantirSenha()}
      onPointerEnter={() => void garantirSenha()}
      onFocus={() => void garantirSenha()}
      onClick={aoClicar}
    >
      {abrindo && variant === 'icone' ? (
        <span className="size-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />
      ) : (
        conteudo
      )}
    </a>
  )
}
