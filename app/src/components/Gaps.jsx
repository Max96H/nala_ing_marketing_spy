import { useEffect, useState } from 'react'
import { api } from '../api'
import { ErrorState } from './Overview'

export default function Gaps() {
  const [rows, setRows] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.gaps().then(setRows).catch((e) => setError(e.message))
  }, [])

  if (error) return <ErrorState message={error} />
  if (!rows) return <div className="empty-state">Loading…</div>

  return (
    <div className="panel">
      {rows.length === 0 ? (
        <div className="empty-state">
          No gaps computed yet. Run <code>analysis.py</code> after <code>analyst.py</code>.
        </div>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Topic</th>
              <th>Used by</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i}>
                <td>
                  <span className="badge gap">{r.topic}</span>
                </td>
                <td>{r.used_by}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <p style={{ color: 'var(--color-ink-soft)', fontSize: 13, marginTop: 16 }}>
        Candidate whitespace — a topic worth a look, not an automatic recommendation.
      </p>
    </div>
  )
}
