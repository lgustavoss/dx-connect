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

import { ApiError, type Ticket, tickets } from '../api/client'
import { Avatar } from '../components/Avatar'
import { EmptyState } from '../components/EmptyState'
import { SegTabs } from '../components/SegTabs'
import { useRealtimeRefresh } from '../hooks/useRealtimeRefresh'
import { type Cores } from '../lib/brand'
import { horaCurta } from '../lib/format'
import { useCores } from '../lib/tema'

type Aba = 'fila' | 'meus'

const ABAS: Aba[] = ['fila', 'meus']
const VAZIOS: Record<Aba, string> = {
  fila: 'Nenhum ticket sem responsável.',
  meus: 'Você não tem tickets em aberto.',
}

export function TicketsLista() {
  const router = useRouter()
  const insets = useSafeAreaInsets()
  const cores = useCores()
  const styles = usarEstilos()
  const [aba, setAba] = useState<Aba>('fila')
  const [fila, setFila] = useState<Ticket[]>([])
  const [meus, setMeus] = useState<Ticket[]>([])
  const [erro, setErro] = useState<string | null>(null)
  const [aCarregar, setACarregar] = useState(true)
  const [aAtualizar, setAAtualizar] = useState(false)
  const [largura, setLargura] = useState(0)
  const [altura, setAltura] = useState(0)
  const pagerRef = useRef<ScrollViewInstance | null>(null)

  const carregar = useCallback(async (silencioso = false) => {
    if (!silencioso) setACarregar(true)
    try {
      const [f, m] = await Promise.all([tickets.fila(), tickets.meus()])
      setFila(f.items || [])
      setMeus(m.items || [])
      setErro(null)
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : 'Não foi possível carregar os tickets.')
    } finally {
      setACarregar(false)
      setAAtualizar(false)
    }
  }, [])

  useEffect(() => {
    void carregar()
  }, [carregar])

  const refreshSilencioso = useCallback(() => {
    void carregar(true)
  }, [carregar])
  useRealtimeRefresh(refreshSilencioso, true)

  useEffect(() => {
    if (largura > 0) {
      pagerRef.current?.scrollTo({ x: ABAS.indexOf(aba) * largura, animated: false })
    }
  }, [aba, largura])

  const listas: Record<Aba, Ticket[]> = { fila, meus }
  const lista = listas[aba]

  function irPara(destino: Aba) {
    setAba(destino)
    if (largura > 0) {
      pagerRef.current?.scrollTo({ x: ABAS.indexOf(destino) * largura, animated: true })
    }
  }

  function pagina(p: Aba) {
    const itens = listas[p]
    return (
      <ScrollView
        key={p}
        style={{ width: largura, height: altura }}
        contentContainerStyle={itens.length === 0 ? styles.scrollVazio : styles.scrollLista}
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
        {itens.length === 0 ? <EmptyState icone="ticket-outline" titulo={VAZIOS[p]} /> : null}
        {itens.map((t) => (
          <Pressable
            key={t.id}
            accessibilityRole="button"
            style={styles.item}
            onPress={() => router.push(`/ticket/${t.id}`)}
          >
            <Avatar nome={t.empresa_nome || t.protocolo} />
            <View style={styles.meio}>
              <Text style={styles.prot}>{t.protocolo}</Text>
              <Text style={styles.nome} numberOfLines={1}>
                {t.assunto}
              </Text>
              <Text style={styles.meta} numberOfLines={1}>
                {t.empresa_nome || 'Sem empresa'}
                {t.setor_nome ? ` · ${t.setor_nome}` : ''}
              </Text>
            </View>
            <View style={styles.dir}>
              <Text style={styles.hora}>{horaCurta(t.fila_desde_at || t.created_at)}</Text>
              <Text style={styles.estado} numberOfLines={1}>
                {t.status_nome || (t.atendente_id ? 'Em atendimento' : 'Na fila')}
              </Text>
            </View>
          </Pressable>
        ))}
      </ScrollView>
    )
  }

  return (
    <View style={[styles.root, { paddingTop: insets.top }]}>
      <SegTabs
        ativo={aba}
        onChange={(id) => irPara(id as Aba)}
        itens={[
          { id: 'fila', titulo: 'Fila', badge: fila.length },
          { id: 'meus', titulo: 'Meus', badge: meus.length },
        ]}
      />
      {erro ? <Text style={styles.erro}>{erro}</Text> : null}
      {aCarregar && lista.length === 0 ? (
        <ActivityIndicator style={{ marginTop: 40 }} color={cores.teal} />
      ) : (
        <View
          style={styles.pager}
          onLayout={(e) => {
            setLargura(e.nativeEvent.layout.width)
            setAltura(e.nativeEvent.layout.height)
          }}
        >
          <ScrollView
            ref={pagerRef}
            horizontal
            pagingEnabled
            style={styles.pagerScroll}
            showsHorizontalScrollIndicator={false}
            onMomentumScrollEnd={(e) => {
              if (largura <= 0) return
              const indice = Math.round(e.nativeEvent.contentOffset.x / largura)
              const destino = ABAS[indice]
              if (destino && destino !== aba) setAba(destino)
            }}
          >
            {ABAS.map((p) => pagina(p))}
          </ScrollView>
        </View>
      )}
    </View>
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
  scrollVazio: { flexGrow: 1 },
  scrollLista: { paddingBottom: 28 },
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
  meio: { flex: 1, minWidth: 0, gap: 2 },
  prot: { fontSize: 12, fontWeight: '700', color: cores.tealDark, letterSpacing: 0.2 },
  nome: { fontSize: 15, fontWeight: '600', color: cores.text },
  meta: { fontSize: 13, color: cores.muted },
  dir: { alignItems: 'flex-end', gap: 6, maxWidth: 108 },
  hora: { fontSize: 11, color: cores.muted, fontWeight: '500' },
  estado: { fontSize: 11, fontWeight: '600', color: cores.tealDark, textAlign: 'right' },
  })
}
