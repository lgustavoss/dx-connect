import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    rules: {
      // Este projeto usa padrões comuns de React (fetch em effects, setLoading, etc.).
      // A regra abaixo está muito agressiva e torna o lint impraticável.
      'react-hooks/set-state-in-effect': 'off',

      // Usamos namespaces como agrupadores de tipos no client gerado/centralizado.
      '@typescript-eslint/no-namespace': 'off',

      // Os arquivos de contexto exportam Provider + hooks utilitários (padrão comum).
      // Desabilitar evita falsos positivos no fluxo de desenvolvimento.
      'react-refresh/only-export-components': 'off',
    },
  },
])
