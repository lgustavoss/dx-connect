import { useState } from 'react'
import {
  ActivityIndicator,
  Image,
  ImageBackground,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native'

import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { Icon } from '../components/Icon'
import { TelaTeclado } from '../components/TelaTeclado'
import { DEFAULT_SLUG, normalizeSlug } from '../lib/instance'

/** Login sempre escuro, como o do painel web (independe do tema do aparelho). */
const fundo = '#050810'
const cinza = '#64748B'
const ciano = '#22D3EE'
const botaoTxtCor = '#04121E'

export function LoginScreen() {
  const { slug: slugGravado, entrar } = useAuth()
  const [slug, setSlug] = useState(slugGravado || DEFAULT_SLUG)
  const [email, setEmail] = useState('')
  const [senha, setSenha] = useState('')
  const [senhaVisivel, setSenhaVisivel] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  const [aEnviar, setAEnviar] = useState(false)

  async function onSubmit() {
    setErro(null)
    if (!normalizeSlug(slug)) {
      setErro('Informe a conta da empresa (ex.: suaempresa), só letras minúsculas, números e hífen.')
      return
    }
    if (!email.trim() || !senha) {
      setErro('Informe e-mail e senha.')
      return
    }
    if (!email.includes('@')) {
      setErro('Informe um e-mail válido.')
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
    <ImageBackground
      source={require('../../assets/login-bg.png')}
      resizeMode="cover"
      style={styles.fundo}
    >
      <View style={styles.scurecer} />
      <TelaTeclado style={styles.root} corRodape={fundo}>
        <ScrollView
          contentContainerStyle={styles.scroll}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          <View style={styles.marcaWrap}>
            <Image
              source={require('../../assets/brand-mark.png')}
              style={styles.mark}
              resizeMode="contain"
            />
            <Text style={styles.marca}>
              <Text style={styles.marcaDesk}>Desk</Text>
              <Text style={styles.marcaRudder}>Rudder</Text>
            </Text>
            <Text style={styles.tagline}>Organize. Foque. Direcione</Text>
          </View>

          <View style={styles.card}>
            <View style={styles.campoWrap}>
              <Text style={styles.label}>Conta da empresa</Text>
              <TextInput
                autoCapitalize="none"
                autoCorrect={false}
                placeholder="ex.: suaempresa"
                placeholderTextColor={cinza}
                style={styles.input}
                value={slug}
                onChangeText={(v) => setSlug(v.toLowerCase())}
                editable={!aEnviar}
              />
              <Text style={styles.hint}>Sem espaços. Em geral é o nome curto da empresa.</Text>
            </View>

            <View style={styles.campoWrap}>
              <Text style={styles.label}>E-mail</Text>
              <TextInput
                autoCapitalize="none"
                autoCorrect={false}
                keyboardType="email-address"
                placeholder="nome@empresa.com"
                placeholderTextColor={cinza}
                style={styles.input}
                value={email}
                onChangeText={setEmail}
                editable={!aEnviar}
              />
            </View>

            <View style={styles.campoWrap}>
              <Text style={styles.label}>Senha</Text>
              <View style={styles.senhaWrap}>
                <TextInput
                  secureTextEntry={!senhaVisivel}
                  placeholder="••••••••"
                  placeholderTextColor={cinza}
                  style={[styles.input, styles.inputSenha]}
                  value={senha}
                  onChangeText={setSenha}
                  editable={!aEnviar}
                  onSubmitEditing={() => void onSubmit()}
                />
                <Pressable
                  accessibilityRole="button"
                  accessibilityLabel={senhaVisivel ? 'Ocultar senha' : 'Mostrar senha'}
                  style={styles.olho}
                  onPress={() => setSenhaVisivel((v) => !v)}
                  hitSlop={8}
                >
                  <Icon
                    name={senhaVisivel ? 'eye-off-outline' : 'eye-outline'}
                    size={20}
                    color={ciano}
                  />
                </Pressable>
              </View>
            </View>

            {erro ? <Text style={styles.erro}>{erro}</Text> : null}

            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Entrar"
              style={[styles.botao, aEnviar && styles.botaoOff]}
              onPress={() => void onSubmit()}
              disabled={aEnviar}
            >
              {aEnviar ? (
                <ActivityIndicator color={botaoTxtCor} />
              ) : (
                <Text style={styles.botaoTxt}>Entrar</Text>
              )}
            </Pressable>
          </View>

          <Text style={styles.rodape}>Após validar, você entra direto no painel da sua empresa.</Text>

          {Platform.OS === 'web' ? (
            <Text style={styles.avisoWeb}>
              O preview no navegador usa um proxy local para a API. No celular o app fala direto com a
              instância.
            </Text>
          ) : null}
        </ScrollView>
      </TelaTeclado>
    </ImageBackground>
  )
}

const styles = StyleSheet.create({
  fundo: { flex: 1, backgroundColor: fundo },
  scurecer: { position: 'absolute', top: 0, right: 0, bottom: 0, left: 0, backgroundColor: 'rgba(5,8,16,0.22)' },
  root: { flex: 1 },
  scroll: {
    flexGrow: 1,
    justifyContent: 'center',
    paddingHorizontal: 24,
    paddingVertical: 40,
  },
  marcaWrap: { alignItems: 'center', marginBottom: 28 },
  mark: { width: 84, height: 76, marginBottom: 10 },
  marca: { fontSize: 32, fontWeight: '700', letterSpacing: -0.6 },
  marcaDesk: { color: '#E2E8F0' },
  marcaRudder: { color: '#38BDF8' },
  tagline: { marginTop: 6, fontSize: 13, color: '#94A3B8', letterSpacing: 0.2 },
  card: {
    width: '100%',
    maxWidth: 420,
    alignSelf: 'center',
    backgroundColor: 'rgba(255,255,255,0.045)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.09)',
    borderRadius: 18,
    padding: 20,
    gap: 14,
    shadowColor: '#000000',
    shadowOpacity: 0.4,
    shadowRadius: 30,
    shadowOffset: { width: 0, height: 18 },
    elevation: 12,
  },
  campoWrap: { gap: 6 },
  label: { fontSize: 13, fontWeight: '600', color: '#CBD5E1' },
  input: {
    backgroundColor: 'rgba(255,255,255,0.06)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.12)',
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 16,
    color: '#F1F5F9',
  },
  hint: { fontSize: 12, lineHeight: 16, color: '#64748B' },
  senhaWrap: { justifyContent: 'center' },
  inputSenha: { paddingRight: 48 },
  olho: {
    position: 'absolute',
    right: 6,
    width: 40,
    height: 40,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 10,
  },
  erro: {
    color: '#FCA5A5',
    backgroundColor: 'rgba(248,113,113,0.10)',
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 13,
    lineHeight: 18,
  },
  botao: {
    marginTop: 2,
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#06B6D4',
    shadowColor: '#06B6D4',
    shadowOpacity: 0.35,
    shadowRadius: 16,
    shadowOffset: { width: 0, height: 6 },
    elevation: 6,
  },
  botaoOff: { opacity: 0.6 },
  botaoTxt: { color: botaoTxtCor, fontSize: 16, fontWeight: '700' },
  rodape: {
    marginTop: 22,
    textAlign: 'center',
    fontSize: 12,
    lineHeight: 18,
    color: '#64748B',
  },
  avisoWeb: {
    marginTop: 10,
    textAlign: 'center',
    fontSize: 12,
    lineHeight: 18,
    color: '#64748B',
  },
})
