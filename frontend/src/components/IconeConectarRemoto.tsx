export function IconeConectarRemoto({ className = 'size-5' }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <rect x="3" y="4" width="18" height="12" rx="1.5" strokeWidth={2} />
      <path strokeLinecap="round" strokeWidth={2} d="M8 20h8M12 16v4" />
    </svg>
  )
}
