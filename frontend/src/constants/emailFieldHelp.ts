import type { EmailProviderKind } from './emailProviderPresets'

export type EmailHelpTopic =
  | 'provedor'
  | 'conta_email'
  | 'conta_senha'
  | 'smtp_remetente'
  | 'smtp_nome_remetente'
  | 'imap_pasta'

export function getEmailFieldHelp(
  topic: EmailHelpTopic,
  provedor: EmailProviderKind,
): { title: string; steps: string[] } {
  const p = provedor === 'manual' ? null : provedor

  if (topic === 'provedor') {
    return {
      title: 'Provedor de e-mail (presets)',
      steps:
        p === 'gmail'
          ? [
              'Escolha «Google Gmail» para preencher automaticamente smtp.gmail.com, imap.gmail.com, portas 587/993 e STARTTLS/SSL.',
              'Depois preencha uma vez o e-mail da conta e a senha de aplicação na secção «Conta de correio».',
              'Se a sua conta não for Gmail, escolha «Personalizado» e peça ao fornecedor os dados de servidor.',
            ]
          : p === 'microsoft365'
            ? [
                'Escolha «Microsoft 365» para preencher smtp.office365.com e outlook.office365.com com as portas habituais.',
                'Contas de trabalho ou escola usam normalmente estes servidores; o e-mail e a senha preenchem-se uma vez em «Conta de correio».',
                'Conta pessoal @outlook.com ou @hotmail.com costuma usar outros hosts: veja a nota abaixo do seletor ou «Personalizado».',
              ]
            : [
                '«Personalizado» não altera os campos: use quando o correio é de outro fornecedor ou quando o administrador lhe passou hosts próprios.',
                'Depois de escolher Gmail ou Microsoft, pode voltar a «Personalizado» para editar à mão sem perder o que já escreveu.',
              ],
    }
  }

  if (topic === 'conta_email') {
    if (p === 'gmail') {
      return {
        title: 'E-mail da conta',
        steps: [
          'Abra mail.google.com e confirme o endereço completo da caixa (ex.: nome@gmail.com ou o domínio Google Workspace).',
          'Esse mesmo e-mail é usado para autenticar no envio (SMTP) e na receção (IMAP).',
        ],
      }
    }
    if (p === 'microsoft365') {
      return {
        title: 'E-mail da conta',
        steps: [
          'Use o endereço com que entra no Outlook na Web ou no Teams (ex.: nome@empresa.com).',
          'Se o teste falhar, confirme com o TI se deve usar outro formato (por vezes difere do e-mail visível).',
        ],
      }
    }
    return {
      title: 'E-mail da conta',
      steps: [
        'É o endereço completo da caixa de correio usada para enviar e receber.',
        'Se não souber, abra o webmail ou o Outlook e veja em Definições / Conta.',
      ],
    }
  }

  if (topic === 'conta_senha') {
    if (p === 'gmail') {
      return {
        title: 'Senha da conta',
        steps: [
          'Com verificação em duas etapas ativa, o Gmail não aceita a senha normal do site.',
          'Na Conta Google: Segurança → verificação em duas etapas ativa → «Senhas de app».',
          'Crie uma senha para a app «Correio» (dispositivo «Outro», ex.: DeskRudder), copie os 16 caracteres e cole aqui.',
          'Esta senha é usada automaticamente para envio e receção. Deixe em branco ao guardar se quiser manter a senha já gravada no sistema.',
        ],
      }
    }
    if (p === 'microsoft365') {
      return {
        title: 'Senha da conta',
        steps: [
          'A senha que você usa para entrar no site do Outlook nem sempre funciona aqui (SMTP/IMAP). Muitas vezes é preciso uma «senha de aplicativo» ou uma política do TI que permita este tipo de acesso.',
          'Se você abriu «Informações de segurança» → «Adicionar um método de entrada» e só aparecem opções como Microsoft Authenticator, token de hardware ou e-mail, isso é normal: essa lista não é onde se cria senha de app. Ela serve para MFA (como entrar no browser), não para correio legado.',
          'Em contas Microsoft 365 de trabalho ou escola, a opção «Senha de aplicativo» costuma sumir quando o administrador desativou senhas de app, usa predefinições de segurança restritivas ou políticas que bloqueiam SMTP/IMAP com senha. Nesse caso não há como o utilizador final «ativar» sozinho: é preciso o TI.',
          'Se o teste SMTP passar e o IMAP falhar com «LOGIN failed», muitas vezes não é a senha no formulário: no Microsoft 365 o envio (SMTP autenticado) e a receção (IMAP) são controlados em separado — o TI pode ter deixado SMTP ativo e bloqueado IMAP ou a autenticação básica só do lado IMAP. Resumo oficial: https://learn.microsoft.com/exchange/clients-and-mobile-in-exchange-online/deprecation-of-basic-authentication-exchange-online',
          'Peça ao TI para: (1) permitir senhas de aplicativo na organização, se forem usar esse modelo, ou (2) ativar «SMTP autenticado» (Authenticated SMTP) na sua caixa de correio no Exchange Online e confirmar se IMAP está permitido para a conta, ou (3) indicar outro método oficial (por exemplo integração OAuth, se o produto suportar).',
          'Conta pessoal @outlook.com / @hotmail.com: em account.microsoft.com → Segurança, com verificação em duas etapas ligada, às vezes existe «Senhas de app» num menu separado (não confundir com a lista de «adicionar método» da conta empresarial).',
          'A mesma senha é aplicada ao envio e à receção neste formulário. Deixe em branco ao guardar para manter a senha já gravada no sistema.',
        ],
      }
    }
    return {
      title: 'Senha da conta',
      steps: [
        'É a senha ou token que o servidor aceita para enviar e receber (muitas vezes uma «senha de aplicação»).',
        'Peça ao fornecedor de e-mail ou ao TI o tipo de credencial correto.',
        'Deixe em branco ao guardar para manter a senha já gravada no sistema.',
      ],
    }
  }

  if (topic === 'smtp_remetente') {
    return {
      title: 'E-mail remetente (From)',
      steps:
        p === 'gmail'
          ? [
              'Para evitar rejeições, use normalmente o mesmo endereço que colocou em «E-mail da conta».',
              'Em Google Workspace, o administrador pode autorizar aliases; confirme antes de usar outro remetente.',
            ]
          : p === 'microsoft365'
            ? [
                'Em muitos casos use o mesmo e-mail da conta.',
                'Se a organização tiver aliases ou caixas partilhadas, confirme com o TI qual pode aparecer em «De:».',
              ]
            : [
                'Endereço que os destinatários vêem em «De:» nos e-mails enviados pelo sistema.',
                'Deve ser um endereço que o SMTP está autorizado a enviar.',
              ],
    }
  }

  if (topic === 'smtp_nome_remetente') {
    return {
      title: 'Nome remetente',
      steps: [
        'Nome amigável junto ao e-mail (ex.: «Suporte ACME»).',
        'Pode ser o nome da empresa ou do departamento.',
      ],
    }
  }

  if (topic === 'imap_pasta') {
    return {
      title: 'Pasta IMAP',
      steps:
        p === 'gmail'
          ? [
              'O Gmail usa normalmente INBOX para a caixa de entrada principal.',
              'Só altere se souber que a conta usa outra pasta para o correio a ler.',
            ]
          : p === 'microsoft365'
            ? [
                'INBOX costuma funcionar no Exchange Online.',
                'Fluxos avançados exigem caminho indicado pelo TI.',
              ]
            : [
                'Pasta onde o servidor faz «select» ao testar IMAP (por omissão INBOX).',
                'Confirme no webmail ou com o fornecedor se usa outra pasta.',
              ],
    }
  }

  return { title: 'Ajuda', steps: ['Sem conteúdo para este tópico.'] }
}
