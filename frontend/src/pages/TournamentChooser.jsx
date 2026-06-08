import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import useTournamentStore from '@/store/tournamentStore'
import Spinner from '@/components/ui/Spinner'

const SPORT = {
  cricket: {
    emoji:  '🏏',
    label:  'Cricket',
    accent: '#C49A36',
    bg:     '#FBF5E6',
    border: '#E8D08A',
    ink:    '#7A5A1A',
  },
  soccer: {
    emoji:  '⚽',
    label:  'Soccer',
    accent: '#2D8B6F',
    bg:     '#E1F5EE',
    border: '#5DCAA5',
    ink:    '#085041',
  },
}

function TournamentCard({ tournament, onSelect }) {
  const sp = SPORT[tournament.sport] ?? { emoji: '🏆', bg: '#f5f5f5', border: '#ddd', ink: '#333', accent: '#666' }
  return (
    <button
      onClick={() => onSelect(tournament)}
      className="w-full text-left rounded-2xl p-5 transition-all hover:scale-[1.01] active:scale-[0.99]"
      style={{
        background:   sp.bg,
        border:       `1.5px solid ${sp.border}`,
        boxShadow:    '0 1px 2px rgba(0,0,0,0.04), 0 4px 16px -8px rgba(0,0,0,0.12)',
      }}
    >
      <div className="flex items-center gap-4">
        <span
          className="w-12 h-12 rounded-xl flex items-center justify-center text-2xl shrink-0"
          style={{ background: 'rgba(255,255,255,0.6)', border: `1px solid ${sp.border}` }}
        >
          {sp.emoji}
        </span>
        <div className="flex-1 min-w-0">
          <div className="font-semibold text-gray-900 leading-tight">{tournament.name}</div>
          <div className="text-sm mt-0.5" style={{ color: sp.ink }}>{tournament.season}</div>
        </div>
        {tournament.state && (
          <span
            className="text-xs font-medium px-2.5 py-1 rounded-full shrink-0"
            style={{ background: 'rgba(255,255,255,0.7)', color: sp.ink, border: `1px solid ${sp.border}` }}
          >
            {tournament.state}
          </span>
        )}
      </div>
    </button>
  )
}

/**
 * TournamentChooser
 *
 * canDismiss=false (default) — full-page mandatory selection (first visit / /choose route)
 * canDismiss=true            — overlay mode triggered from the header switcher
 */
export default function TournamentChooser({ canDismiss = false }) {
  const { tournaments, isLoading, init, setTournament, closeChooser } = useTournamentStore()
  const navigate = useNavigate()

  // Ensure tournaments are loaded — handles timing edge cases where AppRoutes
  // init hasn't fired yet, or a previous API failure left tournaments empty.
  useEffect(() => {
    if (tournaments.length === 0) init()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-select and bypass chooser when only one tournament is available
  useEffect(() => {
    if (!isLoading && tournaments.length === 1 && !canDismiss) {
      setTournament(tournaments[0])
      navigate('/', { replace: true })
    }
  }, [isLoading, tournaments, canDismiss, setTournament, navigate])

  function handleSelect(t) {
    setTournament(t)
    if (!canDismiss) navigate('/', { replace: true })
  }

  if (isLoading || (!canDismiss && tournaments.length === 1)) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: '#F6F3EC' }}>
        <Spinner />
      </div>
    )
  }

  const inner = (
    <div className="flex flex-col items-center justify-center min-h-full gap-8 px-6 py-12">
      {/* Wordmark */}
      <div className="flex flex-col items-center gap-3">
        <div
          className="w-14 h-14 rounded-2xl flex items-center justify-center shrink-0"
          style={{ background: '#181510', boxShadow: '0 0 0 3px #C49A36' }}
        >
          <img src="/logo.PNG" alt="TushFun" className="w-10 h-10 object-contain rounded-xl" />
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-gray-900 tracking-tight">TushFun</div>
          <div className="text-sm text-gray-400 mt-0.5">Two arenas · One rivalry</div>
        </div>
      </div>

      {/* Empty state */}
      {tournaments.length === 0 && (
        <div className="w-full max-w-sm flex flex-col items-center gap-4 text-center">
          <div className="text-4xl">🏟️</div>
          <div>
            <p className="font-semibold text-gray-700">No arenas available</p>
            <p className="text-sm text-gray-400 mt-1">Check back soon or contact the admin.</p>
          </div>
          <button
            onClick={init}
            className="text-sm font-medium text-amber-700 hover:text-amber-900 underline underline-offset-2 transition-colors"
          >
            Try again
          </button>
        </div>
      )}

      {/* Cards */}
      {tournaments.length > 0 && (
      <div className="w-full max-w-sm flex flex-col gap-3">
        <p className="text-xs font-medium text-gray-400 uppercase tracking-wider text-center mb-1">
          Choose your arena
        </p>
        {tournaments.map(t => (
          <TournamentCard key={t.id} tournament={t} onSelect={handleSelect} />
        ))}
      </div>
      )}

      {/* Dismiss button (overlay mode only) */}
      {canDismiss && (
        <button
          onClick={closeChooser}
          className="text-sm text-gray-400 hover:text-gray-600 transition-colors mt-2"
        >
          Keep current arena
        </button>
      )}
    </div>
  )

  // Overlay mode: full-screen fixed layer over the app
  if (canDismiss) {
    return (
      <div className="fixed inset-0 z-50 overflow-y-auto" style={{ background: '#F6F3EC' }}>
        <button
          onClick={closeChooser}
          className="absolute top-4 right-4 w-9 h-9 rounded-full bg-white/80 border border-gray-200 flex items-center justify-center text-gray-500 hover:text-gray-800 transition-colors"
        >
          ✕
        </button>
        {inner}
      </div>
    )
  }

  // Full-page mode: first visit
  return (
    <div className="min-h-screen" style={{ background: '#F6F3EC' }}>
      {inner}
    </div>
  )
}
