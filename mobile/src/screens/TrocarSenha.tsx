import { useRouter } from 'expo-router'
import { useMemo, useState } from 'react'
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native'

import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { TelaTeclado } from '../components/TelaTeclado'
import { radius, type Cores } from '../lib/brand'
import { useCores } from '../lib/tema'

export function TrocarSenhaScreen() {
  const styles = usarEstilos()
  const cores = useCores()
  const router = useRouter()
  const { me, trocarSenha, sair } = useAuth()
  const [senhaAtual, setSenhaAtual] = useState('')
  const [senhaNova, setSenhaNova] = useState('')
  const [confirma, setConfirma] = useState('')
  const [erro, setErro] = useState<string | null>(null)
  const [aSalvar, setASalvar] = useState(false)
  const [aSair, setASair] = useState(false)

  async function onSubmit() {
    setErro(null)
    if (!senhaAtual || !senhaNova || !confirma) {
      setErro('Preencha a senha atual e a nova senha duas vezes.')
      return
    }
    if (senhaNova.length < 8) {
      setErro('A nova senha precisa ter pelo menos 8 caracteres.')
      return
    }
    if (senhaNova !== confirma) {
      setErro('As senhas novas não conferem.')
      return
    }
    if (senhaNova === senhaAtual) {
      setErro('A nova senha precisa ser diferente da senha atual.')
      return
    }
    setASalvar(true)
    try {
      await trocarSenha(senhaAtual, senhaNova)
      router.replace('/chat')
    } catch (e) {
      setErro(
        e instanceof ApiError ? e.message : 'Não foi possível salvar a nova senha. Tente de novo.',
      )
    } finally {
      setASalvar(false)
    }
  }

  async function onSair() {
    setASair(true)
    try {
      await sair()
      router.replace('/')
    } finally {
      setASair(false)
    }
  }

  return (
    <TelaTeclado style={styles.root}>
      <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
        <View style={styles.card}>
          <Text style={styles.titulo}>Defina uma nova senha</Text>
          <Text style={styles.subtitulo}>
            {me?.nome ? `${me.nome}, sua` : 'Sua'} conta ainda usa a senha definida pelo
            administrador. Troque a senha para continuar no app.
          </Text>

          <Text style={styles.label}>Senha atual</Text>
          <TextInput
            secureTextEntry
            autoCapitalize="none"
            autoCorrect={false}
            placeholder="••••••••"
            placeholderTextColor={cores.muted}
            style={styles.input}
            value={senhaAtual}
            onChangeText={setSenhaAtual}
            editable={!aSalvar}
          />

          <Text style={styles.label}>Nova senha</Text>
          <TextInput
            secureTextEntry
            autoCapitalize="none"
            autoCorrect={false}
            placeholder="••••••••"
            placeholderTextColor={cores.muted}
            style={styles.input}
            value={senhaNova}
            onChangeText={setSenhaNova}
            editable={!aSalvar}
          />
          <Text style={styles.hint}>Mínimo de 8 caracteres.</Text>

          <Text style={styles.label}>Confirmar nova senha</Text>
          <TextInput
            secureTextEntry
            autoCapitalize="none"
            autoCorrect={false}
            placeholder="••••••••"
            placeholderTextColor={cores.muted}
            style={styles.input}
            value={confirma}
            onChangeText={setConfirma}
            editable={!aSalvar}
            onSubmitEditing={() => void onSubmit()}
          />

          {erro ? <Text style={styles.erro}>{erro}</Text> : null}

          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Salvar nova senha"
            style={[styles.botao, aSalvar && styles.botaoOff]}
            onPress={() => void onSubmit()}
            disabled={aSalvar}
          >
            {aSalvar ? (
              <ActivityIndicator color={cores.sobre} />
            ) : (
              <Text style={styles.botaoTxt}>Salvar e continuar</Text>
            )}
          </Pressable>

          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Sair e trocar a instância"
            style={styles.botaoSair}
            onPress={() => void onSair()}
            disabled={aSalvar || aSair}
          >
            <Text style={styles.botaoSairTxt}>Sair e trocar a instância</Text>
          </Pressable>
        </View>
      </ScrollView>
    </TelaTeclado>
  )
}


function usarEstilos() {
  const cores = useCores()
  return useMemo(() => criarEstilos(cores), [cores])
}

function criarEstilos(cores: Cores) {
  return StyleSheet.create({
    root: { flex: 1, backgroundColor: cores.deck },
    scroll: { padding: 20, paddingBottom: 40 },
    card: {
      backgroundColor: cores.white,
      borderRadius: radius.lg,
      padding: 22,
      gap: 6,
    },
    titulo: { fontSize: 22, fontWeight: '700', color: cores.navy },
    subtitulo: { fontSize: 15, lineHeight: 21, color: cores.muted, marginBottom: 12 },
    label: { fontSize: 13, fontWeight: '600', color: cores.navyMid, marginTop: 6 },
    input: {
      borderWidth: 1,
      borderColor: cores.border,
      borderRadius: radius.md,
      paddingHorizontal: 14,
      paddingVertical: 12,
      fontSize: 16,
      color: cores.text,
      backgroundColor: cores.deck,
    },
    hint: { fontSize: 12, color: cores.muted },
    erro: {
      color: cores.danger,
      backgroundColor: cores.dangerBg,
      padding: 10,
      borderRadius: radius.md,
      marginTop: 10,
    },
    botao: {
      backgroundColor: cores.teal,
      borderRadius: radius.md,
      paddingVertical: 14,
      alignItems: 'center',
      marginTop: 16,
    },
    botaoOff: { opacity: 0.7 },
    botaoTxt: { color: cores.sobre, fontWeight: '700', fontSize: 16 },
    botaoSair: { alignItems: 'center', paddingVertical: 12, marginTop: 4 },
    botaoSairTxt: { color: cores.danger, fontSize: 14, fontWeight: '600' },

  })
}
