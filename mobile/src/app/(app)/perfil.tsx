import { useCallback, useEffect, useMemo, useState } from 'react'
import { ActivityIndicator, Pressable, StyleSheet, Switch, Text, View } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'

import { notificacoes, type NotificacoesPreferencias } from '../../api/client'
import { useAuth } from '../../auth/AuthContext'
import { Avatar } from '../../components/Avatar'
import { Icon } from '../../components/Icon'
import { radius, type Cores } from '../../lib/brand'
import { useCores, useTema, type PreferenciaTema } from '../../lib/tema'

const OPCOES_APARENCIA: { id: PreferenciaTema; titulo: string; icone: 'sunny-outline' | 'moon-outline' | 'phone-portrait-outline' }[] = [
  { id: 'light', titulo: 'Claro', icone: 'sunny-outline' },
  { id: 'dark', titulo: 'Escuro', icone: 'moon-outline' },
  { id: 'system', titulo: 'Sistema', icone: 'phone-portrait-outline' },
]

export default function PerfilScreen() {
  const styles = usarEstilos()
  const cores = useCores()
  const { preferencia, definir } = useTema()
  const insets = useSafeAreaInsets()
  const { me, slug, sair } = useAuth()
  const [prefs, setPrefs] = useState<NotificacoesPreferencias | null>(null)
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)

  useEffect(() => {
    let vivo = true
    void notificacoes
      .preferencias()
      .then((p) => {
        if (vivo) setPrefs(p)
      })
      .catch(() => {
        if (vivo) setErro('Não foi possível carregar as preferências de notificação.')
      })
    return () => {
      vivo = false
    }
  }, [])

  const salvar = useCallback(
    async (patch: Partial<NotificacoesPreferencias>) => {
      const anterior = prefs
      setSalvando(true)
      setErro(null)
      setPrefs((atual) => ({ ...(atual ?? { push_habilitado: false, push_fila: true }), ...patch }))
      try {
        setPrefs(await notificacoes.atualizar(patch))
      } catch {
        setPrefs(anterior)
        setErro('Não foi possível salvar. Verifique a conexão e tente de novo.')
      } finally {
        setSalvando(false)
      }
    },
    [prefs],
  )

  const papel =
    me?.role === 'admin' ? 'Administrador' : me?.role === 'atendente' ? 'Atendente' : me?.role || '—'
  const pushLigado = prefs?.push_habilitado ?? false

  return (
    <View style={[styles.box, { paddingTop: Math.max(insets.top, 12) + 8 }]}>
      <View style={styles.card}>
        <Avatar nome={me?.nome || '?'} size={72} />
        <Text style={styles.titulo}>{me?.nome}</Text>
        <Text style={styles.email}>{me?.email}</Text>
        <View style={styles.pills}>
          <View style={styles.pill}>
            <Text style={styles.pillTxt}>{papel}</Text>
          </View>
          <View style={styles.pill}>
            <Text style={styles.pillTxt}>{slug}</Text>
          </View>
        </View>
      </View>

      <View style={styles.cardPreferencias}>
        <View style={styles.linha}>
          <View style={styles.textos}>
            <Text style={styles.prefTitulo}>Notificações neste celular</Text>
            <Text style={styles.prefAjuda}>
              Receba avisos de mensagens e de chats aguardando atendimento.
            </Text>
          </View>
          {prefs ? (
            <Switch
              accessibilityLabel="Notificações neste celular"
              value={pushLigado}
              disabled={salvando}
              onValueChange={(valor) => void salvar({ push_habilitado: valor })}
              trackColor={{ true: cores.teal, false: cores.border }}
              thumbColor={cores.sobre}
            />
          ) : (
            <ActivityIndicator color={cores.teal} />
          )}
        </View>
        <View style={styles.separador} />
        <View style={styles.linha}>
          <View style={styles.textos}>
            <Text style={styles.prefTitulo}>Avisar sobre a fila de espera</Text>
            <Text style={styles.prefAjuda}>Um lembrete a cada poucos minutos enquanto houver fila.</Text>
          </View>
          <Switch
            accessibilityLabel="Avisar sobre a fila de espera"
            value={prefs?.push_fila ?? true}
            disabled={!pushLigado || salvando}
            onValueChange={(valor) => void salvar({ push_fila: valor })}
            trackColor={{ true: cores.teal, false: cores.border }}
            thumbColor={cores.sobre}
          />
        </View>
        {erro ? <Text style={styles.erro}>{erro}</Text> : null}
      </View>

      <View style={styles.cardAparencia}>
        <Text style={styles.prefTitulo}>Aparência</Text>
        <Text style={styles.prefAjuda}>
          Claro, escuro ou igual ao sistema — mesmas cores do painel web.
        </Text>
        <View style={styles.aparenciaOpcoes}>
          {OPCOES_APARENCIA.map((opcao) => {
            const ativo = preferencia === opcao.id
            return (
              <Pressable
                key={opcao.id}
                accessibilityRole="button"
                accessibilityLabel={`Tema ${opcao.titulo}`}
                style={[styles.aparenciaOpcao, ativo && styles.aparenciaOpcaoAtiva]}
                onPress={() => definir(opcao.id)}
              >
                <Icon name={opcao.icone} size={18} color={ativo ? cores.sobre : cores.muted} />
                <Text style={[styles.aparenciaTxt, ativo && styles.aparenciaTxtAtiva]}>{opcao.titulo}</Text>
              </Pressable>
            )
          })}
        </View>
      </View>

      <Pressable
        accessibilityRole="button"
        accessibilityLabel="Sair e trocar instância"
        style={styles.botao}
        onPress={() => void sair()}
      >
        <Icon name="log-out-outline" size={20} color={cores.danger} />
        <Text style={styles.botaoTxt}>Sair e trocar instância</Text>
      </Pressable>
    </View>
  )
}


function usarEstilos() {
  const cores = useCores()
  return useMemo(() => criarEstilos(cores), [cores])
}

function criarEstilos(cores: Cores) {
  return StyleSheet.create({
    box: { flex: 1, backgroundColor: cores.deck, padding: 20, gap: 16 },
    card: {
      backgroundColor: cores.white,
      borderRadius: radius.lg,
      paddingVertical: 28,
      paddingHorizontal: 20,
      alignItems: 'center',
      gap: 8,
    },
    cardPreferencias: {
      backgroundColor: cores.white,
      borderRadius: radius.lg,
      paddingHorizontal: 16,
      paddingVertical: 8,
    },
    linha: {
      flexDirection: 'row',
      alignItems: 'center',
      gap: 12,
      paddingVertical: 12,
    },
    textos: { flex: 1, gap: 2 },
    prefTitulo: { fontSize: 15, fontWeight: '600', color: cores.navy },
    prefAjuda: { fontSize: 13, color: cores.muted },
    separador: { height: 1, backgroundColor: cores.border },
    erro: { color: cores.danger, fontSize: 13, paddingBottom: 10 },
    titulo: { fontSize: 22, fontWeight: '700', color: cores.navy, marginTop: 8 },
    email: { fontSize: 15, color: cores.muted },
    pills: { flexDirection: 'row', gap: 8, marginTop: 8 },
    pill: {
      backgroundColor: cores.tealSoft,
      paddingHorizontal: 12,
      paddingVertical: 6,
      borderRadius: radius.full,
    },
    pillTxt: { fontSize: 13, fontWeight: '600', color: cores.tealDark },
    botao: {
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 8,
      backgroundColor: cores.white,
      borderRadius: radius.md,
      paddingVertical: 14,
      borderWidth: 1,
      borderColor: cores.dangerBg,
    },
    botaoTxt: { color: cores.danger, fontWeight: '700', fontSize: 15 },
    cardAparencia: {
      backgroundColor: cores.white,
      borderRadius: radius.lg,
      paddingHorizontal: 16,
      paddingTop: 16,
      paddingBottom: 12,
      gap: 4,
    },
    aparenciaOpcoes: { flexDirection: 'row', gap: 8, marginTop: 10 },
    aparenciaOpcao: {
      flex: 1,
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 6,
      paddingVertical: 10,
      borderRadius: radius.md,
      borderWidth: 1,
      borderColor: cores.border,
      backgroundColor: cores.deck,
    },
    aparenciaOpcaoAtiva: { backgroundColor: cores.teal, borderColor: cores.teal },
    aparenciaTxt: { fontSize: 13, fontWeight: '600', color: cores.muted },
    aparenciaTxtAtiva: { color: cores.sobre },

  })
}
