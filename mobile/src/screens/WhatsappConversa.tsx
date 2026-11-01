import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  ActivityIndicator,
  Alert,
  Animated,
  Dimensions,
  FlatList,
  Image,
  Modal,
  PanResponder,
  Platform,
  Pressable,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native'
import * as DocumentPicker from 'expo-document-picker'
import * as ImagePicker from 'expo-image-picker'
import { useLocalSearchParams, useNavigation, useRouter } from 'expo-router'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import {
  ApiError,
  type WhatsappChat,
  type WhatsappInatividadeConfig,
  type WhatsappMensagem,
  type WhatsappNatureza,
  whatsapp,
} from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { Avatar } from '../components/Avatar'
import { FaixaGestoVoltar } from '../components/FaixaGestoVoltar'
import { Icon, type IconName } from '../components/Icon'
import { TelaTeclado } from '../components/TelaTeclado'
import { temArquivoMidia, WhatsappMidia } from '../components/WhatsappMidia'
import { useAlturaTeclado } from '../hooks/useAlturaTeclado'
import { useRealtimeRefresh } from '../hooks/useRealtimeRefresh'
import { radius, type Cores } from '../lib/brand'
import { useCores } from '../lib/tema'
import { horaCurta, legendaMidiaVisivel, nomeDoChat, rotuloEstado } from '../lib/format'

export function WhatsappConversa() {
  const styles = usarEstilos()
  const cores = useCores()
  const { id: idParam } = useLocalSearchParams<{ id: string }>()
  const chatId = Number(idParam)
  const navigation = useNavigation()
  const router = useRouter()
  const { me } = useAuth()
  const listRef = useRef<FlatList<WhatsappMensagem>>(null)
  const inflight = useRef<Promise<void> | null>(null)
  const colarNoFim = useRef(true)
  const alturaTeclado = useAlturaTeclado()
  useEffect(() => {
    if (alturaTeclado <= 0 || !colarNoFim.current) return
    // Mantém a última mensagem visível quando o teclado abre, mas só se o
    // atendente já estava no fim da conversa: se ele rolou para reler algo
    // acima, a posição atual é preservada.
    const id = requestAnimationFrame(() => {
      listRef.current?.scrollToEnd({ animated: false })
    })
    return () => cancelAnimationFrame(id)
  }, [alturaTeclado])
  const [chat, setChat] = useState<WhatsappChat | null>(null)
  const [mensagens, setMensagens] = useState<WhatsappMensagem[]>([])
  const [texto, setTexto] = useState('')
  const [erro, setErro] = useState<string | null>(null)
  const [aCarregar, setACarregar] = useState(true)
  const [aEnviar, setAEnviar] = useState(false)
  const [aAssumir, setAAssumir] = useState(false)
  const [menuAnexo, setMenuAnexo] = useState(false)
  const [formTicket, setFormTicket] = useState(false)
  const [assuntoTicket, setAssuntoTicket] = useState('')
  const [aAbrirTicket, setAAbrirTicket] = useState(false)
  const insets = useSafeAreaInsets()
  const [detalhes, setDetalhes] = useState(false)
  const [fotoAberta, setFotoAberta] = useState(false)
  const [menuAberto, setMenuAberto] = useState(false)
  const [empresaAberta, setEmpresaAberta] = useState(false)
  const [empresaSalvando, setEmpresaSalvando] = useState(false)
  const [demandaAberta, setDemandaAberta] = useState(false)
  const [naturezas, setNaturezas] = useState<WhatsappNatureza[]>([])
  const [naturezasErro, setNaturezasErro] = useState<string | null>(null)
  const [naturezaId, setNaturezaId] = useState<number | null>(null)
  const [demandaDescricao, setDemandaDescricao] = useState('')
  const [aRegistrarDemanda, setARegistrarDemanda] = useState(false)
  const [inatConfig, setInatConfig] = useState<WhatsappInatividadeConfig | null>(null)
  const [aPausar, setAPausar] = useState(false)
  const fotoY = useRef(new Animated.Value(0)).current
  const fotoPan = useMemo(
    () =>
      PanResponder.create({
        onMoveShouldSetPanResponder: (_, gesto) =>
          gesto.dy > 6 && Math.abs(gesto.dy) > Math.abs(gesto.dx),
        onPanResponderMove: (_, gesto) => {
          if (gesto.dy > 0) fotoY.setValue(gesto.dy)
        },
        onPanResponderRelease: (_, gesto) => {
          if (gesto.dy > 130 || gesto.vy > 1.2) {
            Animated.timing(fotoY, {
              toValue: Dimensions.get('window').height,
              duration: 180,
              useNativeDriver: true,
            }).start(() => setFotoAberta(false))
          } else {
            Animated.spring(fotoY, {
              toValue: 0,
              bounciness: 3,
              useNativeDriver: true,
            }).start()
          }
        },
        onPanResponderTerminate: () => {
          Animated.spring(fotoY, { toValue: 0, bounciness: 3, useNativeDriver: true }).start()
        },
      }),
    [fotoY],
  )

  const carregar = useCallback(
    async (silencioso = false) => {
      if (!Number.isFinite(chatId) || chatId <= 0) return
      if (inflight.current) return inflight.current
      if (!silencioso) setACarregar(true)
      const p = (async () => {
        try {
          const [c, msgs] = await Promise.all([whatsapp.get(chatId), whatsapp.mensagens(chatId)])
          setChat(c)
          setMensagens(msgs)
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

  const titulo = chat ? nomeDoChat(chat) : 'Conversa'
  const tipoFuncionario = rotuloTipoFuncionario(chat?.funcionario_tipo)
  const empresaTexto = chat?.empresa_nome
    ? chat.empresa_nome
    : chat?.funcionario_rede_id
      ? 'Sem empresa'
      : chat
        ? 'Contato sem cadastro'
        : ''
  const subtitulo = chat ? [chat.rede_nome, empresaTexto].filter(Boolean).join(' · ') : 'Carregando…'

  const naFila = chat?.estado === 'aguardando_atendente'
  const souResponsavel = chat?.atendente_id === me?.id
  const acompanhando =
    chat?.estado === 'em_atendimento' && !souResponsavel && Boolean(chat?.atendente_id)
  const possoEnviar = chat?.estado === 'em_atendimento' && souResponsavel
  const ticketIds = chat?.ticket_ids || []
  const ticketAberto = ticketIds[0]
  const empresasOpcoes = chat?.empresas_opcoes || []
  const podeRegistrarDemanda = Boolean(chat) && chat?.estado === 'em_atendimento'
  const mensagensVisiveis = useMemo(() => mensagens.filter((m) => !m.evento_sistema), [mensagens])

  useEffect(() => {
    let cancelado = false
    void whatsapp
      .configInatividade()
      .then((cfg) => {
        if (cancelado) return
        setInatConfig(cfg)
      })
      .catch(() => {
        // Sem permissão para ler as configurações do canal: esconde o contador.
        if (!cancelado) setInatConfig({ ativa: false, avisoMin: 15, posAvisoMin: 5 })
      })
    return () => {
      cancelado = true
    }
  }, [])

  const inatividade = useMemo(
    () => calcularInatividade(chat, inatConfig, mensagens, Date.now()),
    [chat, inatConfig, mensagens],
  )

  useEffect(() => {
    navigation.setOptions({
      title: titulo,
      headerTitle: () => (
        <View style={styles.tituloHeaderWrap}>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Ver foto do contato"
            accessibilityState={{ disabled: !chat?.foto_perfil_url }}
            disabled={!chat?.foto_perfil_url}
            hitSlop={6}
            onPress={() => {
              fotoY.setValue(0)
              setFotoAberta(true)
            }}
          >
            <Avatar nome={titulo} fotoUrl={chat?.foto_perfil_url} size={32} />
          </Pressable>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Ver detalhes do contato"
            accessibilityHint="Mostra tipo de vínculo e empresa deste contato"
            disabled={!chat}
            onPress={() => setDetalhes(true)}
            style={({ pressed }) => [
              styles.tituloHeaderTextos,
              pressed && styles.tituloHeaderPressed,
            ]}
          >
            <Text numberOfLines={1} style={styles.tituloHeader}>
              {titulo}
            </Text>
            {subtitulo ? (
              <Text numberOfLines={1} style={styles.subtituloHeader}>
                {subtitulo}
              </Text>
            ) : null}
          </Pressable>
        </View>
      ),
      headerRight: () => (
        <View style={styles.headerAcoes}>
          <ContadorInatividade
            chat={chat}
            config={inatConfig}
            mensagens={mensagens}
            onPress={() => setMenuAberto(true)}
          />
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Mais ações desta conversa"
            hitSlop={10}
            onPress={() => setMenuAberto(true)}
            style={({ pressed }) => [styles.acaoHeader, pressed && styles.acaoHeaderPressed]}
          >
            <Icon name="ellipsis-vertical" size={20} color={cores.navy} />
          </Pressable>
        </View>
      ),
    })
  }, [chat, inatConfig, mensagens, navigation, subtitulo, titulo])

  async function alternarPausa() {
    if (!chat) return
    setAPausar(true)
    try {
      const c = chat.inatividade_pausada
        ? await whatsapp.retomarInatividade(chatId)
        : await whatsapp.pausarInatividade(chatId)
      setChat(c)
      setErro(null)
      setMenuAberto(false)
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : 'Não foi possível alterar a pausa de inatividade.')
    } finally {
      setAPausar(false)
    }
  }

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

  function abrirFormTicket() {
    if (!chat) return
    if (!chat.empresa_id || !chat.setor_id) {
      setErro('Este chat não tem empresa ou setor. Abra o ticket pelo painel.')
      return
    }
    setAssuntoTicket(`Atendimento — ${nomeDoChat(chat)}`)
    setFormTicket(true)
    setErro(null)
  }

  async function confirmarAbrirTicket() {
    if (!chat?.empresa_id || !chat.setor_id || !assuntoTicket.trim()) return
    setAAbrirTicket(true)
    try {
      const atualizado = await whatsapp.abrirTicket(chatId, {
        empresa_id: chat.empresa_id,
        setor_id: chat.setor_id,
        assunto: assuntoTicket.trim(),
      })
      setChat(atualizado)
      setFormTicket(false)
      const novo = (atualizado.ticket_ids || []).find((id) => !ticketIds.includes(id))
      if (novo) router.push(`/ticket/${novo}`)
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : 'Não foi possível abrir o ticket.')
    } finally {
      setAAbrirTicket(false)
    }
  }

  function abrirEmpresa() {
    setMenuAberto(false)
    if (!chat?.funcionario_rede_id) {
      setErro('Este contato ainda não tem funcionário vinculado — vincule no painel.')
      return
    }
    if (empresasOpcoes.length === 0) {
      setErro('Nenhuma empresa no cadastro deste contato para vincular.')
      return
    }
    setErro(null)
    setEmpresaAberta(true)
  }

  async function escolherEmpresa(empresaId: number) {
    if (empresaSalvando) return
    setEmpresaSalvando(true)
    try {
      const atualizado = await whatsapp.definirEmpresa(chatId, empresaId)
      setChat(atualizado)
      setEmpresaAberta(false)
      setErro(null)
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : 'Não foi possível definir a empresa.')
    } finally {
      setEmpresaSalvando(false)
    }
  }

  async function abrirDemanda() {
    setMenuAberto(false)
    setDemandaAberta(true)
    setNaturezaId(null)
    setDemandaDescricao('')
    setNaturezasErro(null)
    if (naturezas.length > 0) return
    try {
      const resposta = await whatsapp.naturezas()
      setNaturezas(resposta.items)
    } catch (e) {
      setNaturezasErro(
        e instanceof ApiError ? e.message : 'Não foi possível carregar as naturezas.',
      )
    }
  }

  async function confirmarDemanda() {
    if (!naturezaId || aRegistrarDemanda) return
    setARegistrarDemanda(true)
    try {
      await whatsapp.registrarDemanda(chatId, {
        natureza_id: naturezaId,
        descricao_curta: demandaDescricao.trim() || undefined,
      })
      setDemandaAberta(false)
      Alert.alert('Demanda registrada', 'A classificação ficou salva nesta conversa.')
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : 'Não foi possível registrar a demanda.')
    } finally {
      setARegistrarDemanda(false)
    }
  }

  function acaoTicket() {
    setMenuAberto(false)
    if (ticketAberto) {
      router.push(`/ticket/${ticketAberto}`)
      return
    }
    abrirFormTicket()
  }

  function acaoEncerrar() {
    setMenuAberto(false)
    pedirEncerrar()
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
        <ActivityIndicator color={cores.teal} />
        <FaixaGestoVoltar fallback="/chat" />
      </View>
    )
  }

  return (
    <View style={styles.root}>
    <TelaTeclado offset={88} corRodape={cores.white} folga={22}>
      {erro ? <Text style={styles.erro}>{erro}</Text> : null}
      {naFila ? (
        <View style={styles.barraFila}>
          <View style={{ flex: 1 }}>
            <Text style={styles.barraFilaTitulo}>Na fila</Text>
            <Text style={styles.barraFilaTxt}>Assuma para responder ao cliente.</Text>
          </View>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Assumir"
            style={styles.botaoAssumir}
            onPress={() => void assumir()}
            disabled={aAssumir}
          >
            {aAssumir ? (
              <ActivityIndicator color={cores.sobre} />
            ) : (
              <Text style={styles.botaoAssumirTxt}>Assumir</Text>
            )}
          </Pressable>
        </View>
      ) : null}
      {acompanhando ? (
        <View style={styles.barraFila}>
          <View style={{ flex: 1 }}>
            <Text style={styles.barraFilaTitulo}>Acompanhando</Text>
            <Text style={styles.barraFilaTxt}>
              Chat com {chat?.atendente_nome || 'outro atendente'}. Você pode ler, mas não enviar ao
              cliente.
            </Text>
          </View>
        </View>
      ) : null}
      {formTicket ? (
        <View style={styles.formTicket}>
          <Text style={styles.formTicketTitulo}>Abrir ticket deste chat</Text>
          <Text style={styles.formTicketMeta}>
            {chat?.empresa_nome} · {chat?.setor_nome}
          </Text>
          <TextInput
            style={styles.formTicketInput}
            value={assuntoTicket}
            onChangeText={setAssuntoTicket}
            placeholder="Assunto"
            placeholderTextColor={cores.muted}
          />
          <View style={styles.formTicketAcoes}>
            <Pressable onPress={() => setFormTicket(false)} disabled={aAbrirTicket}>
              <Text style={styles.menuAnexoCancelar}>Cancelar</Text>
            </Pressable>
            <Pressable
              style={[styles.botaoAssumir, (!assuntoTicket.trim() || aAbrirTicket) && { opacity: 0.5 }]}
              onPress={() => void confirmarAbrirTicket()}
              disabled={!assuntoTicket.trim() || aAbrirTicket}
            >
              {aAbrirTicket ? (
                <ActivityIndicator color={cores.sobre} />
              ) : (
                <Text style={styles.botaoAssumirTxt}>Abrir</Text>
              )}
            </Pressable>
          </View>
        </View>
      ) : null}
      <FlatList
        ref={listRef}
        data={mensagensVisiveis}
        keyExtractor={(m) => String(m.id)}
        contentContainerStyle={styles.lista}
        keyboardShouldPersistTaps="handled"
        keyboardDismissMode="on-drag"
        onScroll={(e) => {
          const { contentOffset, layoutMeasurement, contentSize } = e.nativeEvent
          colarNoFim.current = contentOffset.y + layoutMeasurement.height >= contentSize.height - 120
        }}
        scrollEventThrottle={16}
        onContentSizeChange={() => {
          if (colarNoFim.current) listRef.current?.scrollToEnd({ animated: false })
        }}
        onLayout={() => {
          // Quando o teclado (ou o composer) muda a altura da lista, acompanha
          // o fim se o atendente estava colado na última mensagem.
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
            <Icon name="image-outline" size={20} color={cores.navy} />
            <Text style={styles.menuAnexoTxt}>Foto</Text>
          </Pressable>
          <Pressable
            style={styles.menuAnexoItem}
            onPress={() => {
              setMenuAnexo(false)
              void anexarArquivo()
            }}
          >
            <Icon name="document-outline" size={20} color={cores.navy} />
            <Text style={styles.menuAnexoTxt}>Arquivo</Text>
          </Pressable>
          <Pressable style={styles.menuAnexoItem} onPress={() => setMenuAnexo(false)}>
            <Text style={styles.menuAnexoCancelar}>Cancelar</Text>
          </Pressable>
        </View>
      ) : null}
      {possoEnviar ? (
        <View style={styles.composer}>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Anexar"
            style={styles.anexo}
            onPress={pedirAnexo}
            disabled={aEnviar}
          >
            <Icon name="attach" size={22} color={cores.navyMid} />
          </Pressable>
          <TextInput
            style={styles.input}
            placeholder="Mensagem"
            placeholderTextColor={cores.muted}
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
            <Icon name="send" size={18} color={cores.sobre} />
          </Pressable>
        </View>
      ) : (
        <Text style={styles.avisoComposer}>
          {naFila
            ? 'Assuma o chat para responder.'
            : acompanhando
              ? `Este chat está com ${chat?.atendente_nome || 'outro atendente'}.`
              : 'Só o atendente responsável pode enviar.'}
        </Text>
      )}
    </TelaTeclado>
    <FaixaGestoVoltar fallback="/chat" />

    <Modal
      visible={detalhes}
      transparent
      animationType="fade"
      onRequestClose={() => setDetalhes(false)}
    >
      <View style={styles.modalFundo}>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Fechar detalhes"
          style={StyleSheet.absoluteFill}
          onPress={() => setDetalhes(false)}
        />
        <View style={[styles.detalhes, { paddingBottom: insets.bottom + 20 }]}>
          <View style={styles.detalhesTopo}>
            <Avatar nome={titulo} fotoUrl={chat?.foto_perfil_url} size={56} />
            <View style={{ flex: 1 }}>
              <Text style={styles.detalhesNome} numberOfLines={2}>
                {titulo}
              </Text>
              {tipoFuncionario ? <Text style={styles.detalhesTipo}>{tipoFuncionario}</Text> : null}
            </View>
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Fechar"
              hitSlop={10}
              onPress={() => setDetalhes(false)}
            >
              <Icon name="close" size={22} color={cores.muted} />
            </Pressable>
          </View>
          {chat?.funcionario_email ? (
            <LinhaDetalhe rotulo="E-mail" valor={chat.funcionario_email} />
          ) : null}
          <LinhaDetalhe rotulo="Rede" valor={chat?.rede_nome || '—'} />
          <LinhaDetalhe
            rotulo="Empresa"
            valor={chat?.empresa_nome || empresaTexto || 'Sem empresa'}
          />
          {empresasOpcoes.length > 1 ? (
            <LinhaDetalhe
              rotulo="Empresas no cadastro"
              valor={empresasOpcoes.map((e) => e.nome).join(' · ')}
            />
          ) : null}
          <LinhaDetalhe rotulo="Protocolo" valor={chat?.protocolo || '—'} />
          <LinhaDetalhe rotulo="Situação" valor={chat ? rotuloEstado(chat.estado) : '—'} />
        </View>
      </View>
    </Modal>

    <Modal
      visible={fotoAberta}
      transparent
      animationType="fade"
      onRequestClose={() => setFotoAberta(false)}
    >
      <View style={styles.fotoFundo}>
        <View style={[styles.fotoTopo, { paddingTop: Math.max(insets.top, StatusBar.currentHeight ?? 0) + 8 }]}>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Fechar foto"
            hitSlop={10}
            onPress={() => setFotoAberta(false)}
            style={({ pressed }) => [styles.fotoFechar, pressed && styles.fotoFecharPressed]}
          >
            <Icon name="close" size={24} color={cores.sobre} />
          </Pressable>
        </View>
        <Animated.View
          style={[styles.fotoArea, { transform: [{ translateY: fotoY }] }]}
          {...fotoPan.panHandlers}
        >
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Fechar foto"
            style={styles.fotoArea}
            onPress={() => setFotoAberta(false)}
          >
            {chat?.foto_perfil_url ? (
              <Image
                source={{ uri: chat.foto_perfil_url }}
                style={styles.fotoGrande}
                resizeMode="contain"
              />
            ) : null}
          </Pressable>
        </Animated.View>
      </View>
    </Modal>

    <Modal
      visible={menuAberto}
      transparent
      animationType="fade"
      onRequestClose={() => setMenuAberto(false)}
    >
      <View style={styles.modalFundo}>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Fechar menu"
          style={StyleSheet.absoluteFill}
          onPress={() => setMenuAberto(false)}
        />
        <View style={styles.menuCentro}>
          <View style={styles.menu}>
            <Text style={styles.menuTitulo}>Ações da conversa</Text>
            {inatividade && souResponsavel && !inatividade.posAviso ? (
              <>
                <OpcaoMenu
                  icone={chat?.inatividade_pausada ? 'play-circle-outline' : 'pause-circle-outline'}
                  titulo={chat?.inatividade_pausada ? 'Retomar inatividade' : 'Pausar inatividade'}
                  onPress={() => void alternarPausa()}
                  desabilitado={aPausar}
                />
                <View style={styles.menuDivisor} />
              </>
            ) : null}
            <OpcaoMenu
              icone="business-outline"
              titulo={chat?.empresa_id ? 'Alterar empresa' : 'Vincular empresa'}
              onPress={abrirEmpresa}
              desabilitado={!chat || chat.estado === 'encerrado'}
            />
            <OpcaoMenu
              icone="clipboard-outline"
              titulo="Registrar demanda"
              onPress={() => void abrirDemanda()}
              desabilitado={!podeRegistrarDemanda}
            />
            <OpcaoMenu
              icone={ticketAberto ? 'ticket-outline' : 'add-circle-outline'}
              titulo={ticketAberto ? `Ver ticket #${ticketAberto}` : 'Abrir ticket'}
              onPress={acaoTicket}
              desabilitado={!chat || chat.estado === 'encerrado'}
            />
            <View style={styles.menuDivisor} />
            <OpcaoMenu
              icone="close-circle-outline"
              titulo="Encerrar atendimento"
              onPress={acaoEncerrar}
              perigo
              desabilitado={!possoEnviar}
            />
          </View>
        </View>
      </View>
    </Modal>

    <Modal
      visible={empresaAberta}
      transparent
      animationType="slide"
      onRequestClose={() => setEmpresaAberta(false)}
    >
      <View style={styles.sheetFundo}>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Fechar"
          style={StyleSheet.absoluteFill}
          onPress={() => setEmpresaAberta(false)}
        />
        <View style={[styles.sheet, { paddingBottom: insets.bottom + 16 }]}>
          <Text style={styles.sheetTitulo}>Empresa do atendimento</Text>
          <Text style={styles.sheetTxt}>
            Escolha a empresa deste contato para vincular a conversa.
          </Text>
          <ScrollView style={{ maxHeight: 320 }} showsVerticalScrollIndicator={false}>
            {empresasOpcoes.map((e) => {
              const ativa = e.id === chat?.empresa_id
              return (
                <Pressable
                  key={e.id}
                  accessibilityRole="button"
                  accessibilityState={{ selected: ativa }}
                  disabled={empresaSalvando}
                  onPress={() => void escolherEmpresa(e.id)}
                  style={({ pressed }) => [
                    styles.opcaoEmpresa,
                    ativa && styles.opcaoEmpresaAtiva,
                    pressed && !empresaSalvando && styles.opcaoEmpresaPressed,
                  ]}
                >
                  <Text style={styles.opcaoEmpresaTxt} numberOfLines={2}>
                    {e.nome}
                  </Text>
                  {ativa ? (
                    <Icon name="checkmark-circle" size={20} color={cores.teal} />
                  ) : null}
                </Pressable>
              )
            })}
          </ScrollView>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Cancelar"
            style={styles.sheetCancelar}
            onPress={() => setEmpresaAberta(false)}
          >
            <Text style={styles.sheetCancelarTxt}>Cancelar</Text>
          </Pressable>
        </View>
      </View>
    </Modal>

    <Modal
      visible={demandaAberta}
      transparent
      animationType="slide"
      onRequestClose={() => setDemandaAberta(false)}
    >
      <View style={styles.sheetFundo}>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Fechar"
          style={StyleSheet.absoluteFill}
          onPress={() => setDemandaAberta(false)}
        />
        <View style={[styles.sheet, { paddingBottom: insets.bottom + 16 }]}>
          <Text style={styles.sheetTitulo}>Registrar demanda</Text>
          <Text style={styles.sheetTxt}>
            Classifique o que o cliente procurou neste atendimento.
          </Text>
          {naturezasErro ? <Text style={styles.erro}>{naturezasErro}</Text> : null}
          {naturezas.length === 0 && !naturezasErro ? (
            <ActivityIndicator color={cores.teal} style={{ marginVertical: 16 }} />
          ) : (
            <View style={styles.naturezas}>
              {naturezas.map((n) => {
                const ativa = n.id === naturezaId
                return (
                  <Pressable
                    key={n.id}
                    accessibilityRole="button"
                    accessibilityState={{ selected: ativa }}
                    onPress={() => setNaturezaId(n.id)}
                    style={[styles.natureza, ativa && styles.naturezaAtiva]}
                  >
                    <Text style={[styles.naturezaTxt, ativa && styles.naturezaTxtAtiva]}>
                      {n.nome}
                    </Text>
                  </Pressable>
                )
              })}
            </View>
          )}
          <TextInput
            style={styles.demandaInput}
            value={demandaDescricao}
            onChangeText={setDemandaDescricao}
            placeholder="Descrição (opcional)"
            placeholderTextColor={cores.muted}
            maxLength={500}
            multiline
          />
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Registrar demanda"
            style={[styles.botaoAssumir, (!naturezaId || aRegistrarDemanda) && { opacity: 0.5 }]}
            onPress={() => void confirmarDemanda()}
            disabled={!naturezaId || aRegistrarDemanda}
          >
            {aRegistrarDemanda ? (
              <ActivityIndicator color={cores.sobre} />
            ) : (
              <Text style={styles.botaoAssumirTxt}>Registrar</Text>
            )}
          </Pressable>
        </View>
      </View>
    </Modal>
    </View>
  )
}

function Bolha({ chatId, msg }: { chatId: number; msg: WhatsappMensagem }) {
  const styles = usarEstilos()
  const outbound = msg.direcao === 'outbound'
  const midia = temArquivoMidia(msg.tipo_midia)
  const corpo = msg.apagada ? 'Mensagem apagada' : midia ? msg.corpo : msg.corpo
  return (
    <View style={[styles.bolhaWrap, outbound ? styles.bolhaWrapOut : styles.bolhaWrapIn]}>
      <View style={[styles.bolha, outbound ? styles.bolhaOut : styles.bolhaIn]}>
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

function rotuloTipoFuncionario(tipo?: string | null): string | null {
  if (!tipo) return null
  if (tipo === 'socio') return 'Sócio'
  if (tipo === 'supervisor') return 'Supervisor'
  if (tipo === 'colaborador') return 'Colaborador'
  return tipo
}

function formatarContagem(totalSegundos: number): string {
  const s = Math.max(0, Math.floor(totalSegundos))
  const mm = String(Math.floor(s / 60)).padStart(2, '0')
  const ss = String(s % 60).padStart(2, '0')
  return `${mm}:${ss}`
}

type FaseInatividade = { restante: number; pausada: boolean; posAviso: boolean }

function calcularInatividade(
  chat: WhatsappChat | null,
  config: WhatsappInatividadeConfig | null,
  mensagens: WhatsappMensagem[],
  agoraMs: number,
): FaseInatividade | null {
  if (!config?.ativa || chat?.estado !== 'em_atendimento') return null
  if (chat.inatividade_pausada) {
    // Pausado: mostra o prazo cheio até o aviso, sem contar.
    return { restante: config.avisoMin * 60, pausada: true, posAviso: false }
  }
  // Só atividade humana reinicia o ciclo — marcos de sistema/demanda não (#712).
  const humanas = mensagens.filter(
    (m) => m.direcao === 'inbound' || (m.direcao === 'outbound' && !m.evento_sistema),
  )
  const ultima = humanas[humanas.length - 1]
  const candidatos: number[] = []
  if (ultima?.created_at) candidatos.push(new Date(ultima.created_at).getTime())
  if (chat.inatividade_retomada_em) {
    candidatos.push(new Date(chat.inatividade_retomada_em).getTime())
  }
  const referencia = candidatos.length > 0 ? Math.max(...candidatos) : 0
  const avisos = mensagens.filter((m) => m.evento_sistema === 'auto_inativ_aviso' && m.created_at)
  const ultimoAviso = avisos[avisos.length - 1]
  const avisoMs = ultimoAviso?.created_at ? new Date(ultimoAviso.created_at).getTime() : 0
  if (avisoMs > 0 && avisoMs >= referencia) {
    return {
      restante: Math.max(0, config.posAvisoMin * 60 - (agoraMs - avisoMs) / 1000),
      pausada: false,
      posAviso: true,
    }
  }
  if (referencia === 0) {
    return { restante: config.avisoMin * 60, pausada: false, posAviso: false }
  }
  return {
    restante: Math.max(0, config.avisoMin * 60 - (agoraMs - referencia) / 1000),
    pausada: false,
    posAviso: false,
  }
}

function ContadorInatividade({
  chat,
  config,
  mensagens,
  onPress,
}: {
  chat: WhatsappChat | null
  config: WhatsappInatividadeConfig | null
  mensagens: WhatsappMensagem[]
  onPress: () => void
}) {
  const styles = usarEstilos()
  const cores = useCores()
  const [agora, setAgora] = useState(() => Date.now())

  // O relógio fica isolado aqui para não re-renderizar a lista de mensagens a cada segundo.
  useEffect(() => {
    const id = setInterval(() => setAgora(Date.now()), 1000)
    return () => clearInterval(id)
  }, [])

  const fase = useMemo(
    () => calcularInatividade(chat, config, mensagens, agora),
    [agora, chat, config, mensagens],
  )
  if (!fase) return null

  const cor = fase.pausada
    ? cores.warning
    : fase.posAviso || fase.restante <= 60
      ? cores.danger
      : cores.muted

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`Tempo de inatividade restante: ${formatarContagem(fase.restante)}`}
      accessibilityHint="Abre o menu com a opção de pausar o atendimento"
      hitSlop={8}
      onPress={onPress}
      style={({ pressed }) => [styles.contadorHeader, pressed && styles.contadorHeaderPressed]}
    >
      <Icon name={fase.pausada ? 'pause-circle-outline' : 'time-outline'} size={13} color={cor} />
      <Text style={[styles.contadorHeaderTexto, { color: cor }]}>
        {formatarContagem(fase.restante)}
      </Text>
    </Pressable>
  )
}

function LinhaDetalhe({ rotulo, valor }: { rotulo: string; valor: string }) {
  const styles = usarEstilos()
  return (
    <View style={styles.linhaDetalhe}>
      <Text style={styles.linhaRotulo}>{rotulo}</Text>
      <Text style={styles.linhaValor} numberOfLines={2}>
        {valor}
      </Text>
    </View>
  )
}

function OpcaoMenu({
  icone,
  titulo,
  onPress,
  desabilitado,
  perigo,
}: {
  icone: IconName
  titulo: string
  onPress: () => void
  desabilitado?: boolean
  perigo?: boolean
}) {
  const styles = usarEstilos()
  const cores = useCores()
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ disabled: Boolean(desabilitado) }}
      disabled={desabilitado}
      onPress={onPress}
      style={({ pressed }) => [
        styles.opcaoMenu,
        pressed && !desabilitado && styles.opcaoMenuPressed,
        desabilitado && styles.opcaoMenuOff,
      ]}
    >
      <Icon name={icone} size={18} color={perigo ? cores.danger : cores.navy} />
      <Text style={[styles.opcaoMenuTxt, perigo && styles.opcaoMenuPerigo]}>{titulo}</Text>
    </Pressable>
  )
}


function usarEstilos() {
  const cores = useCores()
  return useMemo(() => criarEstilos(cores), [cores])
}

function criarEstilos(cores: Cores) {
  return StyleSheet.create({
    root: { flex: 1, backgroundColor: cores.chatBg },
    centro: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: cores.deck },
    erro: { color: cores.danger, backgroundColor: cores.dangerBg, margin: 8, padding: 10, borderRadius: radius.md },
    barraFila: {
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'space-between',
      margin: 12,
      padding: 14,
      backgroundColor: cores.warningBg,
      borderRadius: radius.md,
      gap: 12,
    },
    barraFilaTitulo: { color: cores.warning, fontWeight: '700', fontSize: 14 },
    barraFilaTxt: { color: cores.warning, fontSize: 13, marginTop: 2 },
    botaoAssumir: {
      backgroundColor: cores.teal,
      paddingHorizontal: 16,
      paddingVertical: 10,
      borderRadius: radius.full,
      minWidth: 96,
      alignItems: 'center',
    },
    botaoAssumirTxt: { color: cores.sobre, fontWeight: '700' },
    tituloHeaderWrap: {
      flexDirection: 'row',
      alignItems: 'center',
      gap: 8,
      maxWidth: 230,
      paddingVertical: 2,
    },
    tituloHeaderPressed: { opacity: 0.6 },
    tituloHeaderTextos: { flexShrink: 1, paddingVertical: 2 },
    tituloHeader: { fontSize: 16, fontWeight: '700', color: cores.navy },
    subtituloHeader: { fontSize: 12, color: cores.muted, marginTop: 1 },
    acaoHeader: {
      width: 36,
      height: 36,
      borderRadius: radius.full,
      alignItems: 'center',
      justifyContent: 'center',
    },
    acaoHeaderPressed: { backgroundColor: cores.deck },
    modalFundo: { flex: 1, backgroundColor: 'rgba(11,45,74,0.35)' },
    detalhes: {
      position: 'absolute',
      left: 12,
      right: 12,
      bottom: 12,
      backgroundColor: cores.white,
      borderRadius: radius.xl,
      padding: 18,
      shadowColor: cores.navy,
      shadowOpacity: 0.18,
      shadowRadius: 24,
      shadowOffset: { width: 0, height: 10 },
      elevation: 12,
    },
    detalhesTopo: { flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 10 },
    detalhesNome: { fontSize: 18, fontWeight: '700', color: cores.navy },
    detalhesTipo: { fontSize: 13, fontWeight: '600', color: cores.teal, marginTop: 2 },
    fotoFundo: {
      flex: 1,
      backgroundColor: 'rgba(0,0,0,0.94)',
    },
    fotoTopo: {
      paddingHorizontal: 16,
      paddingBottom: 8,
      alignItems: 'flex-end',
    },
    fotoArea: { flex: 1 },
    fotoGrande: { flex: 1, width: '100%' },
    fotoFechar: {
      width: 44,
      height: 44,
      borderRadius: 22,
      backgroundColor: 'rgba(255,255,255,0.14)',
      alignItems: 'center',
      justifyContent: 'center',
    },
    fotoFecharPressed: { backgroundColor: 'rgba(255,255,255,0.24)' },
    linhaDetalhe: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      gap: 16,
      paddingVertical: 8,
      borderTopWidth: StyleSheet.hairlineWidth,
      borderTopColor: cores.border,
    },
    linhaRotulo: { fontSize: 13, color: cores.muted },
    linhaValor: { fontSize: 14, fontWeight: '500', color: cores.text, flexShrink: 1, textAlign: 'right' },
    menuCentro: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24 },
    menu: {
      width: '100%',
      maxWidth: 360,
      backgroundColor: cores.white,
      borderRadius: radius.xl,
      paddingVertical: 8,
      shadowColor: cores.navy,
      shadowOpacity: 0.18,
      shadowRadius: 24,
      shadowOffset: { width: 0, height: 10 },
      elevation: 12,
    },
    menuTitulo: {
      fontSize: 12,
      fontWeight: '700',
      letterSpacing: 0.4,
      textTransform: 'uppercase',
      color: cores.muted,
      paddingHorizontal: 16,
      paddingTop: 12,
      paddingBottom: 8,
    },
    headerAcoes: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingRight: 4 },
    contadorHeader: {
      flexDirection: 'row',
      alignItems: 'center',
      gap: 3,
      paddingHorizontal: 7,
      paddingVertical: 3,
      borderRadius: 999,
      backgroundColor: cores.deck,
    },
    contadorHeaderPressed: { opacity: 0.6 },
    contadorHeaderTexto: { fontSize: 12, fontWeight: '700', fontVariant: ['tabular-nums'] },
    opcaoMenu: {
      flexDirection: 'row',
      alignItems: 'center',
      gap: 10,
      paddingHorizontal: 14,
      paddingVertical: 12,
    },
    opcaoMenuPressed: { backgroundColor: cores.deck },
    opcaoMenuOff: { opacity: 0.4 },
    opcaoMenuTxt: { fontSize: 15, fontWeight: '500', color: cores.text },
    opcaoMenuPerigo: { color: cores.danger },
    menuDivisor: {
      height: StyleSheet.hairlineWidth,
      backgroundColor: cores.border,
      marginVertical: 4,
    },
    sheetFundo: { flex: 1, justifyContent: 'flex-end', backgroundColor: 'rgba(11,45,74,0.35)' },
    sheet: {
      backgroundColor: cores.white,
      borderTopLeftRadius: radius.xl,
      borderTopRightRadius: radius.xl,
      padding: 18,
      gap: 10,
    },
    sheetTitulo: { fontSize: 18, fontWeight: '700', color: cores.navy },
    sheetTxt: { fontSize: 14, color: cores.muted, lineHeight: 20 },
    opcaoEmpresa: {
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: 12,
      padding: 14,
      borderRadius: radius.md,
      borderWidth: 1,
      borderColor: cores.border,
      backgroundColor: cores.white,
      marginBottom: 8,
    },
    opcaoEmpresaAtiva: { backgroundColor: cores.tealSoft, borderColor: cores.teal },
    opcaoEmpresaPressed: { backgroundColor: cores.deck },
    opcaoEmpresaTxt: { flex: 1, fontSize: 15, fontWeight: '500', color: cores.text },
    sheetCancelar: { alignItems: 'center', paddingVertical: 12, marginTop: 2 },
    sheetCancelarTxt: { fontSize: 15, fontWeight: '600', color: cores.muted },
    naturezas: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginVertical: 4 },
    natureza: {
      paddingHorizontal: 12,
      paddingVertical: 8,
      borderRadius: radius.full,
      borderWidth: 1,
      borderColor: cores.border,
      backgroundColor: cores.deck,
    },
    naturezaAtiva: { backgroundColor: cores.tealSoft, borderColor: cores.teal },
    naturezaTxt: { fontSize: 13, fontWeight: '500', color: cores.text },
    naturezaTxtAtiva: { color: cores.tealDark, fontWeight: '700' },
    demandaInput: {
      minHeight: 72,
      maxHeight: 120,
      borderWidth: 1,
      borderColor: cores.border,
      borderRadius: radius.md,
      padding: 12,
      fontSize: 15,
      color: cores.text,
      backgroundColor: cores.deck,
      textAlignVertical: 'top',
    },
    formTicket: {
      padding: 14,
      backgroundColor: cores.white,
      borderBottomWidth: StyleSheet.hairlineWidth,
      borderBottomColor: cores.border,
      gap: 8,
    },
    formTicketTitulo: { fontSize: 15, fontWeight: '700', color: cores.navy },
    formTicketMeta: { fontSize: 13, color: cores.muted },
    formTicketInput: {
      borderWidth: 1,
      borderColor: cores.border,
      borderRadius: radius.md,
      paddingHorizontal: 12,
      paddingVertical: 10,
      fontSize: 16,
      color: cores.text,
      backgroundColor: cores.deck,
    },
    formTicketAcoes: { flexDirection: 'row', alignItems: 'center', justifyContent: 'flex-end', gap: 16 },
    lista: { padding: 12, paddingBottom: 24 },
    bolhaWrap: { marginBottom: 6, maxWidth: '82%' },
    bolhaWrapIn: { alignSelf: 'flex-start' },
    bolhaWrapOut: { alignSelf: 'flex-end' },
    bolha: { borderRadius: 16, paddingHorizontal: 12, paddingVertical: 8 },
    bolhaIn: { backgroundColor: cores.bolhaIn, borderBottomLeftRadius: 4 },
    bolhaOut: { backgroundColor: cores.teal, borderBottomRightRadius: 4 },
    corpo: { fontSize: 16, lineHeight: 22 },
    corpoIn: { color: cores.text },
    corpoOut: { color: cores.sobre },
    horaBolha: { fontSize: 11, marginTop: 4, alignSelf: 'flex-end' },
    horaIn: { color: cores.muted },
    horaOut: { color: cores.sobre, opacity: 0.85 },
    composer: {
      flexDirection: 'row',
      alignItems: 'flex-end',
      gap: 8,
      paddingHorizontal: 10,
      paddingVertical: 10,
      backgroundColor: cores.white,
      borderTopWidth: StyleSheet.hairlineWidth,
      borderTopColor: cores.border,
    },
    anexo: {
      width: 40,
      height: 40,
      borderRadius: 20,
      backgroundColor: cores.deck,
      alignItems: 'center',
      justifyContent: 'center',
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
      color: cores.text,
      backgroundColor: cores.deck,
    },
    enviar: {
      width: 40,
      height: 40,
      borderRadius: 20,
      backgroundColor: cores.teal,
      alignItems: 'center',
      justifyContent: 'center',
    },
    enviarOff: { opacity: 0.4 },
    avisoComposer: {
      textAlign: 'center',
      color: cores.muted,
      padding: 14,
      backgroundColor: cores.white,
    },
    menuAnexo: {
      backgroundColor: cores.white,
      borderTopWidth: StyleSheet.hairlineWidth,
      borderTopColor: cores.border,
      paddingHorizontal: 8,
      paddingTop: 4,
    },
    menuAnexoItem: {
      flexDirection: 'row',
      alignItems: 'center',
      gap: 10,
      paddingVertical: 12,
      paddingHorizontal: 10,
    },
    menuAnexoTxt: { fontSize: 16, fontWeight: '600', color: cores.navy },
    menuAnexoCancelar: { fontSize: 16, color: cores.muted },

  })
}
