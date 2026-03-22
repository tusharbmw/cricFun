import { Link } from 'react-router-dom'

export default function AlertBanner({ missingPicks, urgentMissing = 0 }) {
  if (!missingPicks || missingPicks === 0) return null

  const isUrgent = urgentMissing > 0

  // STATE 1: urgent — amber warning banner
  if (isUrgent) {
    return (
      <div className="rounded-xl p-3.5 flex items-center justify-between gap-3"
        style={{ background: '#FAEEDA', border: '1px solid #f59e0b' }}>
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <span className="text-lg shrink-0">⚠️</span>
          <div className="min-w-0">
            <p className="text-sm font-medium" style={{ color: '#633806' }}>
              {missingPicks} match{missingPicks !== 1 ? 'es' : ''} available for picks
            </p>
            <p className="text-xs mt-0.5" style={{ color: '#854d0e' }}>
              {urgentMissing} closing soon (next 24 hrs)
            </p>
          </div>
        </div>
        <Link to="/schedule" className="text-sm font-medium shrink-0" style={{ color: '#854d0e' }}>
          View →
        </Link>
      </div>
    )
  }

  // STATE 2: not urgent — blue info banner
  return (
    <div className="rounded-xl p-3.5 flex items-center justify-between gap-3"
      style={{ background: '#E6F1FB', border: '1px solid #93c5fd' }}>
      <div className="flex items-center gap-3 flex-1 min-w-0">
        <span className="text-lg shrink-0">ℹ️</span>
        <div className="min-w-0">
          <p className="text-sm font-medium" style={{ color: '#1e40af' }}>
            {missingPicks} match{missingPicks !== 1 ? 'es' : ''} available for picks
          </p>
          <p className="text-xs mt-0.5" style={{ color: '#1d4ed8' }}>
            All matches lock &gt;24 hrs away
          </p>
        </div>
      </div>
      <Link to="/schedule" className="text-sm font-medium shrink-0" style={{ color: '#1e40af' }}>
        View →
      </Link>
    </div>
  )
}
