'use client'
import { useEffect, useState } from 'react'
import { fetchReports } from '@/lib/api'
import { Report } from '@/types'
import SignalTimeline from '@/components/SignalTimeline'
import ReportCard from '@/components/ReportCard'
import ChatPanel from '@/components/ChatPanel'

const COMPANIES = ['All', 'Microsoft', 'Apple', 'Google']

export default function Dashboard() {
  const [reports, setReports]   = useState<Report[]>([])
  const [filtered, setFiltered] = useState<Report[]>([])
  const [company, setCompany]   = useState('All')
  const [loading, setLoading]   = useState(true)
  const [lastUpdated, setLastUpdated] = useState<string>('')

  useEffect(() => {
    fetchReports(50)
      .then(data => {
        setReports(data.reports)
        setFiltered(data.reports)
        if (data.reports.length > 0) {
          setLastUpdated(new Date(data.reports[0].created_at).toLocaleString())
        }
      })
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (company === 'All') {
      setFiltered(reports)
    } else {
      setFiltered(reports.filter(r =>
        r.query.toLowerCase().includes(company.toLowerCase())
      ))
    }
  }, [company, reports])

  return (
    <div className="min-h-screen bg-gray-50 flex">

      {/* Sidebar */}
      <aside className="w-48 bg-white border-r flex flex-col p-4 gap-1">
        <div className="mb-4">
          <h1 className="text-base font-bold text-gray-800">InsightStream</h1>
          <p className="text-xs text-gray-400">Competitive Intelligence</p>
        </div>
        {COMPANIES.map(c => (
          <button
            key={c}
            onClick={() => setCompany(c)}
            className={`text-left text-sm px-3 py-2 rounded-lg transition-colors ${
              company === c
                ? 'bg-blue-50 text-blue-700 font-medium'
                : 'text-gray-600 hover:bg-gray-50'
            }`}
          >
            {c}
          </button>
        ))}
        {lastUpdated && (
          <div className="mt-auto pt-4 border-t">
            <p className="text-xs text-gray-400">Last updated</p>
            <p className="text-xs text-gray-500">{lastUpdated}</p>
          </div>
        )}
      </aside>

      {/* Main */}
      <main className="flex-1 flex flex-col gap-4 p-6 overflow-hidden">

        {/* Timeline */}
        {loading ? (
          <div className="bg-white rounded-xl border p-4 text-sm text-gray-400">
            Loading timeline...
          </div>
        ) : (
          <SignalTimeline reports={filtered} />
        )}

        {/* Bottom split */}
        <div className="flex-1 grid grid-cols-2 gap-4 min-h-0">

          {/* Report Feed */}
          <div className="flex flex-col gap-3 overflow-y-auto">
            <h2 className="text-sm font-semibold text-gray-500">
              Report Feed {filtered.length > 0 && `(${filtered.length})`}
            </h2>
            {loading && <p className="text-sm text-gray-400">Loading reports...</p>}
            {!loading && filtered.length === 0 && (
              <p className="text-sm text-gray-400">
                No reports yet. Run a query to generate one.
              </p>
            )}
            {filtered.map(r => <ReportCard key={r.id} report={r} />)}
          </div>

          {/* Chat */}
          <ChatPanel />
        </div>
      </main>
    </div>
  )
}
