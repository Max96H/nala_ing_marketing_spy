import { useEffect, useMemo, useState } from 'react'
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

function formatPageType(label) {
  if (!label) return 'Uncategorized'
  return label
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

export default function PositioningMap() {
  const [rows, setRows] = useState(null)
  const [error, setError] = useState(null)
  const [selectedPageTypes, setSelectedPageTypes] = useState(new Set())

  useEffect(() => {
    api
      .positioning()
      .then((data) => {
        setRows(data)
        const initialTypes = new Set(data.map((r) => r.page_type || 'uncategorized'))
        setSelectedPageTypes(initialTypes)
      })
      .catch((e) => setError(e.message))
  }, [])

  const availablePageTypes = useMemo(() => {
    if (!rows) return []
    const types = new Set(rows.map((r) => r.page_type || 'uncategorized'))
    return Array.from(types).sort()
  }, [rows])

  const filteredRows = useMemo(() => {
    if (!rows) return []
    return rows.filter((r) => {
      const type = r.page_type || 'uncategorized'
      return selectedPageTypes.has(type)
    })
  }, [rows, selectedPageTypes])

  const togglePageType = (type) => {
    setSelectedPageTypes((prev) => {
      const next = new Set(prev)
      if (next.has(type)) {
        next.delete(type)
      } else {
        next.add(type)
      }
      return next
    })
  }

  const selectAll = () => setSelectedPageTypes(new Set(availablePageTypes))
  const clearAll = () => setSelectedPageTypes(new Set())

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
      {/* Controls */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 10,
        }}
      >
        <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-ink-soft)' }}>
          Filter by Page Type:
        </span>
        <div style={{ display: 'flex', gap: 8, fontSize: 12 }}>
          <button
            onClick={selectAll}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--color-accent)',
              cursor: 'pointer',
              padding: 0,
              fontWeight: 500,
            }}
          >
            Select All
          </button>
          <span style={{ color: 'var(--color-border)' }}>|</span>
          <button
            onClick={clearAll}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--color-accent)',
              cursor: 'pointer',
              padding: 0,
              fontWeight: 500,
            }}
          >
            Clear All
          </button>
        </div>
      </div>

      <div className="chat-suggestions" style={{ marginBottom: 20 }}>
        {availablePageTypes.map((type) => {
          const isSelected = selectedPageTypes.has(type)
          return (
            <button
              key={type}
              onClick={() => togglePageType(type)}
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
              {formatPageType(type)}
            </button>
          )
        })}
      </div>

      {/* Map Chart */}
      <ResponsiveContainer width="100%" height={480}>
        <ScatterChart margin={{ top: 10, right: 100, bottom: 20, left: 0 }}>
          <CartesianGrid stroke="var(--color-border)" />
          <XAxis
            type="number"
            dataKey="pca_x"
            tick={{ fontSize: 12 }}
            label={{
              value: 'Content Focus',
              position: 'bottom',
              offset: 0,
              style: { fontSize: 12, fill: 'var(--color-ink-soft)' },
            }}
          />
          <YAxis
            type="number"
            dataKey="pca_y"
            tick={{ fontSize: 12 }}
            label={{
              value: 'Tone & Topic Variation',
              angle: -90,
              position: 'insideLeft',
              style: { fontSize: 12, fill: 'var(--color-ink-soft)', textAnchor: 'middle' },
            }}
          />
          <Tooltip
            cursor={{ strokeDasharray: '3 3' }}
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null
              const d = payload[0].payload
              
              // Normalize topics list display
              const topics = Array.isArray(d.topics_list)
                ? d.topics_list.join(', ')
                : d.topics_list || 'N/A'

              return (
                <div
                  style={{
                    background: 'var(--color-surface)',
                    border: '1px solid var(--color-border)',
                    borderRadius: 8,
                    padding: '10px 14px',
                    fontSize: 12.5,
                    maxWidth: 320,
                    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.08)',
                  }}
                >
                  <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 6 }}>
                    {d.bank?.toUpperCase()} —{' '}
                    <span style={{ fontWeight: 500, color: 'var(--color-ink-soft)' }}>
                      {formatPageType(d.page_type)}
                    </span>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    <div>
                      <strong style={{ color: 'var(--color-ink-soft)' }}>Tone: </strong>
                      <span>{d.tone || 'N/A'}</span>
                    </div>

                    <div>
                      <strong style={{ color: 'var(--color-ink-soft)' }}>Value Proposition: </strong>
                      <span>{d.value_proposition || 'N/A'}</span>
                    </div>

                    <div>
                      <strong style={{ color: 'var(--color-ink-soft)' }}>Topics: </strong>
                      <span>{topics}</span>
                    </div>
                  </div>
                </div>
              )
            }}
          />
          <Legend
            layout="vertical"
            position="right"
            itemStyle={{ marginBottom: 30 }}
            wrapperStyle={{ paddingLeft: 20 }}
            formatter={(value) => value}
          />
          {banks.map((bank) => (
            <Scatter
              key={bank}
              name={bank}
              data={filteredRows.filter((r) => r.bank === bank)}
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