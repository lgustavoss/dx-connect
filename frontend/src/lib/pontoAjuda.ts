/** Textos de ajuda do módulo ponto — pt-BR para o usuário final. */

export const PONTO_AJUDA_TITULO = 'Como funciona o ponto'

export type PontoAjudaAudiencia = 'colaborador' | 'admin'

export type PontoAjudaSecao = {
  titulo: string
  paragrafos: string[]
}

const SECOES_COMUNS: PontoAjudaSecao[] = [
  {
    titulo: 'Três caminhos no dia',
    paragrafos: [
      'Trabalhou e fechou o ponto: o banco ajusta sozinho (crédito se passou da meta; débito se ficou abaixo — ex.: 6h de 8h).',
      'Não trabalhou e quer usar o banco: peça folga (banco). Após aprovação, o dia não conta como falta e a carga desconta do banco.',
      'Não trabalhou e não é folga de banco: fica como falta — sem desconto no banco (tratamento em folha fica separado).',
    ],
  },
  {
    titulo: 'Bater ponto',
    paragrafos: [
      'Um único botão: cada toque registra o próximo horário (entrada, saída do período, nova entrada após pausa).',
      'Também dá para bater pelo indicador na barra superior (Fora do ponto / Trabalhando).',
      'Saída esquecida: o período fica em aberto. Peça inclusão ou correção com o horário certo — o admin só aprova ou rejeita.',
    ],
  },
]

const SECOES_COLABORADOR: PontoAjudaSecao[] = [
  ...SECOES_COMUNS,
  {
    titulo: 'Espelho e solicitações',
    paragrafos: [
      'No Espelho do mês, os cards mostram horas, faltas (p/ desconto), crédito e débito do banco e o saldo.',
      'Clique em um dia: inclusão, correção ou folga (banco). Em falta, use Converter em folga (banco) se houve acordo.',
      'Déficit parcial (trabalhou menos que a meta e já fechou a jornada) aparece como −Xh no banco (automático).',
      'Dá para anexar PDF ou imagem (ex.: atestado) no pedido.',
    ],
  },
  {
    titulo: 'Banco de horas',
    paragrafos: [
      'O destino do excesso (banco, pagamento ou misto) é definido pelo admin nas configurações.',
      'O saldo passa de um mês para o outro no prazo de compensação. Desconto em folha do saldo negativo só com acordo/convenção coletiva.',
      'Atraso isolado não gera alerta: o ajuste entra no banco quando a jornada do dia fecha.',
    ],
  },
  {
    titulo: 'Ciência do mês',
    paragrafos: [
      'Quando o admin fecha a competência, você confirma ciência do espelho na aba Operação.',
      'Pedidos feitos depois do fechamento ficam marcados como pós-fechamento (auditoria).',
    ],
  },
]

const SECOES_ADMIN: PontoAjudaSecao[] = [
  ...SECOES_COMUNS,
  {
    titulo: 'Seu papel na equipe',
    paragrafos: [
      'O colaborador pede inclusão, correção ou folga (banco). Você só aprova ou rejeita — sem criar batida no lugar dele.',
      'Na aba Ajustes: fila do que falta decidir e histórico do mês/colaborador.',
      'No Espelho: calendário e métricas de uma pessoa; exportar PDF/Excel/folha RH só dela.',
    ],
  },
  {
    titulo: 'Fechamento',
    paragrafos: [
      'Antes de fechar, confira o resumo: faltas (p/ desconto em folha), crédito e débito do banco, saldo inicial e do mês.',
      'O PDF/Excel do espelho traz o mesmo bloco de banco e faltas para a contabilidade/RH.',
      'Ao fechar o mês, a equipe confirma ciência; novos ajustes entram como pós-fechamento. Reabrir pede motivo.',
    ],
  },
  {
    titulo: 'Configurações e feriados',
    paragrafos: [
      'Banco de horas, destino do excesso (banco / pagamento / misto), jornada diária, pausa mínima e geolocalização ficam nesta aba.',
      'Feriados da instância: marque «repetir todos os anos» para o mesmo dia/mês valer automaticamente nos anos seguintes.',
      'Feriados nacionais (BR) podem ser ligados à parte na conformidade.',
    ],
  },
  {
    titulo: 'Jornada no cadastro',
    paragrafos: [
      'Nenhum: sem dias esperados (calendário neutro).',
      'Semanal: grade por dia da semana.',
      'Ciclo: X de trabalho × Y de folga a partir de uma data de referência.',
    ],
  },
]

export function secoesAjudaPonto(audiencia: PontoAjudaAudiencia): PontoAjudaSecao[] {
  return audiencia === 'admin' ? SECOES_ADMIN : SECOES_COLABORADOR
}

/** @deprecated use secoesAjudaPonto('colaborador') */
export const PONTO_AJUDA_SECOES = SECOES_COLABORADOR
