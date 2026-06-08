import { useParams } from 'react-router-dom'
import { useState, useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { format } from 'date-fns'
import { matchesAPI } from '@/api/matches'
import Spinner from '@/components/ui/Spinner'
import { matchStatusBadge } from '@/components/ui/Badge'

const POWERUP_META = {
  cricket: {
    hidden:      { emoji: '🕵️', label: 'Hidden' },
    fake:        { emoji: '🃏', label: 'Googly' },
    no_negative: { emoji: '🛡️', label: 'The Wall' },
  },
  soccer: {
    hidden:      { emoji: '🕵️', label: 'Hidden' },
    fake:        { emoji: '🪄', label: 'Dummy' },
    no_negative: { emoji: '🧤', label: 'Clean Sheet' },
  },
}

function FormBadge({ result, opponent, isOpen, onToggle, isRecent }) {
  const styles = {
    W: 'bg-green-100 text-green-700',
    L: 'bg-red-100 text-red-700',
    N: 'bg-yellow-100 text-yellow-700',
  }
  const recentBorder = {
    W: 'ring-1 ring-green-400',
    L: 'ring-1 ring-red-400',
    N: 'ring-1 ring-yellow-400',
  }
  return (
    <span className="relative inline-block">
      <button
        type="button"
        onClick={onToggle}
        className={`text-xs font-bold px-2 py-0.5 rounded cursor-pointer ${styles[result] ?? 'bg-gray-100 text-gray-400'} ${isRecent ? (recentBorder[result] ?? 'ring-1 ring-gray-400') : ''}`}
      >
        {result}
      </button>
      {isOpen && opponent && (
        <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 whitespace-nowrap rounded bg-gray-800 text-white text-xs px-2 py-1 z-10 pointer-events-none">
          {opponent}
        </span>
      )}
    </span>
  )
}

function FormRow({ entries }) {
  const [openIdx, setOpenIdx] = useState(null)
  const ref = useRef(null)

  useEffect(() => {
    function handler(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpenIdx(null)
    }
    document.addEventListener('mousedown', handler)
    document.addEventListener('touchstart', handler)
    return () => {
      document.removeEventListener('mousedown', handler)
      document.removeEventListener('touchstart', handler)
    }
  }, [])

  return (
    <div ref={ref} className="flex gap-1 flex-wrap">
      {entries?.length > 0
        ? entries.map((e, i) => (
            <FormBadge
              key={i}
              result={e.result}
              opponent={e.opponent}
              isOpen={openIdx === i}
              onToggle={() => setOpenIdx(openIdx === i ? null : i)}
              isRecent={i === 0}
            />
          ))
        : <span className="text-xs text-gray-400 italic">No matches yet this season</span>
      }
    </div>
  )
}

export default function MatchDetail() {
  const { id } = useParams()

  const { data: match, isLoading } = useQuery({
    queryKey: ['match', id],
    queryFn: () => matchesAPI.get(id).then(r => r.data),
    refetchInterval: (data) => data?.result === 'IP' ? 30000 : false,
  })

  const isSoccer = match?.tournament?.sport === 'soccer'
  const PM = POWERUP_META[isSoccer ? 'soccer' : 'cricket']

  const { data: sel } = useQuery({
    queryKey: ['match', id, 'selections'],
    queryFn: () => matchesAPI.selections(id).then(r => r.data),
    enabled: !!match,
    refetchInterval: match?.result === 'IP' ? 30000 : false,
  })

  const { data: form } = useQuery({
    queryKey: ['match', id, 'team_form'],
    queryFn: () => matchesAPI.teamForm(id).then(r => r.data),
    enabled: !!match && !isSoccer,
    staleTime: 10 * 60 * 1000,
  })

  if (isLoading) return <Spinner />
  if (!match) return <p className="text-gray-500 text-center py-10">Match not found.</p>

  const dt = new Date(match.datetime)
  const hasScore = match.home_score != null && match.away_score != null
  const drawPicks = sel?.draw_selections ?? []
  const showDrawColumn = isSoccer && (match.allows_draw || drawPicks.length > 0)

  return (
    <div className="space-y-4">
      <div className="bg-white border border-gray-100 rounded-xl shadow-sm">
        <div className="p-4">
          <div className="flex items-start justify-between gap-2 flex-wrap">
            <div>
              {matchStatusBadge(match.result)}
              {isSoccer && hasScore ? (
                <div className="flex items-center gap-3 mt-2">
                  <span className="text-lg font-bold text-gray-800">{match.team1?.name}</span>
                  <span className="text-2xl font-black text-gray-700 tabular-nums">
                    {match.home_score} — {match.away_score}
                  </span>
                  <span className="text-lg font-bold text-gray-800">{match.team2?.name}</span>
                </div>
              ) : (
                <h1 className="text-xl font-bold text-gray-800 mt-2">
                  {match.team1?.name} vs {match.team2?.name}
                </h1>
              )}
              <p className="text-sm text-gray-500 mt-0.5">{match.description}</p>
              {isSoccer && hasScore && match.duration && match.duration !== 'REGULAR' && (
                <p className="text-xs text-gray-400">
                  {match.duration === 'EXTRA_TIME' ? 'After Extra Time' : 'Penalties'}
                </p>
              )}
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
            <div className={`grid gap-4 ${showDrawColumn ? 'grid-cols-3' : 'grid-cols-2'}`}>
              {[
                { teamName: sel.team1, picks: sel.team1_selections ?? [], auto: sel.team1_auto ?? [], isDrawCol: false },
                ...(showDrawColumn ? [{ teamName: '⚖ Draw', picks: drawPicks, auto: [], isDrawCol: true }] : []),
                { teamName: sel.team2, picks: sel.team2_selections ?? [], auto: sel.team2_auto ?? [], isDrawCol: false },
              ].map(({ teamName, picks, auto, isDrawCol }) => (
                <div key={teamName}>
                  <div className={`text-sm font-medium mb-2 ${isDrawCol ? 'text-amber-700' : 'text-gray-800'}`}>
                    {teamName} <span className="text-gray-400 text-xs">({picks.length + auto.length})</span>
                  </div>
                  {picks.length === 0 && auto.length === 0
                    ? <p className="text-xs text-gray-300">No picks yet</p>
                    : <>
                        {picks.map(u => {
                          const pp = sel.powerups?.[u]
                          return (
                            <div key={u} className="text-sm text-gray-600 py-0.5">
                              {u}{pp && <span title={PM[pp]?.label}> {PM[pp]?.emoji}</span>}
                            </div>
                          )
                        })}
                        {auto.map(u => (
                          <div key={u} className="text-sm text-gray-400 py-0.5" title="Auto-assigned — did not pick">
                            💀 {u}
                          </div>
                        ))}
                      </>
                  }
                </div>
              ))}
            </div>
            {Object.keys(sel.powerups ?? {}).length > 0 && (
              <div className="mt-3 pt-3 border-t border-gray-100 flex flex-wrap gap-x-4 gap-y-1">
                {Object.values(PM).map(({ emoji, label }) => (
                  <span key={label} className="text-xs text-gray-400">{emoji} {label}</span>
                ))}
              </div>
            )}
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
                <FormRow entries={entries} />
              </div>
            ))}

            <p className="text-xs text-gray-400">Tap badge to see opponent · W = Won · L = Lost · N = No Result</p>

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
