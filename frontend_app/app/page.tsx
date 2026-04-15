'use client'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { fetchReports } from '@/lib/api'
import { Report } from '@/types'
import SignalTimeline from '@/components/SignalTimeline'
import ReportCard from '@/components/ReportCard'
import ChatPanel from '@/components/ChatPanel'
import { IconBuilding, IconRadar, IconRefresh } from '@/components/DashboardIcons'

const COMPANIES = ['All', 'Microsoft', 'Apple', 'Google'] as const

function countByLabel(reports: Report[]) {
  const m: Record<string, number> = {}
  for (const r of reports) {
    m[r.signal_label] = (m[r.signal_label] ?? 0) + 1
  }
  return m
}

export default function Dashboard() {
  const [reports, setReports] = useState<Report[]>([])
  const [filtered, setFiltered] = useState<Report[]>([])
  const [company, setCompany] = useState<string>('All')
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [lastUpdated, setLastUpdated] = useState<string>('')

  const loadReports = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true)
    else setLoading(true)
    try {
      const data = await fetchReports(50)
      setReports(data.reports)
      setFiltered(data.reports)
      if (data.reports.length > 0) {
        setLastUpdated(
          new Date(data.reports[0].created_at).toLocaleString(undefined, {
            dateStyle: 'medium',
            timeStyle: 'short',
          })
        )
      } else {
        setLastUpdated('')
      }
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    loadReports(false)
  }, [loadReports])

  useEffect(() => {
    if (company === 'All') {
      setFiltered(reports)
    } else {
      setFiltered(
        reports.filter(r => r.query.toLowerCase().includes(company.toLowerCase()))
      )
    }
  }, [company, reports])

  const labelCounts = useMemo(() => countByLabel(filtered), [filtered])

  return (
    <div className="is-app-bg h-dvh max-h-dvh min-h-0 overflow-hidden text-slate-900">
      <div className="flex h-full min-h-0">
        {/* Sidebar */}
        <aside
          className="flex h-full min-h-0 w-56 shrink-0 flex-col overflow-y-auto border-r border-slate-800/80 bg-[var(--sidebar)] text-slate-300 lg:w-60"
          style={{ background: 'linear-gradient(180deg, #0c1222 0%, #0a0f1a 100%)' }}
        >
          <div className="border-b border-white/5 p-5">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-500/15 text-cyan-400 ring-1 ring-cyan-400/20">
                <IconRadar className="h-5 w-5" />
              </div>
              <div>
                <h1 className="text-sm font-bold tracking-tight text-white">InsightStream</h1>
                <p className="text-[11px] text-slate-500">Intelligence console</p>
              </div>
            </div>
          </div>

          <nav className="flex flex-1 flex-col gap-0.5 p-3" aria-label="Company filter">
            <p className="mb-2 px-3 text-[10px] font-bold uppercase tracking-widest text-slate-500">
              Watchlist
            </p>
            {COMPANIES.map(c => (
              <button
                key={c}
                type="button"
                onClick={() => setCompany(c)}
                className={`flex items-center gap-2.5 rounded-xl px-3 py-2.5 text-left text-sm transition-all ${
                  company === c
                    ? 'bg-cyan-500/12 font-semibold text-cyan-300 ring-1 ring-cyan-400/25'
                    : 'text-slate-400 hover:bg-white/5 hover:text-slate-200'
                }`}
              >
                <IconBuilding className="h-4 w-4 opacity-70" />
                {c}
              </button>
            ))}
          </nav>

          <div className="border-t border-white/5 p-4">
            {lastUpdated ? (
              <>
                <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                  Latest ingest
                </p>
                <p className="mt-1 text-xs text-slate-400">{lastUpdated}</p>
              </>
            ) : (
              <p className="text-xs text-slate-500">No reports synced yet</p>
            )}
          </div>
        </aside>

        {/* Main */}
        <main className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
          <header className="shrink-0 border-b border-slate-200/80 bg-[rgba(244,246,249,0.85)] px-5 py-4 backdrop-blur-md sm:px-8">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-lg font-bold tracking-tight text-slate-900 sm:text-xl">
                  Operations overview
                </h2>
                <p className="mt-0.5 text-sm text-slate-600">
                  Live signal density, archived reports, and analyst chat in one place.
                </p>
              </div>
              <button
                type="button"
                onClick={() => loadReports(true)}
                disabled={loading || refreshing}
                className="inline-flex items-center justify-center gap-2 self-start rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-cyan-300 hover:text-cyan-800 disabled:opacity-50 sm:self-auto"
              >
                <IconRefresh className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
                {refreshing ? 'Refreshing…' : 'Refresh data'}
              </button>
            </div>

            {!loading && filtered.length > 0 && (
              <div className="mt-5 flex flex-wrap gap-2">
                <span className="inline-flex items-center rounded-full bg-white px-3 py-1 text-xs font-semibold text-slate-600 ring-1 ring-slate-200/80">
                  {filtered.length} report{filtered.length === 1 ? '' : 's'}
                  {company !== 'All' ? ` · ${company}` : ''}
                </span>
                {['EARNINGS', 'PRODUCT_LAUNCH', 'GEOPOLITICAL'].map(l => {
                  const n = labelCounts[l] ?? 0
                  if (n === 0) return null
                  return (
                    <span
                      key={l}
                      className="inline-flex items-center rounded-full bg-slate-900/5 px-3 py-1 text-xs font-medium text-slate-600"
                    >
                      {l.replace(/_/g, ' ')} · {n}
                    </span>
                  )
                })}
              </div>
            )}
          </header>

          <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-5 py-4 sm:px-8 sm:py-5">
            {loading ? (
              <div className="is-card flex h-40 shrink-0 animate-pulse items-center justify-center rounded-2xl">
                <p className="text-sm text-slate-500">Loading intelligence feed…</p>
              </div>
            ) : (
              <div className="shrink-0">
                <SignalTimeline reports={filtered} />
              </div>
            )}

            <div className="flex min-h-[500px] flex-1 flex-col gap-4 xl:grid xl:grid-cols-12 xl:grid-rows-1 xl:items-stretch">
              <section className="flex flex-col gap-3 max-xl:shrink-0 xl:col-span-5 xl:h-full">
                <div className="flex items-baseline justify-between gap-2">
                  <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400">
                    Report archive
                  </h3>
                  {!loading && filtered.length > 0 && (
                    <span className="text-xs font-medium text-slate-500">{filtered.length} items</span>
                  )}
                </div>
                <div className="min-h-0 flex-1 space-y-3 overflow-y-auto pr-1">
                  {loading && (
                    <p className="text-sm text-slate-500">Loading reports…</p>
                  )}
                  {!loading && filtered.length === 0 && (
                    <div className="is-card rounded-2xl p-8 text-center">
                      <p className="text-sm font-medium text-slate-700">No reports in this view</p>
                      <p className="mt-1 text-xs text-slate-500">
                        Run a query from chat or wait for the nightly pipeline.
                      </p>
                    </div>
                  )}
                  {filtered.map(r => (
                    <ReportCard key={r.id} report={r} />
                  ))}
                </div>
              </section>

              <section className="flex min-h-0 flex-1 flex-col xl:col-span-7 xl:h-full xl:max-h-full">
                <ChatPanel />
              </section>
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}
