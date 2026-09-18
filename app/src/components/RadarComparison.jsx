import { useEffect, useMemo, useState } from 'react'
import {
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  Legend,
  Tooltip,
} from 'recharts'
import { api, bankColor } from '../api'
import { ErrorState } from './Overview'

const DIMENSION_LABELS = {
  promo_intensity: 'Promotional intensity',
  visual_richness: 'Visual richness',
  colour_vibrancy: 'Colour vibrancy',
  content_density: 'Content density',
  topic_diversity: 'Topic diversity',
}

export default function RadarComparison() {
  const [rows, setRows] = useState(null)
  const [error, setError] = useState(null)
  const [selected, setSelected] = useState([])

  useEffect(() => {
    api.radar().then((data) => {
      setRows(data)
      const banks = [...new Set(data.map((r) => r.bank))]
      setSelected(banks.slice(0, 3))
    }).catch((e) => setError(e.message))
  }, [])

  const banks = useMemo(() => (rows ? [...new Set(rows.map((r) => r.bank))] : []), [rows])

  const chartData = useMemo(() => {
    if (!rows) return []
    const dims = [...new Set(rows.map((r) => r.dimension))]
    return dims.map((dim) => {
      const point = { dimension: DIMENSION_LABELS[dim] || dim }
      for (const bank of selected) {
        const match = rows.find((r) => r.bank === bank && r.dimension === dim)
        point[bank] = match ? Number(match.score) : 0
      }
      return point
    })
  }, [rows, selected])

  if (error) return <ErrorState message={error} />
  if (!rows) return <div className="empty-state">Loading…</div>

  if (rows.length === 0) {
    return (
      <div className="panel">
        <div className="empty-state">
          No radar data yet. Run <code>analysis.py</code> after <code>analyst.py</code>.
        </div>
      </div>
    )
  }

  const toggle = (bank) => {
    setSelected((prev) =>
      prev.includes(bank) ? prev.filter((b) => b !== bank) : [...prev, bank]
    )
  }

  return (
    <div className="panel">
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 20 }}>
        {banks.map((bank) => (
          <button
            key={bank}
            onClick={() => toggle(bank)}
            className="chat-suggestion"
            style={
              selected.includes(bank)
                ? { borderColor: bankColor(bank), color: bankColor(bank) }
                : {}
            }
          >
            {bank}
          </button>
        ))}
      </div>

      {selected.length === 0 ? (
        <div className="empty-state">Pick at least one bank above to compare.</div>
      ) : (
        <ResponsiveContainer width="100%" height={440}>
          <RadarChart data={chartData}>
            <PolarGrid stroke="#e4e7eb" />
            <PolarAngleAxis dataKey="dimension" tick={{ fontSize: 12.5 }} />
            <PolarRadiusAxis domain={[0, 1]} tick={{ fontSize: 10 }} />
            <Tooltip />
            <Legend />
            {selected.map((bank) => (
              <Radar
                key={bank}
                name={bank}
                dataKey={bank}
                stroke={bankColor(bank)}
                fill={bankColor(bank)}
                fillOpacity={0.15}
              />
            ))}
          </RadarChart>
        </ResponsiveContainer>
      )}
      <p style={{ color: 'var(--color-ink-soft)', fontSize: 13, marginTop: 4 }}>
        Scores are normalized 0–1 across banks. These are measurable proxies for the brief's five
        dimensions (tone & messaging, visuals, colour, layout, value proposition) — not the
        dimensions themselves.
      </p>
    </div>
  )
}
