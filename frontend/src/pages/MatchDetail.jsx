import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { format } from 'date-fns'
import { matchesAPI } from '@/api/matches'
import Spinner from '@/components/ui/Spinner'
import { matchStatusBadge } from '@/components/ui/Badge'

const POWERUP_META = {
  hidden:      { emoji: '🕵️', label: 'Hidden' },
  fake:        { emoji: '🃏', label: 'Googly' },
  no_negative: { emoji: '🛡️', label: 'The Wall' },
}

function FormBadge({ result, opponent }) {
  const styles = {
    W: 'bg-green-100 text-green-700',
    L: 'bg-red-100 text-red-700',
    N: 'bg-yellow-100 text-yellow-700',
  }
  return (
    <span
      title={opponent}
      className={`text-xs font-bold px-2 py-0.5 rounded ${styles[result] ?? 'bg-gray-100 text-gray-400'}`}
    >
      {result}
    </span>
  )
}

export default function MatchDetail() {
  const { id } = useParams()

  const { data: match, isLoading } = useQuery({
    queryKey: ['match', id],
    queryFn: () => matchesAPI.get(id).then(r => r.data),
    refetchInterval: (data) => data?.result === 'IP' ? 30000 : false,
  })

  const { data: sel } = useQuery({
    queryKey: ['match', id, 'selections'],
    queryFn: () => matchesAPI.selections(id).then(r => r.data),
    enabled: !!match,
    refetchInterval: match?.result === 'IP' ? 30000 : false,
  })

  const { data: form } = useQuery({
    queryKey: ['match', id, 'team_form'],
    queryFn: () => matchesAPI.teamForm(id).then(r => r.data),
    enabled: !!match,
    staleTime: 10 * 60 * 1000,
  })

  if (isLoading) return <Spinner />
  if (!match) return <p className="text-gray-500 text-center py-10">Match not found.</p>

  const dt = new Date(match.datetime)

  return (
    <div className="space-y-4">
      <div className="bg-white border border-gray-100 rounded-xl shadow-sm">
        <div className="p-4">
          <div className="flex items-start justify-between gap-2 flex-wrap">
            <div>
              {matchStatusBadge(match.result)}
              <h1 className="text-xl font-bold text-gray-800 mt-2">
                {match.team1?.name} vs {match.team2?.name}
              </h1>
              <p className="text-sm text-gray-500">{match.description}</p>
            </div>
            {match.match_points > 1 && (
              <span className="badge badge-secondary font-semibold">
                {match.match_points}× points
              </span>
            )}
          </div>
          <div className="mt-3 grid grid-cols-2 gap-2 text-sm text-gray-600">
            <div><span className="text-gray-400">Date:</span> {format(dt, 'EEE d MMM, h:mm a')}</div>
            <div><span className="text-gray-400">Venue:</span> {match.venue}</div>
            <div><span className="text-gray-400">Result:</span> {match.result_display}</div>
            <div><span className="text-gray-400">Points:</span> {match.match_points}× multiplier</div>
          </div>
        </div>
      </div>

      {sel && (
        <div className="bg-white border border-gray-100 rounded-xl shadow-sm">
          <div className="p-4">
            <h2 className="font-semibold text-gray-600 mb-3">Who picked who</h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-sm font-medium text-gray-800 mb-2">
                  {sel.team1} <span className="text-gray-400 text-xs">({sel.team1_selections?.length})</span>
                </div>
                {sel.team1_selections?.length === 0
                  ? <p className="text-xs text-gray-300">No picks yet</p>
                  : sel.team1_selections?.map(u => {
                      const pp = sel.powerups?.[u]
                      return (
                        <div key={u} className="text-sm text-gray-600 py-0.5">
                          {u}{pp && <span title={POWERUP_META[pp].label}> {POWERUP_META[pp].emoji}</span>}
                        </div>
                      )
                    })
                }
              </div>
              <div>
                <div className="text-sm font-medium text-gray-800 mb-2">
                  {sel.team2} <span className="text-gray-400 text-xs">({sel.team2_selections?.length})</span>
                </div>
                {sel.team2_selections?.length === 0
                  ? <p className="text-xs text-gray-300">No picks yet</p>
                  : sel.team2_selections?.map(u => {
                      const pp = sel.powerups?.[u]
                      return (
                        <div key={u} className="text-sm text-gray-600 py-0.5">
                          {u}{pp && <span title={POWERUP_META[pp].label}> {POWERUP_META[pp].emoji}</span>}
                        </div>
                      )
                    })
                }
              </div>
            </div>
          </div>
        </div>
      )}

      {form && (
        <div className="bg-white border border-gray-100 rounded-xl shadow-sm">
          <div className="p-4 space-y-4">
            <h2 className="font-semibold text-gray-600">Team Stats</h2>

            {/* Season stats + form per team */}
            {[
              { name: form.team1, entries: form.team1_form, season: form.team1_season },
              { name: form.team2, entries: form.team2_form, season: form.team2_season },
            ].map(({ name, entries, season }) => (
              <div key={name}>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-sm font-medium text-gray-800">{name}</span>
                  {season && (
                    <span className="text-xs text-gray-400">
                      {season.played} played · <span className="text-green-600 font-medium">{season.won}W</span> · <span className="text-red-500 font-medium">{season.lost}L</span>
                    </span>
                  )}
                </div>
                <div className="flex gap-1">
                  {entries?.length > 0
                    ? entries.map((e, i) => <FormBadge key={i} result={e.result} opponent={e.opponent} />)
                    : <span className="text-xs text-gray-400 italic">No matches yet this season</span>
                  }
                </div>
              </div>
            ))}

            <p className="text-xs text-gray-400">Hover badge to see opponent · W = Won · L = Lost · N = No Result</p>

            {/* Head-to-head */}
            {form.h2h?.length > 0 && (
              <div className="border-t border-gray-100 pt-3">
                <p className="text-sm font-semibold text-gray-600 mb-2">Head-to-Head</p>
                <div className="space-y-1.5">
                  {form.h2h.map((m, i) => (
                    <div key={i} className="flex items-center justify-between text-xs">
                      <span className="text-gray-400">{m.description}</span>
                      <span className={`font-medium ${m.winner ? 'text-gray-700' : 'text-gray-400'}`}>
                        {m.winner ? `${m.winner} won` : 'No result'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
