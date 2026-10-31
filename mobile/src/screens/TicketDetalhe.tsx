import { useCallback, useEffect, useRef, useState } from 'react'
import {
  ActivityIndicator,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native'
import { useLocalSearchParams, useNavigation } from 'expo-router'

import { ApiError, type Ticket, type TicketMensagem, tickets } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { FaixaGestoVoltar } from '../components/FaixaGestoVoltar'
import { Icon } from '../components/Icon'
import { useRealtimeRefresh } from '../hooks/useRealtimeRefresh'
import { colors, radius } from '../lib/brand'
import { horaCurta } from '../lib/format'

export function TicketDetalhe() {
  const { id: idParam } = useLocalSearchParams<{ id: string }>()
  const ticketId = Number(idParam)
  const navigation = useNavigation()
  const { me } = useAuth()
  const listRef = useRef<FlatList<TicketMensagem>>(null)
  const inflight = useRef<Promise<void> | null>(null)
  const colarNoFim = useRef(true)
  const [ticket, setTicket] = useState<Ticket | null>(null)
  const [mensagens, setMensagens] = useState<TicketMensagem[]>([])
  const [texto, setTexto] = useState('')
  const [interno, setInterno] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  const [aCarregar, setACarregar] = useState(true)
  const [aEnviar, setAEnviar] = useState(false)
  const [aAssumir, setAAssumir] = useState(false)

  const carregar = useCallback(
    async (silencioso = false) => {
      if (!Number.isFinite(ticketId) || ticketId <= 0) return
      if (inflight.current) return inflight.current
      if (!silencioso) setACarregar(true)
      const p = (async () => {
        try {
          const [t, msgs] = await Promise.all([tickets.get(ticketId), tickets.mensagens(ticketId)])
          setTicket(t)
          setMensagens(msgs)
          setErro(null)
        } catch (e) {
          setErro(e instanceof ApiError ? e.message : 'Não foi possível abrir o ticket.')
        } finally {
          setACarregar(false)
          inflight.current = null
        }
      })()
      inflight.current = p
      await p
    },
    [ticketId],
  )

  useEffect(() => {
    void carregar()
  }, [carregar])

  const refreshSilencioso = useCallback(() => {
    void carregar(true)
  }, [carregar])
  useRealtimeRefresh(refreshSilencioso, Number.isFinite(ticketId) && ticketId > 0 && Boolean(ticket))

  useEffect(() => {
    navigation.setOptions({ title: ticket?.protocolo || 'Ticket' })
  }, [ticket, navigation])

  const naFila = Boolean(ticket && !ticket.atendente_id && !ticket.fechado_em)
  const meu = ticket?.atendente_id === me?.id || me?.role === 'admin'
  const possoEnviar = Boolean(ticket && !ticket.fechado_em && meu && ticket.atendente_id)

  async function assumir() {
    if (!me?.id) return
    setAAssumir(true)
    try {
      const t = await tickets.assumir(ticketId, me.id)
      setTicket(t)
      setErro(null)
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : 'Não foi possível assumir.')
    } finally {
      setAAssumir(false)
    }
  }

  async function enviar() {
    const corpo = texto.trim()
    if (!corpo || !possoEnviar) return
    setAEnviar(true)
    try {
      const msg = await tickets.enviar(ticketId, corpo, interno ? 'interno' : 'publico')
      setMensagens((prev) => [...prev.filter((m) => m.id !== msg.id), msg])
      setTexto('')
      setErro(null)
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : 'Não foi possível enviar.')
    } finally {
      setAEnviar(false)
    }
  }

  if (aCarregar && !ticket) {
    return (
      <View style={styles.centro}>
        <ActivityIndicator color={colors.teal} />
        <FaixaGestoVoltar fallback="/tickets" />
      </View>
    )
  }

  return (
    <View style={styles.root}>
    <KeyboardAvoidingView
      style={styles.root}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={88}
    >
      {erro ? <Text style={styles.erro}>{erro}</Text> : null}
      {ticket ? (
        <View style={styles.cabecalho}>
          <Text style={styles.assunto}>{ticket.assunto}</Text>
          <Text style={styles.meta} numberOfLines={2}>
            {ticket.empresa_nome || 'Sem empresa'}
            {ticket.setor_nome ? ` · ${ticket.setor_nome}` : ''}
            {ticket.status_nome ? ` · ${ticket.status_nome}` : ''}
          </Text>
        </View>
      ) : null}
      {naFila ? (
        <View style={styles.barraFila}>
          <View style={{ flex: 1 }}>
            <Text style={styles.barraFilaTitulo}>Na fila</Text>
            <Text style={styles.barraFilaTxt}>Assuma para responder.</Text>
          </View>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Assumir"
            style={styles.botaoAssumir}
            onPress={() => void assumir()}
            disabled={aAssumir}
          >
            {aAssumir ? (
              <ActivityIndicator color={colors.white} />
            ) : (
              <Text style={styles.botaoAssumirTxt}>Assumir</Text>
            )}
          </Pressable>
        </View>
      ) : null}
      <FlatList
        ref={listRef}
        data={mensagens}
        keyExtractor={(m) => String(m.id)}
        contentContainerStyle={styles.lista}
        onScroll={(e) => {
          const { contentOffset, layoutMeasurement, contentSize } = e.nativeEvent
          colarNoFim.current = contentOffset.y + layoutMeasurement.height >= contentSize.height - 120
        }}
        scrollEventThrottle={16}
        onContentSizeChange={() => {
          if (colarNoFim.current) listRef.current?.scrollToEnd({ animated: false })
        }}
        renderItem={({ item }) => <Bolha msg={item} />}
      />
      {possoEnviar ? (
        <View>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={interno ? 'Nota interna' : 'Resposta pública'}
            style={styles.toggle}
            onPress={() => setInterno((v) => !v)}
          >
            <Icon
              name={interno ? 'lock-closed-outline' : 'globe-outline'}
              size={16}
              color={interno ? colors.warning : colors.muted}
            />
            <Text style={[styles.toggleTxt, interno && styles.toggleOn]}>
              {interno ? 'Nota interna (só a equipe vê)' : 'Resposta pública'}
            </Text>
          </Pressable>
          <View style={styles.composer}>
            <TextInput
              style={styles.input}
              placeholder={interno ? 'Nota interna' : 'Mensagem'}
              placeholderTextColor={colors.muted}
              value={texto}
              onChangeText={setTexto}
              multiline
              editable={!aEnviar}
              onSubmitEditing={() => void enviar()}
            />
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Enviar"
              style={[styles.enviar, (!texto.trim() || aEnviar) && styles.enviarOff]}
              onPress={() => void enviar()}
              disabled={!texto.trim() || aEnviar}
            >
              <Icon name="send" size={18} color={colors.white} />
            </Pressable>
          </View>
        </View>
      ) : (
        <Text style={styles.avisoComposer}>
          {ticket?.fechado_em
            ? 'Ticket encerrado.'
            : naFila
              ? 'Assuma o ticket para responder.'
              : 'Só o responsável pode enviar.'}
        </Text>
      )}
    </KeyboardAvoidingView>
    <FaixaGestoVoltar fallback="/tickets" />
    </View>
  )
}

function Bolha({ msg }: { msg: TicketMensagem }) {
  const interno = msg.tipo === 'interno'
  const outbound = Boolean(msg.atendente_id) && !msg.autor_externo
  return (
    <View style={[styles.bolhaWrap, outbound ? styles.bolhaWrapOut : styles.bolhaWrapIn]}>
      <View
        style={[
          styles.bolha,
          interno ? styles.bolhaInterno : outbound ? styles.bolhaOut : styles.bolhaIn,
        ]}
      >
        {interno ? <Text style={styles.autorInterno}>Nota interna</Text> : null}
        {!interno && (msg.atendente_nome || msg.autor_externo) ? (
          <Text style={[styles.autor, outbound && !interno ? styles.autorOut : null]}>
            {msg.atendente_nome || msg.autor_externo}
          </Text>
        ) : null}
        <Text style={[styles.corpo, interno ? styles.corpoInterno : outbound ? styles.corpoOut : styles.corpoIn]}>
          {msg.corpo}
        </Text>
        <Text style={[styles.horaBolha, outbound && !interno ? styles.horaOut : styles.horaIn]}>
          {horaCurta(msg.created_at)}
        </Text>
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.chatBg },
  centro: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.deck },
  erro: { color: colors.danger, backgroundColor: colors.dangerBg, margin: 8, padding: 10, borderRadius: radius.md },
  cabecalho: {
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: colors.white,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border,
  },
  assunto: { fontSize: 16, fontWeight: '700', color: colors.text },
  meta: { fontSize: 13, color: colors.muted, marginTop: 4 },
  barraFila: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    margin: 12,
    padding: 14,
    backgroundColor: colors.warningBg,
    borderRadius: radius.md,
    gap: 12,
  },
  barraFilaTitulo: { color: colors.warning, fontWeight: '700', fontSize: 14 },
  barraFilaTxt: { color: colors.warning, fontSize: 13, marginTop: 2 },
  botaoAssumir: {
    backgroundColor: colors.teal,
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: radius.full,
    minWidth: 96,
    alignItems: 'center',
  },
  botaoAssumirTxt: { color: colors.white, fontWeight: '700' },
  lista: { padding: 12, paddingBottom: 24 },
  bolhaWrap: { marginBottom: 6, maxWidth: '82%' },
  bolhaWrapIn: { alignSelf: 'flex-start' },
  bolhaWrapOut: { alignSelf: 'flex-end' },
  bolha: { borderRadius: 16, paddingHorizontal: 12, paddingVertical: 8 },
  bolhaIn: { backgroundColor: colors.white, borderBottomLeftRadius: 4 },
  bolhaOut: { backgroundColor: colors.teal, borderBottomRightRadius: 4 },
  bolhaInterno: { backgroundColor: colors.warningBg, borderBottomLeftRadius: 4 },
  autor: { fontSize: 11, color: colors.muted, marginBottom: 2 },
  autorOut: { color: colors.white, opacity: 0.85 },
  autorInterno: { fontSize: 11, color: colors.warning, fontWeight: '700', marginBottom: 2 },
  corpo: { fontSize: 16, lineHeight: 22 },
  corpoIn: { color: colors.text },
  corpoOut: { color: colors.white },
  corpoInterno: { color: '#78350F' },
  horaBolha: { fontSize: 11, marginTop: 4, alignSelf: 'flex-end' },
  horaIn: { color: colors.muted },
  horaOut: { color: colors.white, opacity: 0.85 },
  toggle: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 14,
    paddingTop: 10,
    backgroundColor: colors.white,
  },
  toggleTxt: { fontSize: 13, color: colors.muted, fontWeight: '600' },
  toggleOn: { color: colors.warning },
  composer: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: 8,
    padding: 10,
    backgroundColor: colors.white,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.border,
  },
  input: {
    flex: 1,
    minHeight: 40,
    maxHeight: 120,
    borderWidth: 0,
    borderRadius: 20,
    paddingHorizontal: 14,
    paddingVertical: 10,
    fontSize: 16,
    color: colors.text,
    backgroundColor: colors.deck,
  },
  enviar: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: colors.teal,
    alignItems: 'center',
    justifyContent: 'center',
  },
  enviarOff: { opacity: 0.4 },
  avisoComposer: {
    textAlign: 'center',
    color: colors.muted,
    padding: 14,
    backgroundColor: colors.white,
  },
})
