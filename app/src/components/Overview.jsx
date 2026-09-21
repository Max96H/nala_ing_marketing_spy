import { useEffect, useState } from 'react'
import { api } from '../api'

export default function Overview() {
  const [pages, setPages] = useState(null)
  const [summary, setSummary] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    Promise.all([api.pages(), api.summary()])
      .then(([p, s]) => { setPages(p); setSummary(s) })
      .catch((e) => setError(e.message))
  }, [])

  if (error) return <ErrorState message={error} />
  if (!pages) return <div className="empty-state">Loading…</div>

  return (
    <div>
      <div className="summary-row">
        <Stat label="Pages scraped" value={summary?.pages ?? '—'} />
        <Stat label="Banks covered" value={summary?.banks ?? '—'} />
        <Stat label="Pages analyzed" value={summary?.analyzed ?? '—'} />
        <Stat label="Changes flagged" value={summary?.changes ?? '—'} />
      </div>

      <div className="panel">
        {pages.length === 0 ? (
          <div className="empty-state">
            No pages yet. Run <code>collector.py</code> (and <code>merge_db.py</code>, if using
            a merged team database) first.
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Bank</th>
                <th>Page type</th>
                <th>Headline</th>
                <th>Tone</th>
                <th>Offer</th>
                <th>Scraped by</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {pages.map((p) => (
                <tr key={p.id}>
                  <td>{p.bank}</td>
                  <td>{p.page_type}</td>
                  <td>{p.headline || '—'}</td>
                  <td>{p.tone || '—'}</td>
                  <td>
                    {p.has_numeric_offer === 'True' ? (
                      <span className="badge offer">Yes</span>
                    ) : (
                      '—'
                    )}
                  </td>
                  <td>{p.scraped_by || '—'}</td>
                  <td>{p.scrape_date}</td>
                </tr>
              ))}
            </tbody>
          </table>
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
