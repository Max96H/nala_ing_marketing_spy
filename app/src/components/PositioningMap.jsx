import { useEffect, useState } from 'react'
import {
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'
import { api, bankColor } from '../api'
import { ErrorState } from './Overview'

export default function PositioningMap() {
  const [rows, setRows] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.positioning().then(setRows).catch((e) => setError(e.message))
  }, [])

  if (error) return <ErrorState message={error} />
  if (!rows) return <div className="empty-state">Loading…</div>

  if (rows.length === 0) {
    return (
      <div className="panel">
        <div className="empty-state">
          No positioning data yet. Run <code>analysis.py</code> after <code>analyst.py</code> has
          filled in tone, value proposition, and topics for at least a few pages.
        </div>
      </div>
    )
  }

  const banks = [...new Set(rows.map((r) => r.bank))]

  return (
    <div className="panel">
      <ResponsiveContainer width="100%" height={480}>
        <ScatterChart margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
          <CartesianGrid stroke="#e4e7eb" />
          <XAxis type="number" dataKey="pca_x" tick={{ fontSize: 12 }} />
          <YAxis type="number" dataKey="pca_y" tick={{ fontSize: 12 }} />
          <Tooltip
            cursor={{ strokeDasharray: '3 3' }}
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null
              const d = payload[0].payload
              return (
                <div
                  style={{
                    background: '#fff',
                    border: '1px solid #e4e7eb',
                    borderRadius: 6,
                    padding: '8px 12px',
                    fontSize: 13,
                  }}
                >
                  <strong>{d.bank}</strong> — {d.page_type}
                </div>
              )
            }}
          />
          <Legend />
          {banks.map((bank) => (
            <Scatter
              key={bank}
              name={bank}
              data={rows.filter((r) => r.bank === bank)}
              fill={bankColor(bank)}
            />
          ))}
        </ScatterChart>
      </ResponsiveContainer>
      <p style={{ color: 'var(--color-ink-soft)', fontSize: 13, marginTop: 4 }}>
        Each point is one page. Closer points share more similar tone, value proposition, and
        topics — position is relative, not a literal distance metric.
      </p>
    </div>
  )
}
