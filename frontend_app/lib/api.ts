import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL
const API_KEY = process.env.NEXT_PUBLIC_API_KEY

const client = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': API_KEY
  }
})

export async function queryIntelligence(query: string) {
  const res = await client.post('/api/v1/intelligence/query', { query })
  return res.data
}

export async function fetchReports(limit = 20) {
  const res = await client.get(`/api/v1/intelligence/reports?limit=${limit}`)
  return res.data
}

export async function ingestNews(topic: string) {
  const res = await client.post('/api/v1/intelligence/ingest/news', { topic })
  return res.data
}
