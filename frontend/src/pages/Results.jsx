import { useQuery } from '@tanstack/react-query'
import { format } from 'date-fns'
import { matchesAPI } from '@/api/matches'
import { picksAPI } from '@/api/picks'
import useAuthStore from '@/store/authStore'
import Spinner from '@/components/ui/Spinner'
import PickDistribution from '@/components/home/PickDistribution'

const POWERUP_META = {
  hidden:      { emoji: '🕵️', label: 'Hidden',   suffix: 'from others' },
  fake:        { emoji: '🃏', label: 'Googly',   suffix: 'for others' },
  no_negative: { emoji: '🛡️', label: 'The Wall', suffix: 'applied' },
}

function TeamLogo({ team, bgColor }) {
  const initials = team?.name?.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase() || '?'
  return (
    <div className="w-12 h-12 rounded-full mx-auto flex items-center justify-center overflow-hidden shrink-0" style={{ background: bgColor }}>
      {team?.logo_url
        ? <img src={team.logo_url} alt={team.name} className="w-10 h-10 object-contain" />
        : <span className="text-xs font-bold" style={{ color: bgColor === '#E6F1FB' ? '#0C447C' : '#27500A' }}>{initials}</span>
      }
    </div>
  )
}

function ResultStateBadge({ result, myPick, won }) {
  if (result === 'CANC') return <span className="text-xs font-medium px-2.5 py-1 rounded-xl bg-gray-100 text-gray-500">CANCELLED</span>
  if (result === 'NR') return <span className="text-xs font-medium px-2.5 py-1 rounded-xl bg-gray-100 text-gray-500">NO RESULT</span>
  if (!myPick) return <span className="text-xs font-medium px-2.5 py-1 rounded-xl bg-gray-100 text-gray-500">SKIPPED</span>
  if (won) return <span className="text-xs font-bold px-2.5 py-1 rounded-xl" style={{ background: '#EAF3DE', color: '#27500A' }}>✓ WON</span>
  return <span className="text-xs font-bold px-2.5 py-1 rounded-xl" style={{ background: '#FCEBEB', color: '#791F1F' }}>✗ LOST</span>
}

export default function Results() {
  const { data: completed, isLoading } = useQuery({
    queryKey: ['matches', 'completed'],
    queryFn: () => matchesAPI.completed().then(r => r.data),
  })

  const { data: historyData } = useQuery({
    queryKey: ['picks', 'history', 'all'],
    queryFn: () => picksAPI.history({ page_size: 200 }).then(r => r.data),
  })

  const pickMap = {}
  historyData?.results?.forEach(b => { pickMap[b.match] = b })

  if (isLoading) return <Spinner />

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-gray-800">Results</h1>

      {!completed?.length ? (
        <div className="bg-white border border-gray-100 rounded-xl">
          <div className="text-center text-gray-400 py-10">No completed matches yet.</div>
        </div>
      ) : (
        completed.map(m => <ResultCard key={m.id} match={m} myPick={pickMap[m.id] ?? null} />)
      )}
    </div>
  )
}

function ResultCard({ match, myPick }) {
  const { user } = useAuthStore()
  const dt = new Date(match.datetime)
  const winner = match.result === 'team1' ? match.team1?.name : match.result === 'team2' ? match.team2?.name : null
  const won = !!(myPick && winner && myPick.selected_team_name === winner)
  const lost = !!(myPick && winner && myPick.selected_team_name !== winner)

  const t1Won = match.result === 'team1'
  const t2Won = match.result === 'team2'
  const t1MyPick = !!(myPick && myPick.selected_team_name === match.team1?.name)
  const t2MyPick = !!(myPick && myPick.selected_team_name === match.team2?.name)
  const t1Lost = t1MyPick && lost
  const t2Lost = t2MyPick && lost
  const t1WinnerNotPicked = t1Won && !t1MyPick
  const t2WinnerNotPicked = t2Won && !t2MyPick

  const powerup = myPick?.hidden ? 'hidden' : myPick?.fake ? 'fake' : myPick?.no_negative ? 'no_negative' : null

  const { data: sel } = useQuery({
    queryKey: ['match', match.id, 'selections'],
    queryFn: () => matchesAPI.selections(match.id).then(r => r.data),
    staleTime: 5 * 60 * 1000,
  })

  const isSkipped = !myPick && match.result !== 'CANC'

  let pointsDisplay = null
  if (isSkipped) {
    pointsDisplay = { text: '0 pts', skipped: true }
  } else if (myPick && winner && sel) {
    if (won) {
      const loserCount = t1MyPick ? sel.team2_count : sel.team1_count
      pointsDisplay = { text: `+${loserCount * match.match_points} pts`, positive: true, count: loserCount }
    } else if (lost) {
      const winnerCount = t1MyPick ? sel.team1_count : sel.team2_count
      pointsDisplay = { text: `-${winnerCount * match.match_points} pts`, positive: false, count: winnerCount }
    }
  }

  return (
    <div className="bg-white rounded-xl relative border border-gray-200">
      <div className="p-4">
        {/* Header */}
        <div className="flex items-start justify-between gap-2 mb-3">
          <div className="flex items-center gap-2 flex-wrap">
            <ResultStateBadge result={match.result} myPick={myPick} won={won} />
            <span className="text-xs text-gray-400">{match.description}</span>
          </div>
          <div className="flex flex-col items-end shrink-0 gap-0.5">
            <span className="text-xs font-medium px-2 py-0.5 rounded" style={{ background: '#E6F1FB', color: '#0C447C' }}>
              {match.match_points}× pts
            </span>
            {pointsDisplay && (
              <span className="text-sm font-bold px-2 py-0.5 rounded"
                style={pointsDisplay.skipped
                  ? { background: '#f3f4f6', color: '#6b7280' }
                  : pointsDisplay.positive
                    ? { background: '#E1F5EE', color: '#085041' }
                    : { background: '#FCEBEB', color: '#791F1F' }
                }>
                {pointsDisplay.text}
              </span>
            )}
          </div>
        </div>

        {/* Teams */}
        <div className="flex items-start justify-center gap-3 mb-3">
          <div className={`flex-1 flex flex-col items-center transition-opacity ${myPick && !t1MyPick && !t1Won ? 'opacity-30' : ''}`}>
            <div className="relative mb-1.5">
              {t1MyPick && !t1Lost && (
                <span className="absolute -top-1 -right-1 z-10 w-5 h-5 bg-green-500 rounded-full flex items-center justify-center text-white text-[10px] border-2 border-white">✓</span>
              )}
              {t1Lost && (
                <span className="absolute -top-1 -left-1 z-10 w-5 h-5 bg-red-500 rounded-full flex items-center justify-center text-white text-[10px] border-2 border-white">✗</span>
              )}
              {t1WinnerNotPicked && (
                <span className="absolute -top-1 -right-1 z-10 w-5 h-5 bg-amber-400 rounded-full flex items-center justify-center text-white text-[10px] border-2 border-white">★</span>
              )}
              <div className={`${t1MyPick && !t1Lost ? 'ring-2 ring-green-500 rounded-full' : t1Lost ? 'ring-2 ring-red-500 rounded-full' : t1WinnerNotPicked ? 'ring-2 ring-amber-400 rounded-full' : ''}`}>
                <TeamLogo team={match.team1} bgColor="#E6F1FB" />
              </div>
            </div>
            <span className={`text-sm font-medium text-center leading-tight ${t1Won && t1MyPick ? 'text-green-600' : t1WinnerNotPicked ? 'text-amber-600' : t1Lost ? 'text-red-500' : 'text-gray-800'}`}>
              {match.team1?.name}
            </span>
          </div>

          <div className="text-gray-400 font-medium text-sm pt-3">VS</div>

          <div className={`flex-1 flex flex-col items-center transition-opacity ${myPick && !t2MyPick && !t2Won ? 'opacity-30' : ''}`}>
            <div className="relative mb-1.5">
              {t2MyPick && !t2Lost && (
                <span className="absolute -top-1 -right-1 z-10 w-5 h-5 bg-green-500 rounded-full flex items-center justify-center text-white text-[10px] border-2 border-white">✓</span>
              )}
              {t2Lost && (
                <span className="absolute -top-1 -left-1 z-10 w-5 h-5 bg-red-500 rounded-full flex items-center justify-center text-white text-[10px] border-2 border-white">✗</span>
              )}
              {t2WinnerNotPicked && (
                <span className="absolute -top-1 -right-1 z-10 w-5 h-5 bg-amber-400 rounded-full flex items-center justify-center text-white text-[10px] border-2 border-white">★</span>
              )}
              <div className={`${t2MyPick && !t2Lost ? 'ring-2 ring-green-500 rounded-full' : t2Lost ? 'ring-2 ring-red-500 rounded-full' : t2WinnerNotPicked ? 'ring-2 ring-amber-400 rounded-full' : ''}`}>
                <TeamLogo team={match.team2} bgColor="#EAF3DE" />
              </div>
            </div>
            <span className={`text-sm font-medium text-center leading-tight ${t2Won && t2MyPick ? 'text-green-600' : t2WinnerNotPicked ? 'text-amber-600' : t2Lost ? 'text-red-500' : 'text-gray-800'}`}>
              {match.team2?.name}
            </span>
          </div>
        </div>

        {/* Match info */}
        <div className="border-t border-gray-100 pt-3 mb-3">
          <div className="text-xs text-gray-500">{format(dt, 'EEE d MMM · h:mm a')} · {match.venue}</div>
          {winner && (
            <div className="text-xs font-medium mt-1 text-gray-600">{winner} won</div>
          )}
          {match.result === 'CANC' && (
            <div className="text-xs text-gray-400 mt-1">Match cancelled</div>
          )}
          {myPick && (
            <div className={`text-xs font-medium mt-1 ${won ? 'text-green-600' : lost ? 'text-red-500' : 'text-gray-500'}`}>
              You picked {myPick.selected_team_name}
              {powerup && ` · ${POWERUP_META[powerup].emoji} ${POWERUP_META[powerup].label} ${POWERUP_META[powerup].suffix}`}
            </div>
          )}
        </div>

        {/* Pick distribution */}
        {sel && (
          <PickDistribution
            team1={sel.team1} team2={sel.team2}
            team1Count={sel.team1_count} team2Count={sel.team2_count}
            hiddenCount={sel.hidden_count ?? 0}
            isCompleted={true}
          />
        )}

        {/* Who picked what */}
        {sel && (sel.team1_selections?.length > 0 || sel.team2_selections?.length > 0) && (
          <div className="mt-3 grid grid-cols-2 gap-2">
            {[
              { teamName: sel.team1, picks: sel.team1_selections ?? [], won: t1Won },
              { teamName: sel.team2, picks: sel.team2_selections ?? [], won: t2Won },
            ].map(({ teamName, picks, won }) => (
              <div key={teamName} className="rounded-lg p-2.5"
                style={{ background: won ? '#EAF3DE' : '#f9fafb' }}>
                <p className="text-xs font-semibold mb-1.5 truncate"
                  style={{ color: won ? '#27500A' : '#6b7280' }}>
                  {teamName} {won ? '★' : ''}
                </p>
                {picks.length === 0
                  ? <p className="text-xs text-gray-400 italic">No picks</p>
                  : <div className="flex flex-wrap gap-1">
                    {picks.map(username => (
                      <span key={username}
                        className="text-xs px-1.5 py-0.5 rounded-md font-medium"
                        style={username === user?.username
                          ? { background: '#E6F1FB', color: '#0C447C', fontWeight: 700 }
                          : { background: '#e5e7eb', color: '#374151' }
                        }>
                        {username === user?.username ? `${username} (you)` : username}
                      </span>
                    ))}
                  </div>
                }
              </div>
            ))}
          </div>
        )}

        {/* Points explanation */}
        {isSkipped && (
          <p className="text-xs mt-2 font-medium text-gray-400">
            You skipped this match — 0 points
          </p>
        )}
        {!isSkipped && pointsDisplay && sel && (
          <p className="text-xs mt-2 font-medium" style={pointsDisplay.positive ? { color: '#085041' } : { color: '#791F1F' }}>
            {pointsDisplay.positive
              ? `You earned ${pointsDisplay.text} (${match.match_points} pt × ${pointsDisplay.count} opponents who picked the loser)`
              : `You lost ${Math.abs(pointsDisplay.count * match.match_points)} pts (${match.match_points} pt × ${pointsDisplay.count} opponents who picked the winner)`
            }
          </p>
        )}
      </div>
    </div>
  )
}
