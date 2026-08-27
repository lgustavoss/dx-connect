/** Textos de ajuda do módulo ponto (#980) — pt-BR para o usuário final. */

export const PONTO_AJUDA_TITULO = 'Como funciona o ponto'

export type PontoAjudaSecao = {
  titulo: string
  paragrafos: string[]
}

export const PONTO_AJUDA_SECOES: PontoAjudaSecao[] = [
  {
    titulo: 'Modos de jornada',
    paragrafos: [
      'Nenhum: o sistema não espera dias de trabalho; o calendário fica neutro e faltas automáticas não se aplicam.',
      'Semanal: cada dia da semana tem horário de início e fim (como uma grade). Só nesses dias há jornada esperada.',
      'Ciclo: padrão X dias de trabalho × Y de folga, a partir de uma data de referência definida no cadastro.',
    ],
  },
  {
    titulo: 'Tolerância e atraso',
    paragrafos: [
      'A tolerância vale nos dois lados: você pode entrar a partir de (início − tolerância) e o atraso só conta depois de (início + tolerância).',
      'Se o admin não configurou jornada, essas regras de atraso/falta não entram em jogo.',
    ],
  },
  {
    titulo: 'Falta, parcial e folga',
    paragrafos: [
      'Falta: dia esperado sem entrada registrada.',
      'Parcial: houve entrada, mas a saída ainda não fechou a jornada do dia.',
      'Folga: dia fora da escala; se mesmo assim houver batidas, aparece como folga com ponto.',
    ],
  },
  {
    titulo: 'Fecho por esquecimento',
    paragrafos: [
      'Por padrão o fecho automático fica desligado até o admin ativar nas configurações do ponto.',
      'Quando ativo, o sistema pode fechar uma jornada aberta após N horas ou após a saída prevista + margem — o que ocorrer primeiro.',
    ],
  },
  {
    titulo: 'Hora extra e WhatsApp',
    paragrafos: [
      'Depois do fim da jornada, pegar chat WhatsApp novo pode exigir liberação de hora extra pelo admin.',
      'O admin pode liberar o resto do dia, até um horário ou por uma duração em minutos; há teto opcional por colaborador.',
    ],
  },
  {
    titulo: 'Cobertura e competência',
    paragrafos: [
      'Cobertura de plantão: você pede a um colega, ele aceita e o admin homologa (ou o admin agenda direto). No dia, quem pediu não gera falta e quem cobre passa a ter jornada esperada.',
      'Quando o admin fecha o mês (competência), ajustes posteriores ficam marcados como pós-fechamento. Você pode confirmar ciência no espelho mensal depois do fechamento.',
    ],
  },
]
