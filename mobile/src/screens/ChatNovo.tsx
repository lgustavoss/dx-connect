import { useEffect, useState } from 'react'
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native'
import { useRouter } from 'expo-router'

import { ApiError, type SetorResumo, type WhatsappContato, setores, whatsapp } from '../api/client'
import { FaixaGestoVoltar } from '../components/FaixaGestoVoltar'
import { colors, radius } from '../lib/brand'

export function ChatNovo() {
  const router = useRouter()
  const [busca, setBusca] = useState('')
  const [contato, setContato] = useState<WhatsappContato | null>(null)
  const [contatos, setContatos] = useState<WhatsappContato[]>([])
  const [aBuscar, setABuscar] = useState(false)
  const [mensagem, setMensagem] = useState('')
  const [setorId, setSetorId] = useState<number | null>(null)
  const [setoresLista, setSetoresLista] = useState<SetorResumo[]>([])
  const [aCarregarSetores, setACarregarSetores] = useState(true)
  const [erroSetores, setErroSetores] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  const [aEnviar, setAEnviar] = useState(false)

  const setoresOpcoes = [...setoresLista].sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR'))
  const escolherSetor = setoresOpcoes.length > 1

  useEffect(() => {
    let cancelado = false
    setACarregarSetores(true)
    setErroSetores(false)
    void setores
      .listar()
      .then((r) => {
        if (cancelado) return
        const items = (r.items || []).filter((s) => s.ativo !== false)
        setSetoresLista(items)
        if (items.length === 1) setSetorId(items[0].id)
      })
      .catch(() => {
        if (!cancelado) {
          setSetoresLista([])
          setErroSetores(true)
        }
      })
      .finally(() => {
        if (!cancelado) setACarregarSetores(false)
      })
    return () => {
      cancelado = true
    }
  }, [])

  useEffect(() => {
    if (contato) return
    const q = busca.trim()
    if (q.length < 2) {
      setContatos([])
      return
    }
    const t = setTimeout(() => {
      setABuscar(true)
      void whatsapp
        .contatos(q)
        .then((r) => setContatos(r.items || []))
        .catch(() => setContatos([]))
        .finally(() => setABuscar(false))
    }, 320)
    return () => clearTimeout(t)
  }, [busca, contato])

  async function confirmar() {
    setErro(null)
    const digits = busca.replace(/\D/g, '')
    const telefone = contato?.telefone?.replace(/\D/g, '') || digits
    if (!contato && !telefone) {
      setErro('Informe o número ou escolha um contato.')
      return
    }
    if (escolherSetor && setorId == null) {
      setErro('Selecione o setor deste atendimento.')
      return
    }
    if (erroSetores && escolherSetor) {
      setErro('Não foi possível carregar os setores. Volte e tente de novo.')
      return
    }
    setAEnviar(true)
    try {
      const chat = await whatsapp.iniciar({
        funcionario_id: contato?.id,
        telefone: telefone || undefined,
        mensagem_inicial: mensagem.trim() || undefined,
        setor_id: setorId ?? undefined,
      })
      router.replace(`/conversa/${chat.id}`)
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : 'Não foi possível iniciar a conversa.')
    } finally {
      setAEnviar(false)
    }
  }

  return (
    <View style={styles.root}>
    <KeyboardAvoidingView
      style={styles.root}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
        <Text style={styles.hint}>
          Comece pelo número ou pelo nome do contato. A primeira mensagem é opcional.
        </Text>
        <Text style={styles.label}>Contato ou número</Text>
        {contato ? (
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Trocar contato"
            style={styles.contatoOn}
            onPress={() => {
              setContato(null)
              setBusca(contato.telefone || contato.nome)
            }}
          >
            <View style={{ flex: 1 }}>
              <Text style={styles.contatoNome}>{contato.nome}</Text>
              <Text style={styles.contatoMeta}>
                {contato.telefone || 'Sem número'}
                {contato.empresas?.[0]?.nome ? ` · ${contato.empresas[0].nome}` : ''}
              </Text>
            </View>
            <Text style={styles.trocar}>Trocar</Text>
          </Pressable>
        ) : (
          <TextInput
            style={styles.input}
            value={busca}
            onChangeText={setBusca}
            placeholder="Nome, empresa ou 5511999999999"
            placeholderTextColor={colors.muted}
            autoCapitalize="none"
            autoCorrect={false}
            editable={!aEnviar}
          />
        )}
        {!contato && aBuscar ? <ActivityIndicator color={colors.teal} style={{ marginTop: 8 }} /> : null}
        {!contato
          ? contatos.map((c) => (
              <Pressable
                key={c.id}
                accessibilityRole="button"
                style={styles.sugestao}
                onPress={() => {
                  setContato(c)
                  setBusca(c.telefone || '')
                  setContatos([])
                }}
              >
                <Text style={styles.contatoNome}>{c.nome}</Text>
                <Text style={styles.contatoMeta}>
                  {c.telefone || 'Sem número'}
                  {c.empresas?.[0]?.nome ? ` · ${c.empresas[0].nome}` : ''}
                </Text>
              </Pressable>
            ))
          : null}
        {aCarregarSetores || escolherSetor || erroSetores ? (
          <View style={{ marginTop: 16, gap: 8 }}>
            <Text style={styles.label}>Setor</Text>
            <Text style={styles.hint}>O setor escolhido entra na assinatura enviada ao cliente.</Text>
            {aCarregarSetores ? (
              <ActivityIndicator color={colors.teal} />
            ) : erroSetores ? (
              <Text style={styles.erro}>Não foi possível carregar os setores.</Text>
            ) : (
              setoresOpcoes.map((s) => {
                const on = setorId === s.id
                return (
                  <Pressable
                    key={s.id}
                    accessibilityRole="radio"
                    accessibilityState={{ selected: on }}
                    style={[styles.setor, on && styles.setorOn]}
                    onPress={() => setSetorId(s.id)}
                    disabled={aEnviar}
                  >
                    <Text style={[styles.setorTxt, on && styles.setorTxtOn]}>{s.nome}</Text>
                  </Pressable>
                )
              })
            )}
          </View>
        ) : null}
        <Text style={[styles.label, { marginTop: 16 }]}>Mensagem inicial (opcional)</Text>
        <TextInput
          style={[styles.input, styles.area]}
          value={mensagem}
          onChangeText={setMensagem}
          placeholder="Ex.: Olá, retorno sobre a sua demanda…"
          placeholderTextColor={colors.muted}
          multiline
          editable={!aEnviar}
        />
        {erro ? <Text style={styles.erro}>{erro}</Text> : null}
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Iniciar conversa"
          style={[styles.botao, aEnviar && styles.botaoOff]}
          onPress={() => void confirmar()}
          disabled={aEnviar}
        >
          {aEnviar ? (
            <ActivityIndicator color={colors.white} />
          ) : (
            <Text style={styles.botaoTxt}>Iniciar conversa</Text>
          )}
        </Pressable>
      </ScrollView>
    </KeyboardAvoidingView>
    <FaixaGestoVoltar fallback="/chat" />
    </View>
  )
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.deck },
  scroll: { padding: 20, paddingBottom: 40 },
  hint: { fontSize: 13, color: colors.muted, lineHeight: 18, marginBottom: 8 },
  label: { fontSize: 13, fontWeight: '600', color: colors.navyMid, marginBottom: 6 },
  input: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 16,
    color: colors.text,
    backgroundColor: colors.white,
  },
  area: { minHeight: 88, textAlignVertical: 'top' },
  contatoOn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    backgroundColor: colors.white,
    borderRadius: radius.md,
    padding: 14,
    borderWidth: 1,
    borderColor: colors.tealSoft,
  },
  contatoNome: { fontSize: 15, fontWeight: '600', color: colors.text },
  contatoMeta: { fontSize: 13, color: colors.muted, marginTop: 2 },
  trocar: { color: colors.teal, fontWeight: '700', fontSize: 13 },
  sugestao: {
    backgroundColor: colors.white,
    borderRadius: radius.md,
    paddingHorizontal: 14,
    paddingVertical: 12,
    marginTop: 8,
  },
  setor: {
    backgroundColor: colors.white,
    borderRadius: radius.md,
    paddingHorizontal: 14,
    paddingVertical: 12,
    borderWidth: 1,
    borderColor: colors.border,
  },
  setorOn: { backgroundColor: colors.navy, borderColor: colors.navy },
  setorTxt: { fontSize: 15, fontWeight: '600', color: colors.text },
  setorTxtOn: { color: colors.white },
  erro: {
    color: colors.danger,
    backgroundColor: colors.dangerBg,
    padding: 10,
    borderRadius: radius.md,
    marginTop: 12,
  },
  botao: {
    backgroundColor: colors.teal,
    borderRadius: radius.md,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 18,
  },
  botaoOff: { opacity: 0.7 },
  botaoTxt: { color: colors.white, fontWeight: '700', fontSize: 16 },
})
