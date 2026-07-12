export const EMOJIS_REACAO_CHAT_INTERNO = ['👍', '❤️', '😂', '😮', '😢', '🙏'] as const

export type EmojiReacaoChatInterno = (typeof EMOJIS_REACAO_CHAT_INTERNO)[number]
