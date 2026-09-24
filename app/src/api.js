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
  recommendations: () => getJSON('/api/recommendations'),
  uxScores: () => getJSON('/api/ux_scores'),
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

// bank name -> categorical color (kept in sync with the hex values in index.css).
// Keys are normalized (lowercased, trimmed) since real data comes through as the
// lowercase YAML keys from banks.yaml (e.g. "ing", "bnp"), not display names.
const BANK_COLOR_MAP = {
  ing: '#d97a3d',
  kbc: '#2e7d6b',
  bnp: '#3a5f8a',
  belfius: '#b23a48',
  revolut: '#2b2f36',
  n26: '#c9a227',
  bunq: '#4f6b3c',
  argenta: '#7b5ea7',
}

// Fallback palette for any bank not in the map above (added to banks.yaml later,
// or an unrecognized display-name variant). Picked deterministically from a hash
// of the name, so a given bank always gets the same color across renders/tabs —
// never all falling through to one identical color.
const FALLBACK_PALETTE = ['#7b5ea7', '#c9a227', '#4f6b3c', '#8a4f6b', '#3a7d5f', '#6b5a3a']

function hashString(str) {
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    hash = (hash * 31 + str.charCodeAt(i)) >>> 0
  }
  return hash
}

export function bankColor(bank) {
  const key = (bank || '').trim().toLowerCase()
  if (BANK_COLOR_MAP[key]) return BANK_COLOR_MAP[key]
  return FALLBACK_PALETTE[hashString(key) % FALLBACK_PALETTE.length]
}