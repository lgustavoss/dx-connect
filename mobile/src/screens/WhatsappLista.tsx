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

import { ApiError, type WhatsappChat, whatsapp } from '../api/client'
import { useRealtimeRefresh } from '../hooks/useRealtimeRefresh'
import { colors } from '../lib/brand'
import { horaCurta, nomeDoChat, rotuloEstado } from '../lib/format'

type Aba = 'fila' | 'meus' | 'recentes'

export function WhatsappLista() {
  const router = useRouter()
  const [aba, setAba] = useState<Aba>('fila')
  const [fila, setFila] = useState<WhatsappChat[]>([])
  const [meus, setMeus] = useState<WhatsappChat[]>([])
  const [recentes, setRecentes] = useState<WhatsappChat[]>([])
  const [erro, setErro] = useState<string | null>(null)
  const [aCarregar, setACarregar] = useState(true)
  const [aAtualizar, setAAtualizar] = useState(false)

  const carregar = useCallback(async (silencioso = false) => {
    if (!silencioso) setACarregar(true)
    try {
      const [f, m, r] = await Promise.all([
        whatsapp.fila(),
        whatsapp.meus(),
        whatsapp.encerrados().catch(() => ({ items: [] as WhatsappChat[] })),
      ])
      setFila(f)
      setMeus(m)
      setRecentes(r.items || [])
      setErro(null)
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : 'Não foi possível carregar os chats.')
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

  const lista = aba === 'fila' ? fila : aba === 'meus' ? meus : recentes
  const vazio =
    aba === 'fila'
      ? 'Ninguém à espera na fila.'
      : aba === 'meus'
        ? 'Você não tem chats em atendimento.'
        : 'Ainda não há chats encerrados visíveis.'

  return (
    <View style={styles.root}>
      <View style={styles.segs}>
        <Seg titulo="Fila" activo={aba === 'fila'} badge={fila.length} onPress={() => setAba('fila')} />
        <Seg titulo="Meus" activo={aba === 'meus'} badge={meus.length} onPress={() => setAba('meus')} />
        <Seg titulo="Recentes" activo={aba === 'recentes'} badge={recentes.length} onPress={() => setAba('recentes')} />
      </View>
      {erro ? <Text style={styles.erro}>{erro}</Text> : null}
      {aCarregar && lista.length === 0 ? (
        <ActivityIndicator style={{ marginTop: 32 }} color={colors.teal} />
      ) : (
        <ScrollView
          refreshControl={
            <RefreshControl refreshing={aAtualizar} onRefresh={() => { setAAtualizar(true); void carregar() }} />
          }
        >
          {lista.length === 0 ? <Text style={styles.vazio}>{vazio}</Text> : null}
          {lista.map((chat) => (
            <Pressable
              key={chat.id}
              style={styles.item}
              onPress={() => router.push(`/conversa/${chat.id}`)}
            >
              <View style={styles.avatar}>
                <Text style={styles.avatarTxt}>{iniciais(nomeDoChat(chat))}</Text>
              </View>
              <View style={styles.meio}>
                <Text style={styles.nome} numberOfLines={1}>
                  {nomeDoChat(chat)}
                </Text>
                <Text style={styles.meta} numberOfLines={1}>
                  {chat.empresa_nome || chat.protocolo}
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
                  <Text style={styles.estado}>{rotuloEstado(chat.estado)}</Text>
                )}
              </View>
            </Pressable>
          ))}
        </ScrollView>
      )}
    </View>
  )
}

function Seg({
  titulo,
  activo,
  badge,
  onPress,
}: {
  titulo: string
  activo: boolean
  badge: number
  onPress: () => void
}) {
  return (
    <Pressable onPress={onPress} style={[styles.seg, activo && styles.segOn]}>
      <Text style={[styles.segTxt, activo && styles.segTxtOn]}>
        {titulo}
        {badge > 0 ? ` (${badge})` : ''}
      </Text>
    </Pressable>
  )
}

function iniciais(nome: string): string {
  const partes = nome.split(/\s+/).filter(Boolean)
  const a = partes[0]?.[0] || '?'
  const b = partes.length > 1 ? partes[partes.length - 1][0] : ''
  return (a + b).toUpperCase()
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.deck },
  segs: { flexDirection: 'row', padding: 12, gap: 8 },
  seg: {
    flex: 1,
    paddingVertical: 10,
    borderRadius: 10,
    backgroundColor: colors.white,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: colors.border,
  },
  segOn: { backgroundColor: colors.navy, borderColor: colors.navy },
  segTxt: { fontWeight: '700', color: colors.navyMid },
  segTxtOn: { color: colors.white },
  erro: { color: colors.danger, backgroundColor: colors.dangerBg, marginHorizontal: 12, padding: 10, borderRadius: 8 },
  vazio: { textAlign: 'center', color: colors.muted, marginTop: 40, paddingHorizontal: 24 },
  item: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: colors.white,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border,
  },
  avatar: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: colors.navy,
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarTxt: { color: colors.white, fontWeight: '700' },
  meio: { flex: 1, minWidth: 0 },
  nome: { fontSize: 16, fontWeight: '600', color: colors.text },
  meta: { fontSize: 13, color: colors.muted, marginTop: 2 },
  dir: { alignItems: 'flex-end', gap: 4 },
  hora: { fontSize: 12, color: colors.muted },
  estado: { fontSize: 11, color: colors.tealDark },
  badge: {
    minWidth: 20,
    height: 20,
    borderRadius: 10,
    backgroundColor: colors.teal,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 6,
  },
  badgeTxt: { color: colors.white, fontSize: 11, fontWeight: '700' },
})
