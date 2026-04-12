'use client'
import { useEffect, useRef, useState } from 'react'
import { queryIntelligence } from '@/lib/api'
import SignalBadge from './SignalBadge'
import { IconBot, IconSparkles, IconUser } from './DashboardIcons'

interface Message {
  role: 'user' | 'assistant'
  content: string
  signal_label?: string
  signal_confidence?: number
  cache_hit?: boolean
}

interface ConversationMessage {
  role: string
  content: string
}

const SUGGESTIONS = [
  'What are Microsoft’s latest AI products?',
  'Summarize Apple supply chain risks this quarter.',
  'Google regulatory headlines — last 30 days.',
]

export default function ChatPanel() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, loading])

  async function handleSubmit(text?: string) {
    const raw = text ?? input
    if (!raw.trim() || loading) return
    const userMsg = raw.trim()
    setInput('')

    const updatedMessages = [...messages, { role: 'user' as const, content: userMsg }]
    setMessages(updatedMessages)
    setLoading(true)

    const history: ConversationMessage[] = updatedMessages
      .slice(-6)
      .map(m => ({
        role: m.role,
        content: m.content.slice(0, 300),
      }))

    try {
      const data = await queryIntelligence(userMsg, history)
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: data.report,
          signal_label: data.signal_label,
          signal_confidence: data.signal_confidence,
          cache_hit: data.cache_hit,
        },
      ])
    } catch {
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: 'Could not reach the intelligence API. Is the backend running on the URL in `.env`?',
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex h-full min-h-0 max-h-full flex-col overflow-hidden is-card rounded-2xl">
      <header className="flex shrink-0 items-center justify-between border-b border-slate-100 px-4 py-3 sm:px-5">
        <div className="flex items-center gap-2">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-500 to-indigo-600 text-white shadow-md shadow-cyan-500/20">
            <IconSparkles className="h-4 w-4" />
          </span>
          <div>
            <h2 className="text-sm font-semibold text-slate-800">Intelligence chat</h2>
            <p className="text-[11px] text-slate-500">Grounded on your RAG pipeline · context-aware</p>
          </div>
        </div>
        {messages.length > 0 && (
          <button
            type="button"
            onClick={() => setMessages([])}
            className="rounded-lg px-2.5 py-1.5 text-xs font-semibold text-slate-500 transition-colors hover:bg-rose-50 hover:text-rose-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-300/50"
          >
            Clear
          </button>
        )}
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 py-4 sm:px-5">
        {messages.length === 0 && !loading && (
          <div className="mx-auto max-w-md pt-4 text-center">
            <p className="text-sm font-medium text-slate-700">Ask anything about tracked companies</p>
            <p className="mt-1 text-xs text-slate-500">
              Follow-up questions use recent messages so answers stay in context.
            </p>
            <div className="mt-6 flex flex-col gap-2 text-left">
              {SUGGESTIONS.map(s => (
                <button
                  key={s}
                  type="button"
                  onClick={() => handleSubmit(s)}
                  className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-left text-xs text-slate-600 transition-all hover:border-cyan-300/60 hover:bg-cyan-50/40 hover:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400/40"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="space-y-5">
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}
            >
              <div
                className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${
                  msg.role === 'user'
                    ? 'bg-slate-800 text-white'
                    : 'bg-gradient-to-br from-cyan-500/15 to-indigo-500/20 text-cyan-800'
                }`}
              >
                {msg.role === 'user' ? <IconUser className="h-4 w-4" /> : <IconBot className="h-4 w-4" />}
              </div>
              <div
                className={`max-w-[min(100%,42rem)] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm ${
                  msg.role === 'user'
                    ? 'bg-slate-800 text-white rounded-tr-md'
                    : 'is-card-muted rounded-tl-md text-slate-700'
                }`}
              >
                <p className="whitespace-pre-wrap">{msg.content}</p>
                {msg.role === 'assistant' && msg.signal_label && (
                  <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-slate-200/80 pt-3">
                    <SignalBadge label={msg.signal_label} confidence={msg.signal_confidence || 0} />
                    {msg.cache_hit && (
                      <span className="text-[10px] font-semibold uppercase tracking-wider text-amber-600/90">
                        ⚡ Cached
                      </span>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex gap-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-cyan-500/15 to-indigo-500/20 text-cyan-800">
                <IconBot className="h-4 w-4 animate-pulse" />
              </div>
              <div className="is-card-muted rounded-2xl rounded-tl-md px-4 py-3 text-sm text-slate-500">
                <span className="inline-flex items-center gap-2">
                  <span className="flex gap-1">
                    <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-cyan-500 [animation-delay:-0.3s]" />
                    <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-cyan-500 [animation-delay:-0.15s]" />
                    <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-cyan-500" />
                  </span>
                  Retrieving context & drafting report…
                </span>
              </div>
            </div>
          )}
        </div>
        <div ref={scrollRef} className="h-px w-full shrink-0" aria-hidden />
      </div>

      <footer className="shrink-0 border-t border-slate-100 bg-white p-3 sm:p-4">
        <div className="flex gap-2">
          <input
            className="min-w-0 flex-1 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-800 shadow-inner shadow-slate-900/5 placeholder:text-slate-400 focus:border-cyan-400 focus:outline-none focus:ring-2 focus:ring-cyan-400/25"
            placeholder="Ask about Microsoft, Apple, Google…"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                handleSubmit()
              }
            }}
            aria-label="Chat message"
          />
          <button
            type="button"
            onClick={() => handleSubmit()}
            disabled={loading}
            className="shrink-0 rounded-xl bg-gradient-to-r from-cyan-600 to-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-md shadow-cyan-600/25 transition hover:from-cyan-500 hover:to-indigo-500 disabled:cursor-not-allowed disabled:opacity-45 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400/50"
          >
            Send
          </button>
        </div>
      </footer>
    </div>
  )
}
