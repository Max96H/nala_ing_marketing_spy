const common = { fill: 'none', stroke: 'currentColor', strokeWidth: 1.6, strokeLinecap: 'round', strokeLinejoin: 'round' }

export const IconOverview = () => (
  <svg viewBox="0 0 24 24" className="nav-icon" {...common}>
    <rect x="3.5" y="3.5" width="7" height="7" rx="1.2" />
    <rect x="13.5" y="3.5" width="7" height="7" rx="1.2" />
    <rect x="3.5" y="13.5" width="7" height="7" rx="1.2" />
    <rect x="13.5" y="13.5" width="7" height="7" rx="1.2" />
  </svg>
)

export const IconMap = () => (
  <svg viewBox="0 0 24 24" className="nav-icon" {...common}>
    <circle cx="7" cy="9" r="2" />
    <circle cx="16" cy="7" r="2" />
    <circle cx="12" cy="16" r="2" />
    <circle cx="18" cy="16" r="1.5" />
  </svg>
)

export const IconRadar = () => (
  <svg viewBox="0 0 24 24" className="nav-icon" {...common}>
    <polygon points="12,4 19,9 16.5,17 7.5,17 5,9" />
    <polygon points="12,8.5 15,10.5 14,14 10,14 9,10.5" />
  </svg>
)

export const IconChanges = () => (
  <svg viewBox="0 0 24 24" className="nav-icon" {...common}>
    <path d="M4 12a8 8 0 0 1 14-5.2M20 12a8 8 0 0 1-14 5.2" />
    <path d="M18 4v3.5H14.5M6 20v-3.5H9.5" />
  </svg>
)

export const IconGaps = () => (
  <svg viewBox="0 0 24 24" className="nav-icon" {...common}>
    <circle cx="10.5" cy="10.5" r="6.5" />
    <path d="M19 19l-4-4" />
  </svg>
)

export const IconChat = () => (
  <svg viewBox="0 0 24 24" className="nav-icon" {...common}>
    <path d="M4 5.5h16v10H9.5L5 19v-3.5H4z" />
  </svg>
)

export const IconInfo = () => (
  <svg viewBox="0 0 24 24" className="nav-icon" {...common}>
    <circle cx="12" cy="12" r="8" />
    <line x1="12" y1="11" x2="12" y2="16" />
    <circle cx="12" cy="8" r="0.5" fill="currentColor" stroke="none" />
  </svg>
)

export const IconCompare = () => (
  <svg viewBox="0 0 24 24" className="nav-icon" {...common}>
    <rect x="3.5" y="4" width="7" height="16" rx="1.2" />
    <rect x="13.5" y="4" width="7" height="16" rx="1.2" />
  </svg>
)