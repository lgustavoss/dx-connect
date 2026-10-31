import { useCallback, useEffect, useRef, useState } from 'react'
import {
  ActivityIndicator,
  Alert,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native'
import * as DocumentPicker from 'expo-document-picker'
import * as ImagePicker from 'expo-image-picker'
import { useLocalSearchParams, useNavigation } from 'expo-router'

import { ApiError, type WhatsappChat, type WhatsappMensagem, whatsapp } from '../api/client'
import { temArquivoMidia, WhatsappMidia } from '../components/WhatsappMidia'
import { useAuth } from '../auth/AuthContext'
import { useRealtimeRefresh } from '../hooks/useRealtimeRefresh'
import { colors } from '../lib/brand'
import { horaCurta, legendaMidiaVisivel, nomeDoChat } from '../lib/format'

export function WhatsappConversa() {
  const { id: idParam } = useLocalSearchParams<{ id: string }>()
  const chatId = Number(idParam)
  const navigation = useNavigation()
  const { me } = useAuth()
  const listRef = useRef<FlatList<WhatsappMensagem>>(null)
  const inflight = useRef<Promise<void> | null>(null)
  const [chat, setChat] = useState<WhatsappChat | null>(null)
  const [mensagens, setMensagens] = useState<WhatsappMensagem[]>([])
  const [texto, setTexto] = useState('')
  const [erro, setErro] = useState<string | null>(null)
  const [aCarregar, setACarregar] = useState(true)
  const [aEnviar, setAEnviar] = useState(false)
  const [aAssumir, setAAssumir] = useState(false)
  const [menuAnexo, setMenuAnexo] = useState(false)
  const colarNoFim = useRef(true)

  const carregar = useCallback(
    async (silencioso = false) => {
      if (!Number.isFinite(chatId) || chatId <= 0) return
      if (inflight.current) return inflight.current
      if (!silencioso) setACarregar(true)
      const p = (async () => {
        try {
          const [c, msgs] = await Promise.all([whatsapp.get(chatId), whatsapp.mensagens(chatId)])
          setChat(c)
          setMensagens(msgs.filter((m) => !m.evento_sistema))
          setErro(null)
          void whatsapp.marcarVisto(chatId).catch(() => undefined)
        } catch (e) {
          setErro(e instanceof ApiError ? e.message : 'Não foi possível abrir a conversa.')
        } finally {
          setACarregar(false)
          inflight.current = null
        }
      })()
      inflight.current = p
      await p
    },
    [chatId],
  )

  useEffect(() => {
    void carregar()
  }, [carregar])

  const refreshSilencioso = useCallback(() => {
    void carregar(true)
  }, [carregar])
  useRealtimeRefresh(refreshSilencioso, Number.isFinite(chatId) && chatId > 0 && Boolean(chat))

  useEffect(() => {
    const titulo = chat ? nomeDoChat(chat) : 'Conversa'
    navigation.setOptions({ title: titulo })
  }, [chat, navigation])

  const naFila = chat?.estado === 'aguardando_atendente'
  const meu = chat?.atendente_id === me?.id || me?.role === 'admin'
  const possoEnviar = chat?.estado === 'em_atendimento' && meu

  async function assumir() {
    setAAssumir(true)
    try {
      const c = await whatsapp.assumir(chatId)
      setChat(c)
      setErro(null)
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : 'Não foi possível assumir.')
    } finally {
      setAAssumir(false)
    }
  }

  function pedirEncerrar() {
    Alert.alert('Encerrar conversa', 'O cliente deixa de estar em atendimento neste chat.', [
      { text: 'Cancelar', style: 'cancel' },
      {
        text: 'Encerrar',
        style: 'destructive',
        onPress: () => {
          void (async () => {
            try {
              const c = await whatsapp.encerrar(chatId)
              setChat(c)
            } catch (e) {
              setErro(e instanceof ApiError ? e.message : 'Não foi possível encerrar.')
            }
          })()
        },
      },
    ])
  }

  async function enviar() {
    const corpo = texto.trim()
    if (!corpo || !possoEnviar) return
    setAEnviar(true)
    try {
      const msg = await whatsapp.enviar(chatId, corpo)
      setMensagens((prev) => [...prev.filter((m) => m.id !== msg.id), msg])
      setTexto('')
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : 'Não foi possível enviar.')
    } finally {
      setAEnviar(false)
    }
  }

  async function enviarArquivo(file: { uri: string; name: string; type: string }) {
    if (!possoEnviar) return
    setAEnviar(true)
    try {
      const msg = await whatsapp.enviarMidia(chatId, file, texto.trim() || undefined)
      setMensagens((prev) => [...prev.filter((m) => m.id !== msg.id && !m.evento_sistema), msg])
      setTexto('')
      setErro(null)
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : 'Não foi possível enviar a mídia.')
    } finally {
      setAEnviar(false)
    }
  }

  async function anexarFoto() {
    const perm = await ImagePicker.requestMediaLibraryPermissionsAsync()
    if (Platform.OS !== 'web' && perm.status !== 'granted') {
      setErro('Permissão da galeria recusada.')
      return
    }
    const r = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['images'], quality: 0.8 })
    if (r.canceled || !r.assets[0]) return
    const a = r.assets[0]
    await enviarArquivo({
      uri: a.uri,
      name: a.fileName || 'foto.jpg',
      type: a.mimeType || 'image/jpeg',
    })
  }

  async function anexarArquivo() {
    const r = await DocumentPicker.getDocumentAsync({ copyToCacheDirectory: true })
    if (r.canceled || !r.assets?.[0]) return
    const a = r.assets[0]
    await enviarArquivo({
      uri: a.uri,
      name: a.name || 'arquivo',
      type: a.mimeType || 'application/octet-stream',
    })
  }

  function pedirAnexo() {
    if (Platform.OS === 'web') {
      setMenuAnexo((v) => !v)
      return
    }
    Alert.alert('Enviar anexo', undefined, [
      { text: 'Foto', onPress: () => void anexarFoto() },
      { text: 'Arquivo', onPress: () => void anexarArquivo() },
      { text: 'Cancelar', style: 'cancel' },
    ])
  }

  if (aCarregar && !chat) {
    return (
      <View style={styles.centro}>
        <ActivityIndicator color={colors.teal} />
      </View>
    )
  }

  return (
    <KeyboardAvoidingView
      style={styles.root}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={88}
    >
      {erro ? <Text style={styles.erro}>{erro}</Text> : null}
      {naFila ? (
        <View style={styles.barraFila}>
          <Text style={styles.barraFilaTxt}>Este chat está na fila.</Text>
          <Pressable style={styles.botaoAssumir} onPress={() => void assumir()} disabled={aAssumir}>
            {aAssumir ? (
              <ActivityIndicator color={colors.white} />
            ) : (
              <Text style={styles.botaoAssumirTxt}>Assumir</Text>
            )}
          </Pressable>
        </View>
      ) : null}
      {chat?.estado === 'em_atendimento' && meu ? (
        <View style={styles.barraTopo}>
          <Text style={styles.meta} numberOfLines={1}>
            {chat.empresa_nome || chat.protocolo}
            {chat.setor_nome ? ` · ${chat.setor_nome}` : ''}
          </Text>
          <Pressable onPress={pedirEncerrar}>
            <Text style={styles.encerrar}>Encerrar</Text>
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
        renderItem={({ item }) => <Bolha chatId={chatId} msg={item} />}
      />
      {menuAnexo && possoEnviar ? (
        <View style={styles.menuAnexo}>
          <Pressable
            style={styles.menuAnexoItem}
            onPress={() => {
              setMenuAnexo(false)
              void anexarFoto()
            }}
          >
            <Text style={styles.menuAnexoTxt}>Foto</Text>
          </Pressable>
          <Pressable
            style={styles.menuAnexoItem}
            onPress={() => {
              setMenuAnexo(false)
              void anexarArquivo()
            }}
          >
            <Text style={styles.menuAnexoTxt}>Arquivo</Text>
          </Pressable>
          <Pressable style={styles.menuAnexoItem} onPress={() => setMenuAnexo(false)}>
            <Text style={styles.menuAnexoCancelar}>Cancelar</Text>
          </Pressable>
        </View>
      ) : null}
      {possoEnviar ? (
        <View style={styles.composer}>
          <Pressable style={styles.anexo} onPress={pedirAnexo} disabled={aEnviar}>
            <Text style={styles.anexoTxt}>+</Text>
          </Pressable>
          <TextInput
            style={styles.input}
            placeholder="Mensagem"
            placeholderTextColor={colors.muted}
            value={texto}
            onChangeText={setTexto}
            multiline
            editable={!aEnviar}
            onSubmitEditing={() => void enviar()}
          />
          <Pressable
            style={[styles.enviar, (!texto.trim() || aEnviar) && styles.enviarOff]}
            onPress={() => void enviar()}
            disabled={!texto.trim() || aEnviar}
          >
            <Text style={styles.enviarTxt}>Enviar</Text>
          </Pressable>
        </View>
      ) : (
        <Text style={styles.avisoComposer}>
          {naFila ? 'Assuma o chat para responder.' : 'Só o atendente responsável pode enviar.'}
        </Text>
      )}
    </KeyboardAvoidingView>
  )
}

function Bolha({ chatId, msg }: { chatId: number; msg: WhatsappMensagem }) {
  const outbound = msg.direcao === 'outbound'
  const midia = temArquivoMidia(msg.tipo_midia)
  const corpo = msg.apagada ? 'Mensagem apagada' : midia ? msg.corpo : msg.corpo
  return (
    <View style={[styles.bolhaWrap, outbound ? styles.bolhaWrapOut : styles.bolhaWrapIn]}>
      <View style={[styles.bolha, outbound ? styles.bolhaOut : styles.bolhaIn]}>
        {outbound && msg.atendente_nome ? <Text style={styles.autor}>{msg.atendente_nome}</Text> : null}
        {midia && !msg.apagada ? (
          <WhatsappMidia
            chatId={chatId}
            mensagemId={msg.id}
            tipo={msg.tipo_midia}
            disponivel={msg.midia_disponivel}
            nome={msg.midia_nome_original}
            caption={legendaMidiaVisivel(corpo)}
            outbound={outbound}
          />
        ) : (
          <Text style={[styles.corpo, outbound ? styles.corpoOut : styles.corpoIn]}>{corpo}</Text>
        )}
        <Text style={[styles.horaBolha, outbound ? styles.horaOut : styles.horaIn]}>{horaCurta(msg.created_at)}</Text>
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#E8EEF2' },
  centro: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.deck },
  erro: { color: colors.danger, backgroundColor: colors.dangerBg, margin: 8, padding: 10, borderRadius: 8 },
  barraFila: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 12,
    backgroundColor: '#FEF3C7',
    gap: 12,
  },
  barraFilaTxt: { flex: 1, color: '#92400E', fontWeight: '600' },
  botaoAssumir: {
    backgroundColor: colors.teal,
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
    minWidth: 88,
    alignItems: 'center',
  },
  botaoAssumirTxt: { color: colors.white, fontWeight: '700' },
  barraTopo: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 8,
    backgroundColor: colors.white,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border,
  },
  meta: { flex: 1, color: colors.muted, fontSize: 13, marginRight: 12 },
  encerrar: { color: colors.danger, fontWeight: '700' },
  lista: { padding: 12, paddingBottom: 24 },
  bolhaWrap: { marginBottom: 8, maxWidth: '82%' },
  bolhaWrapIn: { alignSelf: 'flex-start' },
  bolhaWrapOut: { alignSelf: 'flex-end' },
  bolha: { borderRadius: 12, paddingHorizontal: 12, paddingVertical: 8 },
  bolhaIn: { backgroundColor: colors.white },
  bolhaOut: { backgroundColor: colors.teal },
  autor: { fontSize: 11, color: colors.white, opacity: 0.85, marginBottom: 2 },
  corpo: { fontSize: 16, lineHeight: 22 },
  corpoIn: { color: colors.text },
  corpoOut: { color: colors.white },
  horaBolha: { fontSize: 11, marginTop: 4, alignSelf: 'flex-end' },
  horaIn: { color: colors.muted },
  horaOut: { color: colors.white, opacity: 0.85 },
  composer: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: 8,
    padding: 10,
    backgroundColor: colors.white,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.border,
  },
  anexo: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: colors.navy,
    alignItems: 'center',
    justifyContent: 'center',
  },
  anexoTxt: { color: colors.white, fontSize: 22, fontWeight: '700', marginTop: -2 },
  input: {
    flex: 1,
    minHeight: 40,
    maxHeight: 120,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 20,
    paddingHorizontal: 14,
    paddingVertical: 10,
    fontSize: 16,
    color: colors.text,
    backgroundColor: colors.deck,
  },
  enviar: {
    backgroundColor: colors.teal,
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 10,
  },
  enviarOff: { opacity: 0.45 },
  enviarTxt: { color: colors.white, fontWeight: '700' },
  avisoComposer: {
    textAlign: 'center',
    color: colors.muted,
    padding: 12,
    backgroundColor: colors.white,
  },
  menuAnexo: {
    backgroundColor: colors.white,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.border,
    paddingHorizontal: 12,
    paddingTop: 8,
  },
  menuAnexoItem: { paddingVertical: 12, paddingHorizontal: 8 },
  menuAnexoTxt: { fontSize: 16, fontWeight: '600', color: colors.navy },
  menuAnexoCancelar: { fontSize: 16, color: colors.muted },
})
