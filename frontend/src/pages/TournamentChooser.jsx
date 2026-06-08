import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import useTournamentStore from '@/store/tournamentStore'
import Spinner from '@/components/ui/Spinner'

const SPORT_EMOJI = { cricket: '🏏', soccer: '⚽' }

export default function TournamentChooser() {
  const { tournaments, isLoading, setTournament } = useTournamentStore()
  const navigate = useNavigate()

  // Auto-select and skip chooser when only one tournament is available
  useEffect(() => {
    if (!isLoading && tournaments.length === 1) {
      setTournament(tournaments[0])
      navigate('/', { replace: true })
    }
  }, [isLoading, tournaments, setTournament, navigate])

  function handleSelect(t) {
    setTournament(t)
    navigate('/', { replace: true })
  }

  if (isLoading || tournaments.length === 1) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Spinner />
      </div>
    )
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-6 p-6 bg-[#f8f9fa]">
      <div className="text-center">
        <h1 className="text-2xl font-bold text-gray-900">Choose your arena</h1>
        <p className="text-sm text-gray-500 mt-1">Select a tournament to continue</p>
      </div>
      <div className="flex flex-col gap-3 w-full max-w-sm">
        {tournaments.map(t => (
          <button
            key={t.id}
            onClick={() => handleSelect(t)}
            className="w-full text-left border border-gray-200 rounded-2xl p-5 bg-white hover:border-gray-400 hover:shadow-sm transition-all"
          >
            <div className="flex items-center gap-3">
              <span className="text-2xl">{SPORT_EMOJI[t.sport] ?? '🏆'}</span>
              <div>
                <div className="font-semibold text-gray-900">{t.name}</div>
                <div className="text-sm text-gray-500">{t.state ?? t.season}</div>
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}
