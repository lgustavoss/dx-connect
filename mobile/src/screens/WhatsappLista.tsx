import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
  type ScrollViewInstance,
} from 'react-native'
import { useRouter } from 'expo-router'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { ApiError, type WhatsappChat, whatsapp } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { Avatar } from '../components/Avatar'
import { EmptyState } from '../components/EmptyState'
import { Icon } from '../components/Icon'
import { SegTabs } from '../components/SegTabs'
import { StatusChip } from '../components/StatusChip'
import { useRealtimeRefresh } from '../hooks/useRealtimeRefresh'
import { type Cores } from '../lib/brand'
import { horaCurta, nomeDoChat } from '../lib/format'
import { useCores } from '../lib/tema'

type Aba = 'fila' | 'atendendo' | 'recentes'

const ABAS: Aba[] = ['fila', 'atendendo', 'recentes']
const PAGINA_RECENTES = 10

export function WhatsappLista() {
  const router = useRouter()
  const insets = useSafeAreaInsets()
  const { me } = useAuth()
  const cores = useCores()
  const styles = usarEstilos()
  const [aba, setAba] = useState<Aba>('fila')
  const [fila, setFila] = useState<WhatsappChat[]>([])
  const [meus, setMeus] = useState<WhatsappChat[]>([])
  const [recentes, setRecentes] = useState<WhatsappChat[]>([])
  const [recentesTotal, setRecentesTotal] = useState(0)
  const [erro, setErro] = useState<string | null>(null)
  const [aCarregar, setACarregar] = useState(true)
  const [aAtualizar, setAAtualizar] = useState(false)
  const [aCarregarMais, setACarregarMais] = useState(false)
  const geracao = useRef(0)
  const recentesLimitRef = useRef(PAGINA_RECENTES)
  const pagerRef = useRef<ScrollViewInstance | null>(null)
  const [largura, setLargura] = useState(0)
  const [altura, setAltura] = useState(0)

  const carregar = useCallback(async (silencioso = false) => {
    const id = ++geracao.current
    if (!silencioso) {
      setACarregar(true)
      recentesLimitRef.current = PAGINA_RECENTES
    }
    try {
      const filaMeus = Promise.all([whatsapp.fila(), whatsapp.meus()])
      const encerradosP = silencioso
        ? null
        : whatsapp
            .encerrados(0, PAGINA_RECENTES)
            .catch(() => ({ items: [] as WhatsappChat[], total: 0 }))
      const [f, m] = await filaMeus
      const r = encerradosP ? await encerradosP : null
      if (id !== geracao.current) return
      setFila(f)
      setMeus(m)
      if (r) {
        const itens = r.items || []
        setRecentes(itens)
        setRecentesTotal(r.total ?? itens.length)
        recentesLimitRef.current = itens.length
      }
      setErro(null)
    } catch (e) {
      if (id !== geracao.current) return
      if (!silencioso) {
        setErro(e instanceof ApiError ? e.message : 'Não foi possível carregar os chats.')
      }
    } finally {
      if (!silencioso) setACarregar(false)
      if (id === geracao.current) setAAtualizar(false)
    }
  }, [])

  const carregarMaisRecentes = useCallback(async () => {
    if (aCarregarMais) return
    setACarregarMais(true)
    try {
      const r = await whatsapp.encerrados(recentes.length, PAGINA_RECENTES)
      const extra = r.items || []
      setRecentes((prev) => {
        const next = [...prev, ...extra]
        recentesLimitRef.current = next.length
        return next
      })
      setRecentesTotal(r.total ?? recentes.length + extra.length)
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : 'Não foi possível carregar mais chats.')
    } finally {
      setACarregarMais(false)
    }
  }, [aCarregarMais, recentes.length])

  useEffect(() => {
    void carregar()
  }, [carregar])

  useEffect(() => {
    if (largura > 0) {
      pagerRef.current?.scrollTo({ x: ABAS.indexOf(aba) * largura, animated: false })
    }
  }, [largura])

  const refreshSilencioso = useCallback(() => {
    void carregar(true)
  }, [carregar])
  useRealtimeRefresh(refreshSilencioso, true)

  const { comigo, outros, mostrarSecoes } = useMemo(() => {
    const uid = me?.id
    const comigoLista = meus.filter((c) => c.atendente_id === uid)
    const outrosLista = meus.filter((c) => c.atendente_id !== uid)
    return {
      comigo: comigoLista,
      outros: outrosLista,
      mostrarSecoes: outrosLista.length > 0,
    }
  }, [meus, me?.id])

  const conteudoAba = (p: Aba) => {
    const lista = p === 'fila' ? fila : p === 'atendendo' ? meus : recentes
    const vazio =
      p === 'fila'
        ? 'Ninguém à espera na fila.'
        : p === 'atendendo'
          ? 'Nenhum chat em atendimento.'
          : 'Ainda não há chats encerrados visíveis.'

    if (p === 'atendendo' && mostrarSecoes) {
      return (
        <>
          {comigo.length > 0 ? (
            <>
              <Text style={styles.secao}>Comigo ({comigo.length})</Text>
              {comigo.map((chat) => (
                <ChatLinha
                  key={chat.id}
                  chat={chat}
                  destacado
                  onPress={() => router.push(`/conversa/${chat.id}`)}
                />
              ))}
            </>
          ) : null}
          <Text style={styles.secao}>Outros atendentes ({outros.length})</Text>
          {outros.map((chat) => (
            <ChatLinha
              key={chat.id}
              chat={chat}
              mostrarResponsavel
              onPress={() => router.push(`/conversa/${chat.id}`)}
            />
          ))}
        </>
      )
    }

    if (lista.length === 0) {
      return <EmptyState icone="chatbubbles-outline" titulo={vazio} />
    }

    return (
      <>
        {lista.map((chat) => (
          <ChatLinha key={chat.id} chat={chat} onPress={() => router.push(`/conversa/${chat.id}`)} />
        ))}
        {p === 'recentes' && recentes.length < recentesTotal ? (
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Ver mais chats recentes"
            style={styles.verMais}
            onPress={() => void carregarMaisRecentes()}
            disabled={aCarregarMais}
          >
            {aCarregarMais ? (
              <ActivityIndicator color={cores.teal} />
            ) : (
              <Text style={styles.verMaisTxt}>Ver mais</Text>
            )}
          </Pressable>
        ) : null}
      </>
    )
  }

  return (
    <View style={[styles.root, { paddingTop: insets.top }]}>
      <SegTabs
        ativo={aba}
        onChange={(id) => {
          const destino = id as Aba
          if (destino === aba) return
          setAba(destino)
          if (largura > 0) {
            pagerRef.current?.scrollTo({ x: ABAS.indexOf(destino) * largura, animated: true })
          }
        }}
        itens={[
          { id: 'fila', titulo: 'Fila', badge: fila.length },
          { id: 'atendendo', titulo: 'Atendendo', badge: meus.length },
          { id: 'recentes', titulo: 'Recentes' },
        ]}
      />
      {erro ? <Text style={styles.erro}>{erro}</Text> : null}
      {aCarregar && fila.length === 0 && meus.length === 0 && recentes.length === 0 ? (
        <ActivityIndicator style={{ marginTop: 40 }} color={cores.teal} />
      ) : (
        <View
          style={styles.pager}
          onLayout={(e) => {
            setLargura(e.nativeEvent.layout.width)
            setAltura(e.nativeEvent.layout.height)
          }}
        >
          {largura > 0 ? (
            <ScrollView
              ref={pagerRef}
              horizontal
              pagingEnabled
              style={styles.pagerScroll}
              showsHorizontalScrollIndicator={false}
              onMomentumScrollEnd={(e) => {
                const i = Math.round(e.nativeEvent.contentOffset.x / largura)
                const destino = ABAS[Math.max(0, Math.min(i, ABAS.length - 1))]
                if (destino !== aba) setAba(destino)
              }}
            >
              {ABAS.map((p) => (
                <View key={p} style={{ width: largura, height: altura }}>
                  <ScrollView
                    contentContainerStyle={
                      (p === 'fila' ? fila.length : p === 'atendendo' ? meus.length : recentes.length) === 0
                        ? styles.scrollVazio
                        : styles.scrollLista
                    }
                    refreshControl={
                      <RefreshControl
                        refreshing={aAtualizar}
                        onRefresh={() => {
                          setAAtualizar(true)
                          void carregar()
                        }}
                      />
                    }
                  >
                    {conteudoAba(p)}
                  </ScrollView>
                </View>
              ))}
            </ScrollView>
          ) : null}
        </View>
      )}
      <Pressable
        accessibilityRole="button"
        accessibilityLabel="Nova conversa"
        style={styles.fab}
        onPress={() => router.push('/chat-novo')}
      >
        <Icon name="add" size={28} color={cores.sobre} />
      </Pressable>
    </View>
  )
}

function ChatLinha({
  chat,
  onPress,
  mostrarResponsavel,
  destacado,
}: {
  chat: WhatsappChat
  onPress: () => void
  mostrarResponsavel?: boolean
  destacado?: boolean
}) {
  const nome = nomeDoChat(chat)
  const styles = usarEstilos()
  return (
    <Pressable accessibilityRole="button" style={[styles.item, destacado && styles.itemMeu]} onPress={onPress}>
      <Avatar nome={nome} fotoUrl={chat.foto_perfil_url} />
      <View style={styles.meio}>
        <Text style={styles.nome} numberOfLines={1}>
          {nome}
        </Text>
        <Text style={styles.meta} numberOfLines={1}>
          {mostrarResponsavel
            ? chat.atendente_nome || 'Outro atendente'
            : chat.empresa_nome || chat.protocolo}
          {chat.setor_nome ? ` · ${chat.setor_nome}` : ''}
        </Text>
      </View>
      <View style={styles.dir}>
        <Text style={styles.hora}>{horaCurta(chat.atendimento_inicio_at || chat.created_at)}</Text>
        {chat.nao_lidas_count ? (
          <View style={styles.badge}>
            <Text style={styles.badgeTxt}>{chat.nao_lidas_count}</Text>
          </View>
        ) : (
          <StatusChip estado={chat.estado} />
        )}
      </View>
    </Pressable>
  )
}

function usarEstilos() {
  const cores = useCores()
  return useMemo(() => criarEstilos(cores), [cores])
}

function criarEstilos(cores: Cores) {
  return StyleSheet.create({
  root: { flex: 1, backgroundColor: cores.deck },
  pager: { flex: 1 },
  pagerScroll: { flex: 1 },
  scrollVazio: { flexGrow: 1, paddingBottom: 88 },
  scrollLista: { paddingBottom: 88 },
  secao: {
    marginHorizontal: 20,
    marginTop: 16,
    marginBottom: 4,
    fontSize: 12,
    fontWeight: '700',
    color: cores.muted,
    letterSpacing: 0.4,
    textTransform: 'uppercase',
  },
  erro: {
    color: cores.danger,
    backgroundColor: cores.dangerBg,
    marginHorizontal: 16,
    marginTop: 8,
    padding: 12,
    borderRadius: 12,
  },
  item: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginHorizontal: 12,
    marginTop: 8,
    paddingHorizontal: 14,
    paddingVertical: 12,
    backgroundColor: cores.white,
    borderRadius: 16,
  },
  itemMeu: { borderLeftWidth: 3, borderLeftColor: cores.teal },
  meio: { flex: 1, minWidth: 0, gap: 3 },
  nome: { fontSize: 16, fontWeight: '600', color: cores.text },
  meta: { fontSize: 13, color: cores.muted },
  dir: { alignItems: 'flex-end', gap: 6 },
  hora: { fontSize: 11, color: cores.muted, fontWeight: '500' },
  badge: {
    minWidth: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: cores.teal,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 6,
  },
  badgeTxt: { color: cores.sobre, fontSize: 11, fontWeight: '700' },
  verMais: {
    marginHorizontal: 12,
    marginTop: 12,
    marginBottom: 8,
    paddingVertical: 14,
    borderRadius: 16,
    backgroundColor: cores.white,
    alignItems: 'center',
    justifyContent: 'center',
  },
  verMaisTxt: { fontSize: 15, fontWeight: '700', color: cores.tealDark },
  fab: {
    position: 'absolute',
    right: 18,
    bottom: 18,
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: cores.teal,
    alignItems: 'center',
    justifyContent: 'center',
    elevation: 4,
    shadowColor: '#0B2D4A',
    shadowOpacity: 0.2,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 4 },
  },
  })
}
