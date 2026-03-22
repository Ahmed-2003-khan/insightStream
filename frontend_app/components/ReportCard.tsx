'use client'
import { useState } from 'react'
import { Report } from '@/types'
import SignalBadge from './SignalBadge'

interface Props { report: Report }

export default function ReportCard({ report }: Props) {
  const [expanded, setExpanded] = useState(false)
  const date = new Date(report.created_at).toLocaleString()

  return (
    <div className="bg-white rounded-xl border p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-2 mb-2">
        <p className="text-sm text-gray-700 font-medium line-clamp-2">{report.query}</p>
        <SignalBadge label={report.signal_label} confidence={report.confidence} />
      </div>
      <div className="flex items-center gap-3 text-xs text-gray-400 mb-3">
        <span>{date}</span>
        {report.sources && <span>Sources: {report.sources}</span>}
      </div>
      {expanded && (
        <div className="text-sm text-gray-600 whitespace-pre-wrap border-t pt-3 mt-2">
          {report.report_text}
        </div>
      )}
      <button
        onClick={() => setExpanded(!expanded)}
        className="text-xs text-blue-500 hover:text-blue-700 mt-1"
      >
        {expanded ? 'Show less' : 'Read full report'}
      </button>
    </div>
  )
}
