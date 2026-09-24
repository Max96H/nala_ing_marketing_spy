import { useEffect, useMemo, useState } from 'react'
import { api, bankColor } from '../api'
import { ErrorState } from './Overview'

function formatPageType(label) {
  if (!label) return 'Uncategorized'
  return label
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

// "Best" competitor page per bank/category = most substantial one, using content
// length as the proxy for "the real flagship page" vs. a thin stub. A judgment
// call — swap out if a better signal becomes available.
function pickBest(pagesForBank) {
  return [...pagesForBank].sort(
    (a, b) => (b.raw_text || '').length - (a.raw_text || '').length
  )[0]
}

function scoreColor(score) {
  if (score == null) return 'var(--color-ink-faint)'
  if (score >= 8) return 'var(--color-accent)'
  if (score >= 5) return 'var(--color-amber)'
  return 'var(--color-ink-faint)'
}

export default function ProductComparison() {
  const [pages, setPages] = useState(null)
  const [uxScores, setUxScores] = useState(null)
  const [recommendations, setRecommendations] = useState(null)
  const [error, setError] = useState(null)
  const [selectedType, setSelectedType] = useState(null)
  const [selectedIngId, setSelectedIngId] = useState(null)

  useEffect(() => {
    Promise.all([api.pages(), api.uxScores(), api.productRecommendations()])
      .then(([p, ux, recs]) => { setPages(p); setUxScores(ux); setRecommendations(recs) })
      .catch((e) => setError(e.message))
  }, [])

  const scoreByPageId = useMemo(() => {
    const map = {}
    for (const row of uxScores || []) map[row.page_id] = row
    return map
  }, [uxScores])

  const recommendationByPair = useMemo(() => {
    const map = {}
    for (const row of recommendations || []) {
      map[`${row.ing_page_id}_${row.competitor_page_id}`] = row.recommendation
    }
    return map
  }, [recommendations])

  const analyzed = useMemo(
    () => (pages ? pages.filter((p) => p.tone && p.tone.trim() !== '') : []),
    [pages]
  )

  const availableTypes = useMemo(() => {
    const counts = {}
    for (const p of analyzed) {
      const type = p.page_type || 'uncategorized'
      counts[type] = (counts[type] || 0) + 1
    }
    return Object.entries(counts).sort((a, b) => b[1] - a[1])
  }, [analyzed])

  useEffect(() => {
    if (!selectedType && availableTypes.length > 0) {
      setSelectedType(availableTypes[0][0])
    }
  }, [availableTypes, selectedType])

  useEffect(() => {
    setSelectedIngId(null) // reset the chosen ING product whenever the category changes
  }, [selectedType])

  const pagesInCategory = useMemo(
    () => analyzed.filter((p) => (p.page_type || 'uncategorized') === selectedType),
    [analyzed, selectedType]
  )

  const ingProducts = useMemo(
    () => pagesInCategory.filter((p) => (p.bank || '').toLowerCase() === 'ing'),
    [pagesInCategory]
  )

  const competitorPages = useMemo(() => {
    const byBank = {}
    for (const p of pagesInCategory) {
      if ((p.bank || '').toLowerCase() === 'ing') continue
      const bank = p.bank || 'unknown'
      byBank[bank] = byBank[bank] ? byBank[bank].concat(p) : [p]
    }
    return Object.values(byBank).map(pickBest).sort((a, b) => a.bank.localeCompare(b.bank))
  }, [pagesInCategory])

  // Skip the extra click when ING only has one product in this category
  useEffect(() => {
    if (!selectedIngId && ingProducts.length === 1) {
      setSelectedIngId(ingProducts[0].id)
    }
  }, [ingProducts, selectedIngId])

  const selectedIngPage = ingProducts.find((p) => p.id === selectedIngId) || null

  if (error) return <ErrorState message={error} />
  if (!pages || !uxScores || !recommendations) return <div className="empty-state">Loading…</div>

  if (availableTypes.length === 0) {
    return (
      <div className="panel">
        <div className="empty-state">
          No analyzed pages yet. Run <code>analyst.py</code> (categories need page_type
          classification first) before product-level comparison is possible.
        </div>
      </div>
    )
  }

  const ingScore = selectedIngPage ? (scoreByPageId[selectedIngPage.id]?.total_score ?? null) : null

  return (
    <div>
      {/* Category filter */}
      <div className="panel" style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-ink-soft)', marginBottom: 10 }}>
          1. Product category
        </div>
        <div className="chat-suggestions" style={{ marginBottom: 0 }}>
          {availableTypes.map(([type, count]) => {
            const isSelected = type === selectedType
            return (
              <button
                key={type}
                onClick={() => setSelectedType(type)}
                className="chat-suggestion"
                style={
                  isSelected
                    ? { borderColor: 'var(--color-accent)', color: 'var(--color-accent)',
                        background: 'var(--color-accent-soft)', fontWeight: 500 }
                    : {}
                }
              >
                {formatPageType(type)} ({count})
              </button>
            )
          })}
        </div>
      </div>

      {/* ING product picker — names only, no score suffix */}
      {ingProducts.length === 0 ? (
        <div className="panel">
          <div className="empty-state">
            ING doesn't have an analyzed {formatPageType(selectedType).toLowerCase()} page —
            nothing to anchor a comparison to for this category.
          </div>
        </div>
      ) : (
        <div className="panel" style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-ink-soft)', marginBottom: 10 }}>
            2. ING product to compare
          </div>
          <div className="chat-suggestions" style={{ marginBottom: 0 }}>
            {ingProducts.map((p) => {
              const isSelected = p.id === selectedIngId
              return (
                <button
                  key={p.id}
                  onClick={() => setSelectedIngId(p.id)}
                  className="chat-suggestion"
                  style={
                    isSelected
                      ? { borderColor: 'var(--color-accent)', color: 'var(--color-accent)',
                          background: 'var(--color-accent-soft)', fontWeight: 500 }
                      : {}
                  }
                >
                  {p.headline || p.page_url}
                </button>
              )
            })}
          </div>
        </div>
      )}

      {/* Comparison table: selected ING product pinned, best-per-bank for competitors */}
      {selectedIngPage && (
        <div className="panel">
          {competitorPages.length === 0 ? (
            <div className="empty-state">
              No competitor has an analyzed {formatPageType(selectedType).toLowerCase()} page yet
              to compare against.
            </div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Bank</th>
                  <th>Headline</th>
                  <th>Tone</th>
                  <th>Value proposition</th>
                  <th>UX score</th>
                  <th>Recommendation for ING</th>
                </tr>
              </thead>
              <tbody>
                <ComparisonRow page={selectedIngPage} score={ingScore} recommendation="—" pinned />
                {competitorPages.map((p) => {
                  const score = scoreByPageId[p.id]?.total_score ?? null
                  const recommendation =
                    recommendationByPair[`${selectedIngPage.id}_${p.id}`] ??
                    'Not generated yet — run product_recommendations.py.'
                  return (
                    <ComparisonRow key={p.id} page={p} score={score} recommendation={recommendation} />
                  )
                })}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  )
}

function ComparisonRow({ page, score, recommendation, pinned }) {
  return (
    <tr style={pinned ? { background: 'var(--color-accent-soft)' } : undefined}>
      <td>
        <span
          style={{
            display: 'inline-flex', alignItems: 'center', gap: 6,
            fontWeight: pinned ? 700 : 500,
            color: pinned ? 'var(--color-accent)' : 'var(--color-ink)',
          }}
        >
          <span style={{ width: 8, height: 8, borderRadius: '50%', background: bankColor(page.bank), flexShrink: 0 }} />
          {page.bank}
        </span>
      </td>
      <td>{page.headline || '—'}</td>
      <td>{page.tone || '—'}</td>
      <td>{page.value_proposition || '—'}</td>
      <td>
        <span style={{ fontWeight: 700, color: scoreColor(score) }}>
          {score != null ? `${score}/10` : 'not scored yet'}
        </span>
      </td>
      <td style={{ color: pinned ? 'var(--color-ink-faint)' : 'var(--color-ink)' }}>
        {recommendation}
      </td>
    </tr>
  )
}