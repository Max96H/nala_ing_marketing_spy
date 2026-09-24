import { useEffect, useMemo, useState } from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts'
import { api, bankColor } from '../api'

// Helper function to convert "utility_security_legal" -> "Utility Security Legal"
function formatPageType(label) {
  if (!label) return ''
  return label
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

export default function Overview() {
  const [pages, setPages] = useState(null)
  const [summary, setSummary] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    Promise.all([api.pages(), api.summary()])
      .then(([p, s]) => {
        setPages(p)
        setSummary(s)
      })
      .catch((e) => setError(e.message))
  }, [])

  // Process data into pivot format required by Recharts and calculate unique page types
  const { chartData, uniqueBanks, pageTypeCount } = useMemo(() => {
    if (!pages || pages.length === 0) {
      return { chartData: [], uniqueBanks: [], pageTypeCount: 0 }
    }

    const banksSet = new Set()
    const pageTypesSet = new Set()
    const countsByCategory = {}

    pages.forEach((p) => {
      const bank = p.bank || 'unknown'
      const category = p.page_type || 'uncategorized'

      banksSet.add(bank)
      if (p.page_type) {
        pageTypesSet.add(p.page_type)
      }

      if (!countsByCategory[category]) {
        countsByCategory[category] = { 
          page_type: category, 
          formatted_page_type: formatPageType(category) 
        }
      }

      countsByCategory[category][bank] = (countsByCategory[category][bank] || 0) + 1
    })

    const uniqueBanksList = Array.from(banksSet)

    // Convert object map to array and sort categories by total page count descending
    const formattedData = Object.values(countsByCategory).sort((a, b) => {
      const totalA = uniqueBanksList.reduce((sum, bank) => sum + (a[bank] || 0), 0)
      const totalB = uniqueBanksList.reduce((sum, bank) => sum + (b[bank] || 0), 0)
      return totalB - totalA
    })

    return { 
      chartData: formattedData, 
      uniqueBanks: uniqueBanksList, 
      pageTypeCount: pageTypesSet.size 
    }
  }, [pages])

  if (error) return <ErrorState message={error} />
  if (!pages) return <div className="empty-state">Loading…</div>

  return (
    <div>
      {/* Summary KPI Cards */}
      <div className="summary-row">
        <Stat label="Pages scraped" value={summary?.pages ?? '—'} />
        <Stat label="Banks covered" value={summary?.banks ?? '—'} />
        <Stat label="Pages analyzed" value={summary?.analyzed ?? '—'} />
        <Stat label="Page types" value={pageTypeCount} />
      </div>

      {/* Clustered Bar Chart Panel */}
      <div className="panel" style={{ padding: '24px', marginTop: '20px' }}>
        <h3 style={{ marginTop: 0, marginBottom: '20px' }}>
          Page Distribution Across Banks
        </h3>

        {chartData.length === 0 ? (
          <div className="empty-state">
            No pages found. Run <code>collector.py</code> to populate the database.
          </div>
        ) : (
          <div style={{ width: '100%', height: 450 }}>
            <ResponsiveContainer>
              <BarChart
                data={chartData}
                margin={{ top: 20, right: 30, left: 10, bottom: 80 }}
              >
                <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.3} />
                <XAxis
                  dataKey="formatted_page_type"
                  angle={-35}
                  textAnchor="end"
                  interval={0}
                  tick={{ fontSize: 12 }}
                />
                <YAxis allowDecimals={false} />
                <Tooltip
                  cursor={{ fill: 'rgba(0, 0, 0, 0.05)' }}
                  contentStyle={{ borderRadius: '8px', boxShadow: '0 2px 8px rgba(0,0,0,0.15)' }}
                />
                <Legend
                  verticalAlign="top"
                  wrapperStyle={{ paddingBottom: '20px' }}
                  formatter={(value) => value}
                />

                {/* Dynamically render a bar for each unique bank using bankColor() from api.js */}
                {uniqueBanks.map((bank) => (
                  <Bar
                    key={bank}
                    dataKey={bank}
                    name={bank}
                    fill={bankColor(bank)}
                    radius={[4, 4, 0, 0]}
                  />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  )
}

function Stat({ label, value }) {
  return (
    <div className="summary-stat">
      <div className="value">{value}</div>
      <div className="label">{label}</div>
    </div>
  )
}

export function ErrorState({ message }) {
  return (
    <div className="panel">
      <div className="empty-state">Couldn't load data: {message}</div>
    </div>
  )
}