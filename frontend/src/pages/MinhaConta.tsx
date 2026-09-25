import { useEffect, useState } from 'react'
import { atendentes, setores } from '../api/client'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { IconEye, IconEyeOff } from '../components/ui/IconEye'
import { Input } from '../components/ui/Input'
import { useToast } from '../components/ui/Toast'
import { useAuth } from '../contexts/AuthContext'
import { mensagemFalhaParaToast } from '../api/errorMessage'

function rotuloPerfil(role: string | undefined): string {
  if (role === 'admin') return 'Administrador'
  if (role === 'atendente') return 'Atendente'
  if (role === 'comercial') return 'Comercial'
  if (role === 'saas_ops') return 'Ops SaaS'
  return role?.trim() || '—'
}

export function MinhaConta() {
  const { user, refreshUser } = useAuth()
  const toast = useToast()
  const [nomesSetor, setNomesSetor] = useState<string[]>([])
  const [carregandoSetores, setCarregandoSetores] = useState(false)
  const [erroSetores, setErroSetores] = useState(false)
  const [tentativaSetores, setTentativaSetores] = useState(0)
  const [senhaAtual, setSenhaAtual] = useState('')
  const [senhaNova, setSenhaNova] = useState('')
  const [senhaConf, setSenhaConf] = useState('')
  const [mostrarAtual, setMostrarAtual] = useState(false)
  const [mostrarNova, setMostrarNova] = useState(false)
  const [mostrarConf, setMostrarConf] = useState(false)
  const [busySenha, setBusySenha] = useState(false)

  const setorIds = user?.setor_ids ?? []
  const setorKey = setorIds.join(',')

  useEffect(() => {
    const ids = setorKey ? setorKey.split(',').map((id) => Number(id)) : []
    if (ids.length === 0) {
      setNomesSetor([])
      setErroSetores(false)
      setCarregandoSetores(false)
      return
    }
    let ativo = true
    setCarregandoSetores(true)
    setErroSetores(false)
    setores
      .list({ limit: 100, incluir_inativos: true })
      .then((pagina) => {
        if (!ativo) return
        const porId = new Map(pagina.items.map((s) => [s.id, s.nome]))
        setNomesSetor(ids.map((id) => porId.get(id)).filter((nome): nome is string => Boolean(nome)))
      })
      .catch(() => {
        if (!ativo) return
        setNomesSetor([])
        setErroSetores(true)
      })
      .finally(() => {
        if (ativo) setCarregandoSetores(false)
      })
    return () => {
      ativo = false
    }
  }, [setorKey, tentativaSetores])

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
      toast.showSuccess('Senha alterada. Você continua conectado.')
    } catch (err) {
      toast.showError(mensagemFalhaParaToast(err, 'Não foi possível alterar a senha.'))
    } finally {
      setBusySenha(false)
    }
  }

  return (
    <div className="mx-auto w-full min-w-0 max-w-2xl space-y-4">
      <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-100">Minha conta</h1>

      <Card title="Seus dados" description="Informações da conta com a qual você entrou. Para alterar perfil ou setores, fale com um administrador.">
        <dl className="space-y-3 text-sm">
          <div>
            <dt className="text-slate-500 dark:text-slate-400">Nome</dt>
            <dd className="font-medium text-slate-900 dark:text-slate-100">{user?.nome || '—'}</dd>
          </div>
          <div>
            <dt className="text-slate-500 dark:text-slate-400">E-mail</dt>
            <dd className="font-medium text-slate-900 dark:text-slate-100">{user?.email || '—'}</dd>
          </div>
          <div>
            <dt className="text-slate-500 dark:text-slate-400">Perfil</dt>
            <dd className="font-medium text-slate-900 dark:text-slate-100">{rotuloPerfil(user?.role)}</dd>
          </div>
          {setorIds.length > 0 ? (
            <div>
              <dt className="text-slate-500 dark:text-slate-400">Setores</dt>
              <dd
                className={
                  erroSetores
                    ? 'text-red-600 dark:text-red-400'
                    : 'font-medium text-slate-900 dark:text-slate-100'
                }
              >
                {carregandoSetores ? (
                  <span className="font-normal text-slate-500 dark:text-slate-400">Carregando setores…</span>
                ) : erroSetores ? (
                  <>
                    Não foi possível carregar os setores.{' '}
                    <button
                      type="button"
                      className="font-medium underline"
                      onClick={() => setTentativaSetores((n) => n + 1)}
                    >
                      Tentar de novo
                    </button>
                  </>
                ) : nomesSetor.length > 0 ? (
                  nomesSetor.join(', ')
                ) : (
                  '—'
                )}
              </dd>
            </div>
          ) : null}
        </dl>
      </Card>

      <Card title="Alterar senha" description="Informe a senha atual e defina uma nova, com pelo menos 8 caracteres. A sessão atual permanece.">
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
              Salvar senha
            </Button>
          </div>
        </form>
      </Card>
    </div>
  )
}
