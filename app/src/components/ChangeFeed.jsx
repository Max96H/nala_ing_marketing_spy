import { useEffect, useState } from 'react'
import { api } from '../api'
import { ErrorState } from './Overview'

export default function ChangeFeed() {
  const [rows, setRows] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.changes().then(setRows).catch((e) => setError(e.message))
  }, [])

  if (error) return <ErrorState message={error} />
  if (!rows) return <div className="empty-state">Loading…</div>

  return (
    <div className="panel">
      {rows.length === 0 ? (
        <div className="empty-state">
          No changes detected yet — needs at least two scrape runs on different dates. Run{' '}
          <code>collector.py</code> again in a few days, then <code>change_watcher.py</code>.
        </div>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Bank</th>
              <th>Field</th>
              <th>Previous</th>
              <th>Current</th>
              <th>Detected</th>
            </tr>
          </thead>
          <tbody>
            {rows
              .sort((a, b) => (a.detected_date < b.detected_date ? 1 : -1))
              .map((r) => (
                <tr key={r.id}>
                  <td>{r.bank}</td>
                  <td>{r.field_changed}</td>
                  <td>{truncate(r.previous_value)}</td>
                  <td>{truncate(r.current_value)}</td>
                  <td>{r.detected_date}</td>
                </tr>
              ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

function truncate(text, max = 60) {
  if (!text) return '—'
  return text.length > max ? text.slice(0, max) + '…' : text
}
