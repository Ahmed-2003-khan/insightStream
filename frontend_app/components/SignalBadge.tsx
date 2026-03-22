interface Props {
  label: string
  confidence: number
}

const COLORS: Record<string, string> = {
  PRODUCT_LAUNCH: 'bg-blue-100 text-blue-800 border border-blue-300',
  EARNINGS:       'bg-green-100 text-green-800 border border-green-300',
  GEOPOLITICAL:   'bg-orange-100 text-orange-800 border border-orange-300',
  CACHED:         'bg-gray-100 text-gray-600 border border-gray-300',
  UNKNOWN:        'bg-red-100 text-red-600 border border-red-300',
}

export default function SignalBadge({ label, confidence }: Props) {
  const colorClass = COLORS[label] || COLORS.UNKNOWN
  const pct = confidence > 0 ? ` — ${Math.round(confidence * 100)}%` : ''
  return (
    <span className={`text-xs font-semibold px-2 py-1 rounded-full ${colorClass}`}>
      {label}{pct}
    </span>
  )
}
