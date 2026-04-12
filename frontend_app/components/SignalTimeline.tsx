'use client'
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  CartesianGrid,
} from 'recharts'
import { Report } from '@/types'

interface Props {
  reports: Report[]
}

const SIGNAL_Y: Record<string, number> = {
  PRODUCT_LAUNCH: 3,
  EARNINGS: 2,
  GEOPOLITICAL: 1,
}

const SIGNAL_COLOR: Record<string, string> = {
  PRODUCT_LAUNCH: '#0ea5e9',
  EARNINGS: '#10b981',
  GEOPOLITICAL: '#f59e0b',
}

export default function SignalTimeline({ reports }: Props) {
  const data = reports
    .filter(r => SIGNAL_Y[r.signal_label])
    .map(r => ({
      x: new Date(r.created_at).getTime(),
      y: SIGNAL_Y[r.signal_label],
      label: r.signal_label,
      confidence: r.confidence,
      query: r.query,
    }))

  const yLabels: Record<number, string> = {
    1: 'GEOPOLITICAL',
    2: 'EARNINGS',
    3: 'PRODUCT',
  }

  return (
    <section className="is-card rounded-2xl p-5 sm:p-6">
      <div className="mb-5 flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-xs font-bold uppercase tracking-widest text-slate-400">
            Signal timeline
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            Classified intelligence events over time
          </p>
        </div>
        {data.length > 0 && (
          <span className="text-xs font-medium text-slate-500">
            {data.length} plotted point{data.length === 1 ? '' : 's'}
          </span>
        )}
      </div>

      {data.length === 0 ? (
        <div className="flex h-[200px] flex-col items-center justify-center rounded-xl border border-dashed border-slate-200 bg-slate-50/80 text-center px-6">
          <p className="text-sm font-medium text-slate-600">No chart data yet</p>
          <p className="mt-1 max-w-sm text-xs text-slate-500">
            Reports with signal types EARNINGS, PRODUCT_LAUNCH, or GEOPOLITICAL appear here after
            queries run.
          </p>
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <ScatterChart margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
            <XAxis
              dataKey="x"
              type="number"
              domain={['auto', 'auto']}
              tickFormatter={v => new Date(v).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
              scale="time"
              stroke="#94a3b8"
              tick={{ fill: '#64748b', fontSize: 11 }}
              tickLine={false}
              axisLine={{ stroke: '#e2e8f0' }}
            />
            <YAxis
              dataKey="y"
              type="number"
              domain={[0.5, 3.5]}
              ticks={[1, 2, 3]}
              tickFormatter={v => yLabels[v] || ''}
              width={100}
              stroke="#94a3b8"
              tick={{ fill: '#64748b', fontSize: 10 }}
              tickLine={false}
              axisLine={{ stroke: '#e2e8f0' }}
            />
            <Tooltip
              cursor={{ strokeDasharray: '4 4', stroke: '#94a3b8' }}
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null
                const p = payload[0].payload as {
                  query?: string
                  confidence?: number
                  label?: string
                }
                const q = (p.query ?? '').slice(0, 80)
                const tail = (p.query?.length ?? 0) > 80 ? '…' : ''
                const c = p.confidence != null ? Math.round(p.confidence * 100) : 0
                return (
                  <div className="max-w-xs rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-xs shadow-lg">
                    <p className="font-semibold text-slate-500">{p.label?.replace(/_/g, ' ')}</p>
                    <p className="mt-1 leading-snug text-slate-700">
                      {q}
                      {tail}
                    </p>
                    <p className="mt-2 text-slate-500">Confidence · {c}%</p>
                  </div>
                )
              }}
            />
            <Scatter data={data} isAnimationActive={false}>
              {data.map((entry, i) => (
                <Cell
                  key={i}
                  fill={SIGNAL_COLOR[entry.label]}
                  fillOpacity={0.65 + entry.confidence * 0.35}
                />
              ))}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      )}

      <div className="mt-4 flex flex-wrap gap-4 border-t border-slate-100 pt-4">
        {Object.entries(SIGNAL_COLOR).map(([label, color]) => (
          <div key={label} className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full shadow-sm" style={{ backgroundColor: color }} />
            <span className="text-xs font-medium text-slate-600">{label.replace(/_/g, ' ')}</span>
          </div>
        ))}
      </div>
    </section>
  )
}
