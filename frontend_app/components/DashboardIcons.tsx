export function IconRadar({ className = 'h-5 w-5' }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden>
      <circle cx="12" cy="12" r="10" strokeOpacity="0.35" />
      <circle cx="12" cy="12" r="6" strokeOpacity="0.5" />
      <circle cx="12" cy="12" r="2" />
      <path d="M12 2v4M12 18v4M2 12h4M18 12h4" strokeLinecap="round" strokeOpacity="0.6" />
    </svg>
  )
}

export function IconBuilding({ className = 'h-4 w-4' }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden>
      <path d="M4 20V8l8-4v16M4 12h8M9 12v8M13 12h3v8M16 12V6l4-2v16" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

export function IconRefresh({ className = 'h-4 w-4' }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden>
      <path d="M21 12a9 9 0 1 1-2.64-6.36" strokeLinecap="round" />
      <path d="M21 3v6h-6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

export function IconSparkles({ className = 'h-4 w-4' }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M9.4 5.6 11 2l1.6 3.6L16 7l-3.4 1.4L11 12 9.4 8.4 6 7l3.4-1.4zm-6 9L5 12l1.4 2.6L9 16l-2.6 1.4L5 20l-1.4-2.6L1 16l2.6-1.4zm12.6 4L16 16l1.4 2.6L20 20l-2.6 1.4L16 24l-1.4-2.6L12 20l2.6-1.4z" />
    </svg>
  )
}

export function IconUser({ className = 'h-4 w-4' }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden>
      <circle cx="12" cy="8" r="3.5" />
      <path d="M5 20c1.5-4 4.5-6 7-6s5.5 2 7 6" strokeLinecap="round" />
    </svg>
  )
}

export function IconBot({ className = 'h-4 w-4' }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden>
      <rect x="5" y="8" width="14" height="12" rx="2" />
      <path d="M9 8V6a3 3 0 0 1 6 0v2" strokeLinecap="round" />
      <circle cx="9.5" cy="13" r="1" fill="currentColor" />
      <circle cx="14.5" cy="13" r="1" fill="currentColor" />
      <path d="M12 16v1" strokeLinecap="round" />
    </svg>
  )
}
