'use client'
import { useState } from 'react'
import { Report } from '@/types'
import SignalBadge from './SignalBadge'

interface Props {
  report: Report
}

export default function ReportCard({ report }: Props) {
  const [expanded, setExpanded] = useState(false)
  const date = new Date(report.created_at).toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  })

  return (
    <article className="group is-card rounded-2xl p-4 transition-all duration-200 hover:shadow-lg hover:border-cyan-500/15 hover:-translate-y-0.5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <p className="text-[15px] leading-snug text-slate-800 font-medium line-clamp-2 pr-2">
          {report.query}
        </p>
        <SignalBadge label={report.signal_label} confidence={report.confidence} />
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500">
        <time dateTime={report.created_at}>{date}</time>
        {report.sources && (
          <span className="truncate max-w-full" title={report.sources}>
            <span className="text-slate-400">Sources · </span>
            {report.sources}
          </span>
        )}
      </div>
      {expanded && (
        <div className="mt-4 text-[13px] leading-relaxed text-slate-600 whitespace-pre-wrap border-t border-slate-100 pt-4 font-mono">
          {report.report_text}
        </div>
      )}
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="mt-3 text-xs font-semibold text-cyan-700 hover:text-cyan-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400/50 rounded-md px-1 -mx-1"
      >
        {expanded ? 'Show less' : 'Read full report'}
        <span className="ml-1 inline-block transition-transform group-hover:translate-x-0.5">
          {expanded ? '↑' : '→'}
        </span>
      </button>
    </article>
  )
}
