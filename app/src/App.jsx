import { useState } from 'react'
import Overview from './components/Overview'
import PositioningMap from './components/PositioningMap'
import RadarComparison from './components/RadarComparison'
import ChangeFeed from './components/ChangeFeed'
import Gaps from './components/Gaps'
import Chatbot from './components/Chatbot'
import Methodology from './components/Methodology'
import { IconOverview, IconMap, IconRadar, IconChanges, IconGaps, IconChat, IconInfo } from './components/Icons'

const VIEWS = [
  { id: 'overview', label: 'Overview', icon: IconOverview, component: Overview,
    title: 'Overview', description: 'Every scraped campaign page, across all banks and contributors.' },
  { id: 'positioning', label: 'Positioning', icon: IconMap, component: PositioningMap,
    title: 'Positioning map', description: "Where ING sits relative to competitors, by tone, value proposition, and topics." },
  { id: 'radar', label: 'Radar', icon: IconRadar, component: RadarComparison,
    title: 'Radar comparison', description: 'Compare banks across five measurable campaign dimensions.' },
  { id: 'changes', label: 'Changes', icon: IconChanges, component: ChangeFeed,
    title: 'Change feed', description: 'What moved between scrape snapshots.' },
  { id: 'gaps', label: 'Gaps', icon: IconGaps, component: Gaps,
    title: 'Gaps', description: "Topics competitors use that ING's campaigns don't." },
  { id: 'chat', label: 'Ask', icon: IconChat, component: Chatbot,
    title: 'Ask about the data', description: null },
  { id: 'methodology', label: 'Methodology', icon: IconInfo, component: Methodology,
    title: 'Methodology', description: 'How each module works, what it measures, and how LLM-generated fields are checked.' },
]

export default function App() {
  const [activeId, setActiveId] = useState('overview')
  const active = VIEWS.find((v) => v.id === activeId)
  const ActiveComponent = active.component

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          Campaign Comparator
          <span>ING competitive intelligence</span>
        </div>
        <nav>
          {VIEWS.map((v) => (
            <button
              key={v.id}
              className={`nav-item ${v.id === activeId ? 'active' : ''}`}
              onClick={() => setActiveId(v.id)}
            >
              <v.icon />
              {v.label}
            </button>
          ))}
        </nav>
      </aside>

      <main className="main">
        <div className="main-header">
          <h1>{active.title}</h1>
          {active.description && <p>{active.description}</p>}
        </div>
        <ActiveComponent />
      </main>
    </div>
  )
}