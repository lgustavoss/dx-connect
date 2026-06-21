/** Estilo do tooltip Recharts compatível com tema escuro, sem faixa clara no hover. */
export const chartTooltipProps = {
  contentStyle: {
    backgroundColor: 'rgb(15 23 42)',
    border: '1px solid rgb(51 65 85)',
    borderRadius: '8px',
    fontSize: '12px',
    boxShadow: '0 4px 12px rgb(0 0 0 / 0.35)',
  },
  labelStyle: { color: 'rgb(148 163 184)' },
  itemStyle: { color: 'rgb(226 232 240)' },
  cursor: { fill: 'transparent' },
} as const

export const barClickableProps = {
  cursor: 'pointer' as const,
}
