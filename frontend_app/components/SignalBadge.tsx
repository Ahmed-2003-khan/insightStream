interface Props {
  label: string
  confidence: number
}

const COLORS: Record<string, string> = {
  PRODUCT_LAUNCH:
    'bg-sky-500/10 text-sky-800 border border-sky-500/25 ring-1 ring-sky-500/10',
  EARNINGS:
    'bg-emerald-500/10 text-emerald-800 border border-emerald-500/25 ring-1 ring-emerald-500/10',
  GEOPOLITICAL:
    'bg-amber-500/10 text-amber-900 border border-amber-500/25 ring-1 ring-amber-500/10',
  CACHED:
    'bg-slate-500/10 text-slate-600 border border-slate-400/25 ring-1 ring-slate-400/10',
  NONE: 'bg-slate-500/10 text-slate-600 border border-slate-400/25 ring-1 ring-slate-400/10',
  UNKNOWN:
    'bg-rose-500/10 text-rose-800 border border-rose-500/25 ring-1 ring-rose-500/10',
}

export default function SignalBadge({ label, confidence }: Props) {
  const colorClass = COLORS[label] ?? COLORS.UNKNOWN
  const pct = confidence > 0 ? ` · ${Math.round(confidence * 100)}%` : ''
  return (
    <span
      className={`inline-flex items-center text-[11px] font-semibold tracking-wide uppercase px-2.5 py-1 rounded-md ${colorClass}`}
    >
      {label.replace(/_/g, ' ')}
      {pct}
    </span>
  )
}
