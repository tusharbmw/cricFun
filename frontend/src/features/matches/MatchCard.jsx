import { Link } from 'react-router-dom'
import { format } from 'date-fns'
import { matchStatusBadge } from '@/components/ui/Badge'

const POWERUP_LABELS = {
  hidden:      '🕵️ Hidden',
  fake:        '🃏 Googly',
  no_negative: '🛡️ The Wall',
}

function getPowerupLabel(pick) {
  if (!pick) return null
  if (pick.hidden)      return POWERUP_LABELS.hidden
  if (pick.fake)        return POWERUP_LABELS.fake
  if (pick.no_negative) return POWERUP_LABELS.no_negative
  return null
}

// myPick: { teamName, hidden, fake, no_negative } or null
// pickWindowDays: from stats API — matches beyond this many days are not open for picks
export default function MatchCard({ match, myPick, pickWindowDays = 5 }) {
  const dt = new Date(match.datetime)
  // eslint-disable-next-line react-hooks/purity
  const now = Date.now()
  const isLive = match.result === 'IP' || match.result === 'TOSS'
  const mySelection = myPick?.teamName ?? null
  const powerupLabel = getPowerupLabel(myPick)
  const canPick = match.result === 'TBD' && dt.getTime() - now <= pickWindowDays * 24 * 60 * 60 * 1000

  return (
    <div className={`bg-white border border-gray-100 rounded-xl shadow-sm transition-shadow hover:shadow-md ${isLive ? 'border-l-4 border-error' : ''}`}>
      <div className="card-body p-4">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              {matchStatusBadge(match.result)}
              {match.match_points > 1 && (
                <span className="badge badge-sm badge-secondary font-medium">
                  {match.match_points}× points
                </span>
              )}
            </div>
            <div className="font-semibold text-gray-800 truncate">
              {match.team1?.name} <span className="text-gray-400 font-normal">vs</span> {match.team2?.name}
            </div>
            <div className="text-xs text-gray-500 mt-0.5">{match.description}</div>
            <div className="text-xs text-gray-400 mt-0.5">
              {format(dt, 'EEE d MMM · h:mm a')} · {match.venue}
            </div>
          </div>

          {mySelection && (
            <div className="flex flex-col items-end gap-1 shrink-0">
              <span className="text-xs text-gray-500">My pick</span>
              <span className="text-sm font-medium text-primary">{mySelection}</span>
              {powerupLabel && (
                <span className="badge badge-sm badge-secondary">{powerupLabel}</span>
              )}
              {match.result_display && match.result !== 'TBD' && match.result !== 'IP' && match.result !== 'TOSS' && (
                <span className={`text-xs font-semibold ${mySelection === match.result_display ? 'text-success' : 'text-error'}`}>
                  {mySelection === match.result_display ? '✓ Won' : '✗ Lost'}
                </span>
              )}
            </div>
          )}
        </div>

        <div className="mt-3 flex items-center justify-between">
          <Link to={`/matches/${match.id}`} className="link link-primary text-xs">
            View details →
          </Link>
          {match.result === 'TBD' && !mySelection && (
            canPick
              ? <Link to="/schedule" className="btn btn-primary btn-xs">Place pick</Link>
              : <span className="text-xs text-gray-400 italic">Opens in {Math.ceil((dt.getTime() - now) / 86400000 - pickWindowDays)} d</span>
          )}
        </div>
      </div>
    </div>
  )
}
