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

// "Best" page per bank/category = most substantial one, using content length as
// the proxy for "the real flagship page" vs. a thin stub or a snippet caught by
// the category classifier. Simple and transparent, but a judgment call — swap
// this out if a better signal becomes available (e.g. explicit page priority).
function pickBest(pagesForBank) {
  return [...pagesForBank].sort(
    (a, b) => (b.raw_text || '').length - (a.raw_text || '').length
  )[0]
}

// Deterministic UX score out of 10 — a proxy built from fields we already scrape,
// not a rigorous audit. Documented in the Methodology tab. Each page can score:
//   +2 clear headline present
//   +1 supporting subtitle present
//   +2 clear call-to-action present
//   +2 concrete/quantified offer (has_numeric_offer)
//   +2 balanced visual support (some images, not an excessive wall of them)
//   +1 healthy content length (not a stub, not overwhelming)
function computeUxScore(page) {
  let score = 0
  if (page.headline && page.headline.trim().length > 5) score += 2
  if (page.subtitle && page.subtitle.trim().length > 0) score += 1
  if (page.cta_text && page.cta_text.trim().length > 0) score += 2
  if (page.has_numeric_offer) score += 2
  const images = page.image_count || 0
  if (images >= 1 && images <= 20) score += 2
  else if (images > 20) score += 1
  const wordCount = (page.raw_text || '').split(/\s+/).filter(Boolean).length
  if (wordCount >= 40 && wordCount <= 800) score += 1
  return score
}

function scoreColor(score) {
  if (score >= 8) return 'var(--color-accent)'
  if (score >= 5) return 'var(--color-amber)'
  return 'var(--color-ink-faint)'
}

// Rule-based, not LLM-generated — compares this competitor's page to ING's on
// the signals we actually measure, phrased cautiously ("worth" / "consider"),
// consistent with how gap recommendations are phrased elsewhere in the app.
function buildRecommendation(competitor, competitorScore, ing, ingScore) {
  if (competitorScore <= ingScore) {
    return "ING's page already scores as well or better here — no immediate action needed."
  }
  const reasons = []
  if (competitor.has_numeric_offer && !ing.has_numeric_offer) {
    reasons.push('leads with a concrete, quantified offer')
  }
  if (competitor.cta_text && !ing.cta_text) {
    reasons.push('has a clearer call-to-action')
  }
  const images = competitor.image_count || 0
  const ingImages = ing.image_count || 0
  if (images > ingImages && images <= 20) {
    reasons.push('uses more visual support')
  }
  const reasonText = reasons.length > 0 ? reasons.join(' and ') : 'scores higher on the measured signals overall'
  return `Worth a look — ${competitor.bank} ${reasonText}.`
}

export default function ProductComparison() {
  const [pages, setPages] = useState(null)
  const [error, setError] = useState(null)
  const [selectedType, setSelectedType] = useState(null)

  useEffect(() => {
    api.pages().then(setPages).catch((e) => setError(e.message))
  }, [])

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

  const bestPerBank = useMemo(() => {
    const inCategory = analyzed.filter((p) => (p.page_type || 'uncategorized') === selectedType)
    const byBank = {}
    for (const p of inCategory) {
      const bank = p.bank || 'unknown'
      byBank[bank] = byBank[bank] ? byBank[bank].concat(p) : [p]
    }
    return Object.values(byBank).map(pickBest)
  }, [analyzed, selectedType])

  const ingPage = bestPerBank.find((p) => (p.bank || '').toLowerCase() === 'ing') || null
  const competitorPages = bestPerBank
    .filter((p) => (p.bank || '').toLowerCase() !== 'ing')
    .sort((a, b) => a.bank.localeCompare(b.bank))

  if (error) return <ErrorState message={error} />
  if (!pages) return <div className="empty-state">Loading…</div>

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

  const ingScore = ingPage ? computeUxScore(ingPage) : null

  return (
    <div>
      <div className="panel" style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-ink-soft)', marginBottom: 10 }}>
          Product category
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
                    ? {
                        borderColor: 'var(--color-accent)',
                        color: 'var(--color-accent)',
                        background: 'var(--color-accent-soft)',
                        fontWeight: 500,
                      }
                    : {}
                }
              >
                {formatPageType(type)} ({count})
              </button>
            )
          })}
        </div>
      </div>

      {!ingPage ? (
        <div className="panel">
          <div className="empty-state">
            ING doesn't have an analyzed {formatPageType(selectedType).toLowerCase()} page —
            nothing to anchor a comparison to for this category.
          </div>
        </div>
      ) : (
        <div className="panel">
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
              <ComparisonRow page={ingPage} score={ingScore} recommendation="—" pinned />
              {competitorPages.map((p) => {
                const score = computeUxScore(p)
                return (
                  <ComparisonRow
                    key={p.id}
                    page={p}
                    score={score}
                    recommendation={buildRecommendation(p, score, ingPage, ingScore)}
                  />
                )
              })}
            </tbody>
          </table>
          {competitorPages.length === 0 && (
            <p style={{ color: 'var(--color-ink-soft)', fontSize: 13, marginTop: 12 }}>
              No competitor has an analyzed {formatPageType(selectedType).toLowerCase()} page yet
              to compare against.
            </p>
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
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
            fontWeight: pinned ? 700 : 500,
            color: pinned ? 'var(--color-accent)' : 'var(--color-ink)',
          }}
        >
          <span
            style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              background: bankColor(page.bank),
              flexShrink: 0,
            }}
          />
          {page.bank}
        </span>
      </td>
      <td>{page.headline || '—'}</td>
      <td>{page.tone || '—'}</td>
      <td>{page.value_proposition || '—'}</td>
      <td>
        <span style={{ fontWeight: 700, color: scoreColor(score) }}>{score}/10</span>
      </td>
      <td style={{ color: pinned ? 'var(--color-ink-faint)' : 'var(--color-ink)' }}>
        {recommendation}
      </td>
    </tr>
  )
}