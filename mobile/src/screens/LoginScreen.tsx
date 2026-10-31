import { useState } from 'react'
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native'

import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { APP_NAME, APP_TAGLINE, colors, radius } from '../lib/brand'
import { DEFAULT_SLUG } from '../lib/instance'

export function LoginScreen() {
  const { slug: slugGravado, entrar } = useAuth()
  const [slug, setSlug] = useState(slugGravado || DEFAULT_SLUG)
  const [email, setEmail] = useState('')
  const [senha, setSenha] = useState('')
  const [erro, setErro] = useState<string | null>(null)
  const [aEnviar, setAEnviar] = useState(false)

  async function onSubmit() {
    setErro(null)
    if (!slug.trim() || !email.trim() || !senha) {
      setErro('Preencha instância, e-mail e senha.')
      return
    }
    setAEnviar(true)
    try {
      await entrar(slug, email, senha)
    } catch (e) {
      const msg =
        e instanceof ApiError
          ? e.message
          : 'Não foi possível conectar à instância. No navegador a API de produção bloqueia CORS — use o Expo Go.'
      setErro(msg)
    } finally {
      setAEnviar(false)
    }
  }

  return (
    <KeyboardAvoidingView
      style={styles.root}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <View style={styles.marcaWrap}>
        <View style={styles.logo}>
          <Text style={styles.logoTxt}>D</Text>
        </View>
        <Text style={styles.marca}>{APP_NAME}</Text>
        <Text style={styles.tag}>{APP_TAGLINE}</Text>
      </View>
      <View style={styles.card}>
        <Text style={styles.label}>Instância</Text>
        <TextInput
          autoCapitalize="none"
          autoCorrect={false}
          placeholder="duplexsoft"
          placeholderTextColor={colors.muted}
          style={styles.input}
          value={slug}
          onChangeText={setSlug}
          editable={!aEnviar}
        />
        <Text style={styles.hint}>A API será api-{slug.trim() || '…'}.deskrudder.com.br</Text>
        <Text style={styles.label}>E-mail</Text>
        <TextInput
          autoCapitalize="none"
          autoCorrect={false}
          keyboardType="email-address"
          placeholder="seuemail@empresa.com"
          placeholderTextColor={colors.muted}
          style={styles.input}
          value={email}
          onChangeText={setEmail}
          editable={!aEnviar}
        />
        <Text style={styles.label}>Senha</Text>
        <TextInput
          secureTextEntry
          placeholder="••••••••"
          placeholderTextColor={colors.muted}
          style={styles.input}
          value={senha}
          onChangeText={setSenha}
          editable={!aEnviar}
          onSubmitEditing={() => void onSubmit()}
        />
        {erro ? <Text style={styles.erro}>{erro}</Text> : null}
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Entrar"
          style={[styles.botao, aEnviar && styles.botaoOff]}
          onPress={() => void onSubmit()}
          disabled={aEnviar}
        >
          {aEnviar ? (
            <ActivityIndicator color={colors.white} />
          ) : (
            <Text style={styles.botaoTxt}>Entrar</Text>
          )}
        </Pressable>
        {Platform.OS === 'web' ? (
          <Text style={styles.avisoWeb}>
            O preview no navegador usa um proxy local para a API. No celular o app fala direto com a instância.
          </Text>
        ) : null}
      </View>
    </KeyboardAvoidingView>
  )
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: colors.navy,
    justifyContent: 'center',
    padding: 24,
  },
  marcaWrap: { alignItems: 'center', marginBottom: 28, gap: 8 },
  logo: {
    width: 64,
    height: 64,
    borderRadius: 20,
    backgroundColor: colors.teal,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 4,
  },
  logoTxt: { color: colors.white, fontSize: 30, fontWeight: '800' },
  marca: { fontSize: 26, fontWeight: '700', color: colors.white, letterSpacing: -0.4 },
  tag: { color: 'rgba(255,255,255,0.7)', fontSize: 15 },
  card: {
    backgroundColor: colors.white,
    borderRadius: radius.lg,
    padding: 22,
    gap: 8,
  },
  label: {
    fontSize: 13,
    fontWeight: '600',
    color: colors.navyMid,
    marginTop: 6,
  },
  input: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 16,
    color: colors.text,
    backgroundColor: colors.deck,
  },
  hint: { fontSize: 12, color: colors.muted },
  erro: {
    color: colors.danger,
    backgroundColor: colors.dangerBg,
    padding: 10,
    borderRadius: radius.md,
    marginTop: 8,
  },
  botao: {
    backgroundColor: colors.teal,
    borderRadius: radius.md,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 14,
  },
  botaoOff: { opacity: 0.7 },
  botaoTxt: { color: colors.white, fontWeight: '700', fontSize: 16 },
  avisoWeb: { fontSize: 12, color: colors.muted, marginTop: 8, lineHeight: 18 },
})
