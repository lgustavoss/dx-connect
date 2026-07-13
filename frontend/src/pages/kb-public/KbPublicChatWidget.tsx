import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties } from 'react'

import { fetchPortalPublicMidiaBlob, kbPublic, type Kb } from '../../api/client'

import { ChatMensagemMidia } from '../../components/chat/ChatMensagemMidia'

import { useKbPublicBranding } from './KbPublicContext'



const LS_TOKEN = 'dxconnect.kb.portal.visitor_token'

const LS_NOME = 'dxconnect.kb.portal.visitor_nome'



type Fase = 'fechado' | 'form' | 'chat'



function brandingVars(b: Kb.PublicBranding): CSSProperties {

  return {

    backgroundColor: b.cor_fundo,

    color: b.cor_texto_corpo,

    ['--kb-chat-header' as string]: b.cor_header,

    ['--kb-chat-header-text' as string]: b.cor_texto_header,

    ['--kb-chat-accent' as string]: b.cor_primaria,

    ['--kb-chat-body' as string]: b.cor_texto_corpo,

    ['--kb-chat-bg' as string]: b.cor_fundo,

  }

}



export function KbPublicChatWidget() {

  const branding = useKbPublicBranding()

  const vars = useMemo(() => brandingVars(branding), [branding])

  const [fase, setFase] = useState<Fase>('fechado')

  const [token, setToken] = useState<string | null>(null)

  const [nome, setNome] = useState('')

  const [email, setEmail] = useState('')

  const [sessao, setSessao] = useState<Kb.PortalChatPublicSession | null>(null)

  const [texto, setTexto] = useState('')

  const [loading, setLoading] = useState(false)

  const [enviando, setEnviando] = useState(false)

  const [erro, setErro] = useState<string | null>(null)

  const fimRef = useRef<HTMLDivElement>(null)

  const lastMsgIdRef = useRef(0)

  const fileInputRef = useRef<HTMLInputElement>(null)



  const abrir = useCallback(() => {

    setFase((f) => (f === 'fechado' ? 'form' : f))

    setErro(null)

  }, [])



  const restaurar = useCallback(async (savedToken: string) => {

    setLoading(true)

    try {

      const data = await kbPublic.obterChat(savedToken)

      if (data.estado === 'encerrado') {

        localStorage.removeItem(LS_TOKEN)

        setFase('form')

        return

      }

      setToken(savedToken)

      setSessao(data)

      setNome(data.visitante_nome)

      lastMsgIdRef.current = data.mensagens.at(-1)?.id ?? 0

      setFase('chat')

    } catch {

      localStorage.removeItem(LS_TOKEN)

      setFase('form')

    } finally {

      setLoading(false)

    }

  }, [])



  useEffect(() => {

    if (!branding.chat_habilitado) return

    const saved = localStorage.getItem(LS_TOKEN)

    const savedNome = localStorage.getItem(LS_NOME)

    if (savedNome) setNome(savedNome)

    if (saved) void restaurar(saved)

  }, [branding.chat_habilitado, restaurar])



  useEffect(() => {

    fimRef.current?.scrollIntoView({ behavior: 'smooth' })

  }, [sessao?.mensagens, sessao?.estado])



  useEffect(() => {

    if (fase !== 'chat' || !token) return

    const timer = setInterval(() => {

      void (async () => {

        try {

          const [sessaoAtual, novas] = await Promise.all([

            kbPublic.obterChat(token),

            kbPublic.listarMensagensChat(token, lastMsgIdRef.current || undefined),

          ])

          setSessao((prev) => {

            const mergedMsgs =

              novas.length > 0

                ? [...(prev?.mensagens ?? []), ...novas.filter((n) => !(prev?.mensagens ?? []).some((m) => m.id === n.id))]

                : (prev?.mensagens ?? sessaoAtual.mensagens)

            if (novas.length > 0) lastMsgIdRef.current = novas[novas.length - 1].id

            return {

              protocolo: sessaoAtual.protocolo,

              estado: sessaoAtual.estado,

              visitante_nome: sessaoAtual.visitante_nome,

              mensagens: mergedMsgs,

            }

          })

        } catch {

          /* silencioso */

        }

      })()

    }, 4000)

    return () => clearInterval(timer)

  }, [fase, token])



  async function iniciar(e: React.FormEvent) {

    e.preventDefault()

    const n = nome.trim()

    if (!n) {

      setErro('Informe seu nome.')

      return

    }

    setLoading(true)

    setErro(null)

    try {

      const data = await kbPublic.iniciarChat(

        { visitante_nome: n, visitante_email: email.trim() || null },

        token,

      )

      localStorage.setItem(LS_TOKEN, data.visitor_token)

      localStorage.setItem(LS_NOME, n)

      setToken(data.visitor_token)

      setSessao({

        protocolo: data.chat.protocolo,

        estado: data.chat.estado,

        visitante_nome: data.chat.visitante_nome,

        mensagens: data.mensagens,

      })

      lastMsgIdRef.current = data.mensagens.at(-1)?.id ?? 0

      setFase('chat')

    } catch (err) {

      setErro(err instanceof Error ? err.message : 'Não foi possível iniciar o chat.')

    } finally {

      setLoading(false)

    }

  }



  async function enviar(corpo?: string) {

    if (!token) return

    const textoEnvio = (corpo ?? texto).trim()

    if (!textoEnvio) return

    setEnviando(true)

    try {

      const msg = await kbPublic.enviarMensagemChat(token, textoEnvio)

      lastMsgIdRef.current = msg.id

      const refreshed = await kbPublic.obterChat(token)

      setSessao(refreshed)

      lastMsgIdRef.current = refreshed.mensagens.at(-1)?.id ?? msg.id

      setTexto('')

    } catch (err) {

      setErro(err instanceof Error ? err.message : 'Não foi possível enviar.')

    } finally {

      setEnviando(false)

    }

  }



  async function enviarArquivo(file: File) {

    if (!token) return

    setEnviando(true)

    try {

      const msg = await kbPublic.enviarMidiaChat(token, file)

      lastMsgIdRef.current = msg.id

      const refreshed = await kbPublic.obterChat(token)

      setSessao(refreshed)

      lastMsgIdRef.current = refreshed.mensagens.at(-1)?.id ?? msg.id

    } catch (err) {

      setErro(err instanceof Error ? err.message : 'Não foi possível enviar o anexo.')

    } finally {

      setEnviando(false)

    }

  }



  if (!branding.chat_habilitado) return null



  const inputClass =

    'w-full rounded-lg border border-black/15 bg-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[var(--kb-chat-accent)]/40'



  const aguardandoAtendente = sessao?.estado === 'aguardando_atendente'

  const aguardandoAvaliacao = sessao?.estado === 'aguardando_avaliacao'

  const encerrado = sessao?.estado === 'encerrado'

  const podeEnviar = sessao?.estado === 'em_atendimento' || aguardandoAvaliacao



  return (

    <div className="pointer-events-none fixed bottom-4 right-4 z-50 flex flex-col items-end gap-3">

      {fase !== 'fechado' ? (

        <div

          className="pointer-events-auto flex w-[min(100vw-2rem,22rem)] flex-col overflow-hidden rounded-2xl border border-black/10 shadow-2xl"

          style={{ ...vars, maxHeight: 'min(70vh, 32rem)' }}

        >

          <header

            className="flex items-center gap-3 border-b border-black/10 px-3 py-2.5"

            style={{ backgroundColor: branding.cor_header, color: branding.cor_texto_header }}

          >

            {branding.logo_url ? (

              <img

                src={kbPublic.logoAssetUrl()}

                alt=""

                className="h-9 max-h-9 w-auto max-w-[5.5rem] shrink-0 object-contain object-left"

              />

            ) : null}

            <div className="min-w-0 flex-1">

              <p className="truncate text-sm font-semibold leading-tight">{branding.nome_exibicao}</p>

              <p className="truncate text-[11px] opacity-90">

                {sessao?.protocolo ? `${sessao.protocolo} · Fale conosco` : 'Fale conosco'}

              </p>

            </div>

            <button

              type="button"

              className="shrink-0 rounded p-1.5 transition-colors hover:bg-white/10"

              style={{ color: branding.cor_texto_header }}

              onClick={() => setFase('fechado')}

              aria-label="Fechar chat"

            >

              ✕

            </button>

          </header>



          {fase === 'form' ? (

            <form onSubmit={(e) => void iniciar(e)} className="space-y-3 p-4" style={{ color: branding.cor_texto_corpo }}>

              <p className="text-sm opacity-90">

                {branding.texto_boas_vindas?.trim() || 'Converse com nossa equipe em tempo real.'}

              </p>

              <input

                value={nome}

                onChange={(e) => setNome(e.target.value)}

                placeholder="Seu nome"

                className={inputClass}

                style={{ color: branding.cor_texto_corpo }}

              />

              <input

                value={email}

                onChange={(e) => setEmail(e.target.value)}

                type="email"

                placeholder="E-mail (opcional)"

                className={inputClass}

                style={{ color: branding.cor_texto_corpo }}

              />

              {erro ? <p className="text-xs text-red-600">{erro}</p> : null}

              <button

                type="submit"

                disabled={loading}

                className="w-full rounded-lg px-3 py-2 text-sm font-semibold text-white disabled:opacity-60"

                style={{ backgroundColor: branding.cor_primaria }}

              >

                {loading ? 'Conectando…' : 'Iniciar chat'}

              </button>

            </form>

          ) : null}



          {fase === 'chat' && sessao ? (

            <>

              <div className="min-h-0 flex-1 overflow-y-auto px-3 py-3" style={{ backgroundColor: branding.cor_fundo }}>

                {aguardandoAtendente ? (

                  <p className="mb-2 text-center text-xs text-amber-800">Aguardando um atendente…</p>

                ) : null}

                <div className="flex flex-col gap-2">

                  {sessao.mensagens.map((m) => {

                    const visitante = m.direcao === 'inbound'

                    return (

                      <div key={m.id} className={`flex ${visitante ? 'justify-end' : 'justify-start'}`}>

                        <div

                          className={`max-w-[90%] rounded-2xl px-3 py-2 text-sm ${

                            visitante ? 'text-white' : 'border border-black/10 bg-white shadow-sm'

                          }`}

                          style={

                            visitante

                              ? { backgroundColor: branding.cor_primaria }

                              : { color: branding.cor_texto_corpo }

                          }

                        >

                          {!visitante && m.atendente_nome ? (

                            <p className="mb-0.5 text-[10px] font-semibold opacity-60">{m.atendente_nome}</p>

                          ) : null}

                          <ChatMensagemMidia

                            mensagem={m}

                            fetchMidia={() => fetchPortalPublicMidiaBlob(token!, m.id)}

                          />

                        </div>

                      </div>

                    )

                  })}

                  <div ref={fimRef} />

                </div>

              </div>



              {aguardandoAvaliacao ? (

                <div className="border-t border-black/10 p-3" style={{ backgroundColor: branding.cor_fundo }}>

                  <p className="mb-2 text-center text-xs font-medium">Como você avalia o atendimento?</p>

                  <div className="flex justify-center gap-2">

                    {[1, 2, 3, 4, 5].map((nota) => (

                      <button

                        key={nota}

                        type="button"

                        disabled={enviando}

                        onClick={() => void enviar(String(nota))}

                        className="flex size-9 items-center justify-center rounded-full border border-black/15 bg-white text-sm font-bold hover:bg-black/5 disabled:opacity-50"

                        style={{ color: branding.cor_texto_corpo }}

                      >

                        {nota}

                      </button>

                    ))}

                  </div>

                </div>

              ) : encerrado ? (

                <p className="border-t border-black/10 px-3 py-2 text-center text-xs opacity-70">

                  Atendimento encerrado.

                </p>

              ) : (

                <form

                  onSubmit={(e) => {

                    e.preventDefault()

                    void enviar()

                  }}

                  className="flex gap-2 border-t border-black/10 p-3"

                  style={{ backgroundColor: branding.cor_fundo }}

                >

                  {podeEnviar && sessao.estado === 'em_atendimento' ? (

                    <>

                      <input

                        ref={fileInputRef}

                        type="file"

                        accept="image/*,audio/*,video/*,.pdf,.doc,.docx"

                        className="hidden"

                        onChange={(e) => {

                          const file = e.target.files?.[0]

                          if (file) void enviarArquivo(file)

                          e.target.value = ''

                        }}

                      />

                      <button

                        type="button"

                        className="shrink-0 rounded-lg border border-black/15 px-2 text-lg"

                        onClick={() => fileInputRef.current?.click()}

                        disabled={enviando}

                        aria-label="Anexar ficheiro"

                      >

                        📎

                      </button>

                    </>

                  ) : null}

                  <input

                    value={texto}

                    onChange={(e) => setTexto(e.target.value)}

                    placeholder={aguardandoAvaliacao ? 'Digite uma nota de 1 a 5…' : 'Digite sua mensagem…'}

                    disabled={!podeEnviar}

                    className={`min-w-0 flex-1 ${inputClass}`}

                    style={{ color: branding.cor_texto_corpo }}

                  />

                  <button

                    type="submit"

                    disabled={enviando || !podeEnviar || !texto.trim()}

                    className="shrink-0 rounded-lg px-3 py-2 text-sm font-semibold text-white disabled:opacity-60"

                    style={{ backgroundColor: branding.cor_primaria }}

                  >

                    Enviar

                  </button>

                </form>

              )}

            </>

          ) : null}

        </div>

      ) : null}



      <button

        type="button"

        onClick={abrir}

        className="pointer-events-auto flex size-14 items-center justify-center rounded-full text-white shadow-lg transition-transform hover:scale-105"

        style={{ backgroundColor: branding.cor_header }}

        aria-label="Abrir chat ao vivo"

      >

        <svg className="size-7" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>

          <path

            strokeLinecap="round"

            strokeLinejoin="round"

            strokeWidth={2}

            d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"

          />

        </svg>

      </button>

    </div>

  )

}


