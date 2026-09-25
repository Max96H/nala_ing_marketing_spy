import { useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { api } from '../api'

const SUGGESTIONS = [
  'How does our tone compare to N26?',
  'What changed this week?',
  'Which bank uses the most casual language?',
  'What topics are we missing that competitors use?',
]

export default function Chatbot() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState(null)
  const scrollRef = useRef(null)

  const send = async (text) => {
    const question = text ?? input
    if (!question.trim() || sending) return

    const next = [...messages, { role: 'user', content: question }]
    setMessages(next)
    setInput('')
    setSending(true)
    setError(null)

    try {
      const reply = await api.chat(next)
      setMessages([...next, reply])
    } catch (e) {
      setError(e.message)
    } finally {
      setSending(false)
      setTimeout(() => {
        scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
      }, 50)
    }
  }

  return (
    <div className="chat-wrap">
      <div className="chat-messages" ref={scrollRef}>
        {messages.length === 0 && (
          <div className="chat-suggestions">
            {SUGGESTIONS.map((s) => (
              <button key={s} className="chat-suggestion" onClick={() => send(s)}>
                {s}
              </button>
            ))}
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`chat-msg ${m.role}`}>
            {m.role === 'assistant' ? (
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown>
            ) : (
              m.content
            )}
          </div>
        ))}
        {sending && <div className="chat-msg assistant thinking">Thinking…</div>}
        {error && <div className="chat-msg assistant">Something went wrong: {error}</div>}
      </div>
      <div className="chat-input-row">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && send()}
          placeholder="Ask about the scraped campaign data…"
          disabled={sending}
        />
        <button onClick={() => send()} disabled={sending || !input.trim()}>
          Send
        </button>
      </div>
    </div>
  )
}
