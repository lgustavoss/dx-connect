import { Link, useNavigate } from 'react-router-dom'
import { BrandLogo } from '../../brand'
import { APP_NAME } from '../../brand/tokens'
import { landingContactEmail } from '../../content/landing'
import { VoltarButton } from '../../components/ui/VoltarButton'
import { MarketingLayout } from './MarketingLayout'

/** Política de privacidade pública — URL exigida pela Play Console (#739). */
export function PrivacidadePage() {
  const navigate = useNavigate()
  return (
    <MarketingLayout>
      <div className="mx-auto w-full min-w-0 max-w-3xl px-5 py-12 sm:px-8 lg:px-10">
        <VoltarButton onClick={() => navigate('/')} />
        <div className="mt-8">
          <BrandLogo variant="wordmark" size="md" markVariant="onDark" />
        </div>
        <h1 className="mt-6 text-3xl font-bold tracking-tight text-white sm:text-4xl">
          Política de privacidade
        </h1>
        <p className="mt-2 text-sm text-slate-500">Última actualização: agosto de 2026 · App e painel {APP_NAME}</p>

        <div className="prose prose-invert mt-10 max-w-none space-y-8 text-slate-300 prose-headings:text-white prose-a:text-sky-300">
          <section className="space-y-3">
            <h2 className="text-xl font-semibold text-white">1. Quem somos</h2>
            <p>
              O {APP_NAME} é um sistema de atendimento (helpdesk) operado por instância dedicada para cada
              empresa cliente. Esta política descreve o tratamento de dados no <strong>painel web</strong>,
              na <strong>PWA</strong> e no <strong>aplicativo Android</strong> (package{' '}
              <code className="text-sky-200">br.com.deskrudder.app</code>).
            </p>
            <p>
              Contacto: <a href={`mailto:${landingContactEmail}`}>{landingContactEmail}</a>.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-xl font-semibold text-white">2. Dados que tratamos</h2>
            <ul className="list-disc space-y-2 pl-5">
              <li>
                <strong>Conta e autenticação:</strong> e-mail, nome, credenciais (hash), tokens de sessão e,
                no app, o identificador da empresa (slug) escolhido no login.
              </li>
              <li>
                <strong>Operação de atendimento:</strong> tickets, mensagens WhatsApp/portal, anexos,
                metadados de fila e preferências de notificação — sempre na base da <em>instância</em> da
                empresa cliente.
              </li>
              <li>
                <strong>Notificações:</strong> endpoints Web Push / UnifiedPush associados ao utilizador na
                instância, para alertas de fila e mensagens.
              </li>
              <li>
                <strong>Dados técnicos:</strong> logs de aplicação, endereço IP e user-agent para segurança e
                diagnóstico.
              </li>
            </ul>
            <p>
              O aplicativo móvel <strong>não</strong> guarda uma cópia local da base de dados: os dados são
              os da API da empresa indicada na Conta.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-xl font-semibold text-white">3. Finalidades</h2>
            <p>
              Prestação do serviço de atendimento, autenticação, notificações operacionais, suporte técnico e
              melhoria de estabilidade. Não vendemos dados pessoais. Não usamos os dados do atendimento para
              publicidade de terceiros.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-xl font-semibold text-white">4. Partilha e subprocessadores</h2>
            <p>
              Os dados da operação permanecem na infraestrutura da instância do cliente (ou do operador
              SaaS, conforme o contrato). Transportes de push (ex. serviços Google Play no Android) podem
              ser usados só para entregar a notificação, sem acesso ao conteúdo do painel.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-xl font-semibold text-white">5. Conservação e direitos</h2>
            <p>
              Os prazos seguem o contrato com a empresa cliente e a legislação aplicável (incluindo LGPD).
              Pedidos de acesso, correcção ou eliminação devem ser feitos ao administrador da instância ou
              a <a href={`mailto:${landingContactEmail}`}>{landingContactEmail}</a>.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-xl font-semibold text-white">6. Segurança</h2>
            <p>
              Comunicação HTTPS, isolamento por instância (single-tenant em produção) e controlos de acesso
              por perfil (RBAC). Credenciais e keystores de publicação de loja não fazem parte do código
              público.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-xl font-semibold text-white">7. Alterações</h2>
            <p>
              Podemos actualizar esta página; a data no topo reflecte a versão vigente. Uso continuado do
              serviço após a alteração constitui ciência da nova versão, salvo obrigação legal em contrário.
            </p>
          </section>
        </div>

        <p className="mt-12 text-sm text-slate-500">
          <Link to="/" className="text-sky-300 hover:text-sky-200">
            {APP_NAME}
          </Link>
          {' · '}
          <a href={`mailto:${landingContactEmail}`} className="hover:text-slate-300">
            {landingContactEmail}
          </a>
        </p>
      </div>
    </MarketingLayout>
  )
}
