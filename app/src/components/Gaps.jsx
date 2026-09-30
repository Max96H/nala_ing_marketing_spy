import { useEffect, useState } from 'react'
import { api } from '../api'
import { ErrorState } from './Overview'

function rankByCompetitorCount(rows) {
  return [...rows].sort((a, b) => {
    const countA = (a.used_by || '').split(',').filter(Boolean).length
    const countB = (b.used_by || '').split(',').filter(Boolean).length
    if (countB !== countA) return countB - countA
    return (a.topic || '').localeCompare(b.topic || '')
  })
}

export default function Gaps() {
  const [recommendations, setRecommendations] = useState(null)
  const [gaps, setGaps] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    Promise.all([api.recommendations(), api.gaps()])
      .then(([recs, g]) => { setRecommendations(recs); setGaps(g) })
      .catch((e) => setError(e.message))
  }, [])

  if (error) return <ErrorState message={error} />
  if (!recommendations || !gaps) return <div className="empty-state">Loading…</div>

  if (gaps.length === 0) {
    return (
      <div className="panel">
        <div className="empty-state">
          No gaps computed yet. Run <code>analysis.py</code> after <code>analyst.py</code>.
        </div>
      </div>
    )
  }

  const haveRecommendations = recommendations.length > 0
  const ranked = rankByCompetitorCount(haveRecommendations ? recommendations : gaps)

  return (
    <div>
      {!haveRecommendations && (
        <div className="panel" style={{ marginBottom: 16 }}>
          <p style={{ color: 'var(--color-ink-soft)', fontSize: 13.5, margin: 0 }}>
            Recommendations weren't generated for this run (no LLM provider configured when{' '}
            <code>analysis.py</code> last ran) — showing the raw gap topics below instead.
          </p>
        </div>
      )}
      <div className="panel">
        {ranked.map((r, i) => {
          const competitorCount = (r.used_by || '').split(',').filter(Boolean).length
          return (
            <div
              key={r.topic}
              style={{
                display: 'flex',
                gap: 14,
                padding: '16px 0',
                borderBottom: i < ranked.length - 1 ? '1px solid var(--color-border)' : 'none',
              }}
            >
              <div
                style={{
                  fontFamily: 'var(--font-display)',
                  fontWeight: 700,
                  color: 'var(--color-ink-faint)',
                  fontSize: 15,
                  width: 22,
                  flexShrink: 0,
                }}
              >
                {i + 1}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
                  <span className="badge gap">{r.topic}</span>
                  <span style={{ color: 'var(--color-ink-faint)', fontSize: 12.5 }}>
                    used by {competitorCount} competitor{competitorCount === 1 ? '' : 's'} — {r.used_by}
                  </span>
                </div>
                {r.recommendation && (
                  <p style={{ margin: 0, fontSize: 14, lineHeight: 1.5, color: 'var(--color-ink)' }}>
                    {r.recommendation}
                  </p>
                )}
              </div>
            </div>
          )
        })}
      </div>
      <p style={{ color: 'var(--color-ink-soft)', fontSize: 13, marginTop: 12 }}>
        Ranked by how many competitors use each topic. These are candidates worth a look, not
        automatic recommendations.
      </p>
    </div>
  )
}