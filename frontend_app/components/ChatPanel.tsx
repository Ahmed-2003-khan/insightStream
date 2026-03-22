'use client'
import { useState } from 'react'
import { queryIntelligence } from '@/lib/api'
import SignalBadge from './SignalBadge'

interface Message {
  role: 'user' | 'assistant'
  content: string
  signal_label?: string
  signal_confidence?: number
  cache_hit?: boolean
}

export default function ChatPanel() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput]       = useState('')
  const [loading, setLoading]   = useState(false)

  async function handleSubmit() {
    if (!input.trim() || loading) return
    const userMsg = input.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: userMsg }])
    setLoading(true)

    try {
      const data = await queryIntelligence(userMsg)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.report,
        signal_label: data.signal_label,
        signal_confidence: data.signal_confidence,
        cache_hit: data.cache_hit
      }])
    } catch {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Error fetching response. Is the backend running?'
      }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-full bg-white rounded-xl border">
      <div className="p-3 border-b">
        <h2 className="text-sm font-semibold text-gray-500">Intelligence Chat</h2>
      </div>
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <p className="text-sm text-gray-400 text-center mt-8">
            Ask anything about tracked companies...
          </p>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] rounded-xl px-4 py-3 text-sm ${
              msg.role === 'user'
                ? 'bg-blue-500 text-white'
                : 'bg-gray-50 text-gray-700 border'
            }`}>
              <p className="whitespace-pre-wrap">{msg.content}</p>
              {msg.role === 'assistant' && msg.signal_label && (
                <div className="flex items-center gap-2 mt-2 pt-2 border-t border-gray-200">
                  <SignalBadge
                    label={msg.signal_label}
                    confidence={msg.signal_confidence || 0}
                  />
                  {msg.cache_hit && (
                    <span className="text-xs text-gray-400">⚡ cached</span>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-50 border rounded-xl px-4 py-3 text-sm text-gray-400">
              Analysing...
            </div>
          </div>
        )}
      </div>
      <div className="p-3 border-t flex gap-2">
        <input
          className="flex-1 text-sm border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-300"
          placeholder="Ask about Microsoft, Apple, Google..."
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSubmit()}
        />
        <button
          onClick={handleSubmit}
          disabled={loading}
          className="bg-blue-500 text-white text-sm px-4 py-2 rounded-lg hover:bg-blue-600 disabled:opacity-50"
        >
          Send
        </button>
      </div>
    </div>
  )
}
