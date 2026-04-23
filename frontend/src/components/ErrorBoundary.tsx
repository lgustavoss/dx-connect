import { Component, type ErrorInfo, type ReactNode } from 'react'

type Props = { children: ReactNode }

type State = { error: Error | null }

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    if (import.meta.env.DEV) {
      console.error('[ErrorBoundary]', error, info.componentStack)
    }
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-slate-50 p-6 text-center">
          <h1 className="text-xl font-semibold text-slate-800">Algo deu errado</h1>
          <p className="max-w-lg text-sm text-slate-600">
            A interface encontrou um erro. Recarregue a página e tente novamente.
          </p>
          <pre className="max-h-40 max-w-2xl overflow-auto rounded-lg bg-red-50 p-3 text-left text-xs text-red-800">
            {this.state.error.message}
          </pre>
          <button
            type="button"
            className="rounded-lg bg-slate-800 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
            onClick={() => window.location.reload()}
          >
            Recarregar página
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
