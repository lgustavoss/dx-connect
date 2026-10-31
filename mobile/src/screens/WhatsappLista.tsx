import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
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
import { colors } from '../lib/brand'
import { horaCurta, nomeDoChat } from '../lib/format'

type Aba = 'fila' | 'atendendo' | 'recentes'

const PAGINA_RECENTES = 10

export function WhatsappLista() {
  const router = useRouter()
  const insets = useSafeAreaInsets()
  const { me } = useAuth()
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

  const lista = aba === 'fila' ? fila : aba === 'atendendo' ? meus : recentes
  const vazio =
    aba === 'fila'
      ? 'Ninguém à espera na fila.'
      : aba === 'atendendo'
        ? 'Nenhum chat em atendimento.'
        : 'Ainda não há chats encerrados visíveis.'

  return (
    <View style={[styles.root, { paddingTop: insets.top }]}>
      <SegTabs
        ativo={aba}
        onChange={(id) => setAba(id as Aba)}
        itens={[
          { id: 'fila', titulo: 'Fila', badge: fila.length },
          { id: 'atendendo', titulo: 'Atendendo', badge: meus.length },
          { id: 'recentes', titulo: 'Recentes' },
        ]}
      />
      {erro ? <Text style={styles.erro}>{erro}</Text> : null}
      {aCarregar && fila.length === 0 && meus.length === 0 && recentes.length === 0 ? (
        <ActivityIndicator style={{ marginTop: 40 }} color={colors.teal} />
      ) : (
        <ScrollView
          contentContainerStyle={lista.length === 0 ? styles.scrollVazio : styles.scrollLista}
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
          {aba === 'atendendo' && mostrarSecoes ? (
            <>
              {comigo.length > 0 ? (
                <>
                  <Text style={styles.secao}>Comigo ({comigo.length})</Text>
                  {comigo.map((chat) => (
                    <ChatLinha key={chat.id} chat={chat} destacado onPress={() => router.push(`/conversa/${chat.id}`)} />
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
          ) : lista.length === 0 ? (
            <EmptyState icone="chatbubbles-outline" titulo={vazio} />
          ) : (
            <>
              {lista.map((chat) => (
                <ChatLinha key={chat.id} chat={chat} onPress={() => router.push(`/conversa/${chat.id}`)} />
              ))}
              {aba === 'recentes' && recentes.length < recentesTotal ? (
                <Pressable
                  accessibilityRole="button"
                  accessibilityLabel="Ver mais chats recentes"
                  style={styles.verMais}
                  onPress={() => void carregarMaisRecentes()}
                  disabled={aCarregarMais}
                >
                  {aCarregarMais ? (
                    <ActivityIndicator color={colors.teal} />
                  ) : (
                    <Text style={styles.verMaisTxt}>Ver mais</Text>
                  )}
                </Pressable>
              ) : null}
            </>
          )}
        </ScrollView>
      )}
      <Pressable
        accessibilityRole="button"
        accessibilityLabel="Nova conversa"
        style={styles.fab}
        onPress={() => router.push('/chat-novo')}
      >
        <Icon name="add" size={28} color={colors.white} />
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

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.deck },
  scrollVazio: { flexGrow: 1, paddingBottom: 88 },
  scrollLista: { paddingBottom: 88 },
  secao: {
    marginHorizontal: 20,
    marginTop: 16,
    marginBottom: 4,
    fontSize: 12,
    fontWeight: '700',
    color: colors.muted,
    letterSpacing: 0.4,
    textTransform: 'uppercase',
  },
  erro: {
    color: colors.danger,
    backgroundColor: colors.dangerBg,
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
    backgroundColor: colors.white,
    borderRadius: 16,
  },
  itemMeu: { borderLeftWidth: 3, borderLeftColor: colors.teal },
  meio: { flex: 1, minWidth: 0, gap: 3 },
  nome: { fontSize: 16, fontWeight: '600', color: colors.text },
  meta: { fontSize: 13, color: colors.muted },
  dir: { alignItems: 'flex-end', gap: 6 },
  hora: { fontSize: 11, color: colors.muted, fontWeight: '500' },
  badge: {
    minWidth: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: colors.teal,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 6,
  },
  badgeTxt: { color: colors.white, fontSize: 11, fontWeight: '700' },
  verMais: {
    marginHorizontal: 12,
    marginTop: 12,
    marginBottom: 8,
    paddingVertical: 14,
    borderRadius: 16,
    backgroundColor: colors.white,
    alignItems: 'center',
    justifyContent: 'center',
  },
  verMaisTxt: { fontSize: 15, fontWeight: '700', color: colors.tealDark },
  fab: {
    position: 'absolute',
    right: 18,
    bottom: 18,
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: colors.teal,
    alignItems: 'center',
    justifyContent: 'center',
    elevation: 4,
    shadowColor: '#0B2D4A',
    shadowOpacity: 0.2,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 4 },
  },
})
