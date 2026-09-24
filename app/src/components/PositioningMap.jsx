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

// Helper function to format page types nicely ("utility_security_legal" -> "Utility Security Legal")
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
    api.positioning()
      .then((data) => {
        setRows(data)
        // Select all unique page types by default upon loading
        const initialTypes = new Set(data.map((r) => r.page_type || 'uncategorized'))
        setSelectedPageTypes(initialTypes)
      })
      .catch((e) => setError(e.message))
  }, [])

  // Extract all distinct page types sorted alphabetically
  const availablePageTypes = useMemo(() => {
    if (!rows) return []
    const types = new Set(rows.map((r) => r.page_type || 'uncategorized'))
    return Array.from(types).sort()
  }, [rows])

  // Filter rows by currently selected page types
  const filteredRows = useMemo(() => {
    if (!rows) return []
    return rows.filter((r) => {
      const type = r.page_type || 'uncategorized'
      return selectedPageTypes.has(type)
    })
  }, [rows, selectedPageTypes])

  // Toggle page type selection
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

  // Select all page types
  const selectAll = () => {
    setSelectedPageTypes(new Set(availablePageTypes))
  }

  // Clear all page types
  const clearAll = () => {
    setSelectedPageTypes(new Set())
  }

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
      {/* Page Type Filter Bar */}
      <div style={{ marginBottom: 20 }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justify: 'space-between',
            marginBottom: 8,
          }}
        >
          <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-ink-soft, #555)' }}>
            Filter by Page Type:
          </span>
          <div style={{ display: 'flex', gap: 8, fontSize: 12 }}>
            <button
              onClick={selectAll}
              style={{
                background: 'none',
                border: 'none',
                color: '#0066cc',
                cursor: 'pointer',
                padding: 0,
              }}
            >
              Select All
            </button>
            <span style={{ color: '#ccc' }}>|</span>
            <button
              onClick={clearAll}
              style={{
                background: 'none',
                border: 'none',
                color: '#0066cc',
                cursor: 'pointer',
                padding: 0,
              }}
            >
              Clear All
            </button>
          </div>
        </div>

        {/* Toggle Chips */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {availablePageTypes.map((type) => {
            const isSelected = selectedPageTypes.has(type)
            return (
              <button
                key={type}
                onClick={() => togglePageType(type)}
                style={{
                  padding: '5px 12px',
                  borderRadius: 16,
                  fontSize: 12,
                  fontWeight: 500,
                  cursor: 'pointer',
                  border: isSelected ? '1px solid #0066cc' : '1px solid #d1d5db',
                  backgroundColor: isSelected ? '#0066cc' : '#f3f4f6',
                  color: isSelected ? '#ffffff' : '#4b5563',
                  transition: 'all 0.15s ease',
                }}
              >
                {formatPageType(type)}
              </button>
            )
          })}
        </div>
      </div>

      {/* Responsive Scatter Plot */}
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
                  <strong>{d.bank}</strong> — {formatPageType(d.page_type)}
                </div>
              )
            }}
          />
          <Legend formatter={(value) => value} />
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