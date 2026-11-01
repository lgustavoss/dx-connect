import { useCallback, useEffect, useState } from 'react'
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

import { ApiError, type Ticket, tickets } from '../api/client'
import { Avatar } from '../components/Avatar'
import { EmptyState } from '../components/EmptyState'
import { SegTabs } from '../components/SegTabs'
import { useRealtimeRefresh } from '../hooks/useRealtimeRefresh'
import { colors } from '../lib/brand'
import { horaCurta } from '../lib/format'

type Aba = 'fila' | 'meus'

export function TicketsLista() {
  const router = useRouter()
  const insets = useSafeAreaInsets()
  const [aba, setAba] = useState<Aba>('fila')
  const [fila, setFila] = useState<Ticket[]>([])
  const [meus, setMeus] = useState<Ticket[]>([])
  const [erro, setErro] = useState<string | null>(null)
  const [aCarregar, setACarregar] = useState(true)
  const [aAtualizar, setAAtualizar] = useState(false)

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

  const lista = aba === 'fila' ? fila : meus
  const vazio =
    aba === 'fila' ? 'Nenhum ticket sem responsável.' : 'Você não tem tickets em aberto.'

  return (
    <View style={[styles.root, { paddingTop: insets.top }]}>
      <SegTabs
        ativo={aba}
        onChange={(id) => setAba(id as Aba)}
        itens={[
          { id: 'fila', titulo: 'Fila', badge: fila.length },
          { id: 'meus', titulo: 'Meus', badge: meus.length },
        ]}
      />
      {erro ? <Text style={styles.erro}>{erro}</Text> : null}
      {aCarregar && lista.length === 0 ? (
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
          {lista.length === 0 ? <EmptyState icone="ticket-outline" titulo={vazio} /> : null}
          {lista.map((t) => (
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
      )}
    </View>
  )
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.deck },
  scrollVazio: { flexGrow: 1 },
  scrollLista: { paddingBottom: 28 },
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
  meio: { flex: 1, minWidth: 0, gap: 2 },
  prot: { fontSize: 12, fontWeight: '700', color: colors.tealDark, letterSpacing: 0.2 },
  nome: { fontSize: 15, fontWeight: '600', color: colors.text },
  meta: { fontSize: 13, color: colors.muted },
  dir: { alignItems: 'flex-end', gap: 6, maxWidth: 108 },
  hora: { fontSize: 11, color: colors.muted, fontWeight: '500' },
  estado: { fontSize: 11, fontWeight: '600', color: colors.tealDark, textAlign: 'right' },
})
