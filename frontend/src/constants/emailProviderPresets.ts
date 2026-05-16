/**
 * Presets de SMTP/IMAP para o painel (preenchimento local; a API continua genérica).
 * Gmail e Microsoft 365 costumam exigir senha de aplicação ou política de TI — ver documentação do provedor.
 */

export type EmailProviderKind = 'manual' | 'gmail' | 'microsoft365'

export const EMAIL_PROVIDER_OPTIONS: { value: EmailProviderKind; label: string }[] = [
  { value: 'manual', label: 'Personalizado (editar manualmente)' },
  { value: 'gmail', label: 'Google Gmail' },
  { value: 'microsoft365', label: 'Microsoft 365 / Outlook (trabalho ou escola)' },
]

export const EMAIL_PROVIDER_PRESETS: Record<
  Exclude<EmailProviderKind, 'manual'>,
  {
    smtp_host: string
    smtp_port: number
    smtp_use_starttls: boolean
    imap_host: string
    imap_port: number
    imap_use_ssl: boolean
    imap_folder: string
  }
> = {
  gmail: {
    smtp_host: 'smtp.gmail.com',
    smtp_port: 587,
    smtp_use_starttls: true,
    imap_host: 'imap.gmail.com',
    imap_port: 993,
    imap_use_ssl: true,
    imap_folder: 'INBOX',
  },
  microsoft365: {
    smtp_host: 'smtp.office365.com',
    smtp_port: 587,
    smtp_use_starttls: true,
    imap_host: 'outlook.office365.com',
    imap_port: 993,
    imap_use_ssl: true,
    imap_folder: 'INBOX',
  },
}

/** Contas pessoais @outlook.com / @hotmail.com costumam usar smtp-mail.outlook.com e imap-mail.outlook.com. */
export const OUTLOOK_CONSUMER_HINT =
  'Conta pessoal Outlook/Hotmail costuma usar smtp-mail.outlook.com (SMTP) e imap-mail.outlook.com (IMAP); ajuste manualmente se o preset Microsoft 365 não funcionar.'

export function detectEmailProviderKind(smtpHost: string, imapHost: string): EmailProviderKind {
  const s = smtpHost.trim().toLowerCase()
  const i = imapHost.trim().toLowerCase()
  if (s === 'smtp.gmail.com' || i === 'imap.gmail.com') {
    return 'gmail'
  }
  if (
    s === 'smtp.office365.com' ||
    i === 'outlook.office365.com' ||
    s === 'smtp-mail.outlook.com' ||
    i === 'imap-mail.outlook.com'
  ) {
    return 'microsoft365'
  }
  return 'manual'
}
