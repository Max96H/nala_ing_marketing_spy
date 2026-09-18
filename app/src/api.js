const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function getJSON(path) {
  const res = await fetch(`${API_BASE}${path}`)
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `${path} failed (${res.status})`)
  }
  return res.json()
}

export const api = {
  summary: () => getJSON('/api/summary'),
  pages: () => getJSON('/api/pages'),
  positioning: () => getJSON('/api/positioning'),
  radar: () => getJSON('/api/radar'),
  changes: () => getJSON('/api/changes'),
  gaps: () => getJSON('/api/gaps'),
  chat: async (messages) => {
    const res = await fetch(`${API_BASE}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages }),
    })
    if (!res.ok) {
      const body = await res.json().catch(() => ({}))
      throw new Error(body.detail || `chat failed (${res.status})`)
    }
    return res.json()
  },
}

// bank name -> categorical color (kept in sync with the hex values in index.css),
// with a stable fallback for banks not in our known set (e.g. a teammate adds
// Argenta/N26/bunq later)
const BANK_COLOR_MAP = {
  ING: '#d97a3d',
  KBC: '#2e7d6b',
  'BNP Paribas Fortis': '#3a5f8a',
  Belfius: '#b23a48',
  Revolut: '#2b2f36',
}

export function bankColor(bank) {
  return BANK_COLOR_MAP[bank] || '#7b5ea7'
}
