'use client'
import { ScatterChart, Scatter, XAxis, YAxis, Tooltip,
         ResponsiveContainer, Cell } from 'recharts'
import { Report } from '@/types'

interface Props { reports: Report[] }

const SIGNAL_Y: Record<string, number> = {
  PRODUCT_LAUNCH: 3,
  EARNINGS:       2,
  GEOPOLITICAL:   1,
}

const SIGNAL_COLOR: Record<string, string> = {
  PRODUCT_LAUNCH: '#3b82f6',
  EARNINGS:       '#22c55e',
  GEOPOLITICAL:   '#f97316',
}

export default function SignalTimeline({ reports }: Props) {
  const data = reports
    .filter(r => SIGNAL_Y[r.signal_label])
    .map(r => ({
      x: new Date(r.created_at).getTime(),
      y: SIGNAL_Y[r.signal_label],
      label: r.signal_label,
      confidence: r.confidence,
      query: r.query
    }))

  const yLabels: Record<number, string> = { 1: 'GEOPOLITICAL', 2: 'EARNINGS', 3: 'PRODUCT_LAUNCH' }

  return (
    <div className="bg-white rounded-xl border p-4">
      <h2 className="text-sm font-semibold text-gray-500 mb-4">Signal Timeline</h2>
      <ResponsiveContainer width="100%" height={200}>
        <ScatterChart>
          <XAxis
            dataKey="x"
            type="number"
            domain={['auto', 'auto']}
            tickFormatter={v => new Date(v).toLocaleDateString()}
            scale="time"
          />
          <YAxis
            dataKey="y"
            type="number"
            domain={[0, 4]}
            tickFormatter={v => yLabels[v] || ''}
            width={120}
          />
          <Tooltip
            formatter={(_, __, props) => [
              `${props.payload.query?.slice(0, 50)}...`,
              `Confidence: ${Math.round(props.payload.confidence * 100)}%`
            ]}
          />
          <Scatter data={data} isAnimationActive={false}>
            {data.map((entry, i) => (
               <Cell key={i} fill={SIGNAL_COLOR[entry.label]} opacity={0.7 + entry.confidence * 0.3} />
            ))}
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>
      <div className="flex gap-4 mt-2">
        {Object.entries(SIGNAL_COLOR).map(([label, color]) => (
          <div key={label} className="flex items-center gap-1">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
            <span className="text-xs text-gray-500">{label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
