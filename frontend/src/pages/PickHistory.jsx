import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { format } from 'date-fns'
import { picksAPI } from '@/api/picks'
import Spinner from '@/components/ui/Spinner'

function appliedPowerup(pick) {
  if (pick.hidden)      return '🕵️ Hidden'
  if (pick.fake)        return '🃏 Googly'
  if (pick.no_negative) return '🛡️ The Wall'
  return null
}

export default function PickHistory() {
  const [page, setPage] = useState(1)

  const { data, isLoading } = useQuery({
    queryKey: ['picks', 'history', page],
    queryFn: () => picksAPI.history({ page }).then(r => r.data),
    keepPreviousData: true,
  })

  const picks = data?.results ?? []
  const totalPages = data?.count ? Math.ceil(data.count / 20) : 1

  if (isLoading && !data) return <Spinner />

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-gray-800">My Picks</h1>

      {!picks.length ? (
        <div className="bg-white border border-gray-100 rounded-xl">
          <div className="text-center text-gray-400 py-10">No picks yet.</div>
        </div>
      ) : (
        <div className="space-y-3">
          {picks.map(pick => <PickRow key={pick.id} pick={pick} />)}
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-3 pt-2">
          <button
            onClick={() => setPage(p => p - 1)}
            disabled={page <= 1}
            className="btn btn-sm btn-ghost"
          >
            ← Prev
          </button>
          <span className="text-sm text-gray-500">{page} / {totalPages}</span>
          <button
            onClick={() => setPage(p => p + 1)}
            disabled={page >= totalPages}
            className="btn btn-sm btn-ghost"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  )
}

function PickRow({ pick }) {
  const dt = pick.match_datetime ? new Date(pick.match_datetime) : null
  const result = pick.match_result
  const isCompleted = result === 'team1' || result === 'team2' || result === 'NR'
  const won = isCompleted && pick.selected_team_name === pick.match_result_display
  const powerup = appliedPowerup(pick)

  return (
    <div className="bg-white border border-gray-100 rounded-xl shadow-sm">
      <div className="p-4">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <div className="font-medium text-gray-800 truncate">{pick.match_name}</div>
            {dt && (
              <div className="text-xs text-gray-400 mt-0.5">{format(dt, 'EEE d MMM, h:mm a')}</div>
            )}
            <div className="flex items-center gap-2 mt-1 flex-wrap">
              <span className="text-sm text-primary font-medium">{pick.selected_team_name}</span>
              {powerup && (
                <span className="badge badge-sm badge-secondary">{powerup}</span>
              )}
            </div>
          </div>

          <div className="shrink-0 text-right">
            {isCompleted ? (
              <>
                <div className={`text-sm font-bold ${won ? 'text-success' : 'text-error'}`}>
                  {won ? '✓ Won' : '✗ Lost'}
                </div>
                {pick.match_result_display && (
                  <div className="text-xs text-gray-400 mt-0.5">{pick.match_result_display}</div>
                )}
              </>
            ) : result === 'IP' || result === 'TOSS' ? (
              <span className="badge badge-sm badge-error">Live</span>
            ) : result === 'CANC' ? (
              <span className="badge badge-sm badge-ghost">Cancelled</span>
            ) : (
              <span className="badge badge-sm badge-info">Upcoming</span>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
