export interface Report {
  id: number
  query: string
  signal_label:
    | 'EARNINGS'
    | 'PRODUCT_LAUNCH'
    | 'GEOPOLITICAL'
    | 'CACHED'
    | 'NONE'
    | 'UNKNOWN'
  confidence: number
  report_text: string
  sources: string
  created_at: string
}

export interface QueryResponse {
  report: string
  cache_hit: boolean
  signal_label: string
  signal_confidence: number
}

export interface ReportsResponse {
  total: number
  reports: Report[]
}
