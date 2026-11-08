const { withAppBuildGradle } = require('expo/config-plugins')

const MARCA = '// deskrudder-release-signing'

/**
 * Assina o APK/AAB de release com o keystore guardado nos secrets do GitHub.
 *
 * O Expo (CNG) regenera a pasta `android/` a cada `expo prebuild` e o template
 * assina o release com a keystore de debug. Este plugin troca essa config por
 * uma que lê as variáveis de ambiente exportadas pelo workflow
 * `.github/workflows/mobile-android-apk.yml`:
 *
 * - `ANDROID_KEYSTORE_PATH`   caminho do `.keystore` decodificado no runner
 * - `ANDROID_KEYSTORE_PASSWORD`
 * - `ANDROID_KEY_ALIAS`
 * - `ANDROID_KEY_PASSWORD`
 *
 * Sem essas variáveis (build local), o bloco fica sem `storeFile` e só o
 * `assembleRelease` falharia — o build de debug continua normal.
 */
module.exports = function withReleaseSigning(config) {
  return withAppBuildGradle(config, (cfg) => {
    if (cfg.modResults.language !== 'groovy') {
      return cfg
    }

    let conteudo = cfg.modResults.contents
    if (conteudo.includes(MARCA)) {
      return cfg
    }

    const blocoAssinatura = `
        release {
            ${MARCA}
            def caminhoKeystore = System.getenv("ANDROID_KEYSTORE_PATH")
            if (caminhoKeystore) {
                storeFile file(caminhoKeystore)
                storePassword System.getenv("ANDROID_KEYSTORE_PASSWORD")
                keyAlias System.getenv("ANDROID_KEY_ALIAS")
                keyPassword System.getenv("ANDROID_KEY_PASSWORD")
            }
        }`

    conteudo = conteudo.replace(/(\n\s*signingConfigs\s*\{\s*\n)/, `$1${blocoAssinatura}\n`)
    // Troca só o release do buildTypes (o debug vem antes e continua na keystore de debug).
    conteudo = conteudo.replace(
      /(\/\/ Caution! In production[\s\S]*?signingConfig signingConfigs\.)debug/,
      '$1release',
    )
    if (!conteudo.includes('signingConfig signingConfigs.release')) {
      throw new Error(
        'withReleaseSigning: não encontrei o buildType release no app/build.gradle do template Expo',
      )
    }

    cfg.modResults.contents = conteudo
    return cfg
  })
}
