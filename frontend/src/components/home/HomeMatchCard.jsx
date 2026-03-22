import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { format } from 'date-fns'
import { matchesAPI } from '@/api/matches'
import { picksAPI } from '@/api/picks'
import PickDistribution from './PickDistribution'

const POWERUP_META = {
  hidden:      { emoji: '🕵️', label: 'Hidden',  key: 'hidden_count',      suffix: 'from others' },
  fake:        { emoji: '🃏', label: 'Googly',  key: 'fake_count',        suffix: 'for others' },
  no_negative: { emoji: '🛡️', label: 'The Wall', key: 'no_negative_count', suffix: 'applied' },
}

// PowerPlay badge pinned to top-center of a picked card
function BoosterBadge({ powerup, onRemove }) {
  if (!powerup) return null
  const { emoji, label } = POWERUP_META[powerup]
  return (
    <div className="absolute -top-3 left-1/2 -translate-x-1/2 z-10 flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded-full shadow border"
      style={{ background: '#EEEDFE', color: '#3C3489', borderColor: '#AFA9EC' }}>
      <span>{emoji}</span>
      <span>{label}</span>
      <button onClick={onRemove} className="ml-1 font-bold hover:opacity-70">×</button>
    </div>
  )
}

// Circular team logo with fallback initials
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

export default function HomeMatchCard({ match, pick, stats, isDragTarget, onDragOver, onDragLeave, onDrop, isApplying, selectedBooster, onApplySelectedBooster }) {
  const qc = useQueryClient()
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [showChangePick, setShowChangePick] = useState(false)

  // eslint-disable-next-line react-hooks/purity
  const now = Date.now()
  const dt = new Date(match.datetime)
  const pickWindowMs = (stats?.pick_window_days ?? 5) * 24 * 60 * 60 * 1000

  const isCompleted = ['team1', 'team2', 'NR'].includes(match.result)
  const isLive = ['IP', 'TOSS', 'DLD'].includes(match.result)
  const isUpcoming = match.result === 'TBD'
  const isBeyondWindow = isUpcoming && dt.getTime() - now > pickWindowMs
  const isLocked = !isUpcoming || isBeyondWindow || isLive
  const isUrgent = isUpcoming && !isBeyondWindow && dt.getTime() - now < 24 * 3600 * 1000

  const hasPick = !!pick
  const powerup = pick?.hidden ? 'hidden' : pick?.fake ? 'fake' : pick?.no_negative ? 'no_negative' : null
  const powersDisabled = stats?.powerups_disabled ?? true

  // Support both active picks (pick.selection = team ID) and history picks (pick.selected_team_name)
  const myPickId = pick?.selection ?? null
  const myPickName = pick?.selected_team_name ?? null

  const winner = match.result === 'team1' ? match.team1?.id : match.result === 'team2' ? match.team2?.id : null
  const winnerName = match.result === 'team1' ? match.team1?.name : match.result === 'team2' ? match.team2?.name : null
  const userWon = hasPick && winner !== null && (myPickId ? myPickId === winner : myPickName === winnerName)

  const { data: sel } = useQuery({
    queryKey: ['match', match.id, 'selections'],
    queryFn: () => matchesAPI.selections(match.id).then(r => r.data),
    staleTime: isCompleted ? 5 * 60 * 1000 : 60 * 1000,
  })

  const isSkipped = isCompleted && !hasPick

  let pointsDisplay = null
  if (isSkipped) {
    pointsDisplay = { text: '0 pts', skipped: true }
  } else if (isCompleted && hasPick && sel && winner) {
    if (userWon) {
      const loserCount = match.result === 'team1' ? sel.team2_count : sel.team1_count
      pointsDisplay = { text: `+${loserCount * match.match_points} pts`, positive: true }
    } else {
      const winnerCount = match.result === 'team1' ? sel.team1_count : sel.team2_count
      pointsDisplay = { text: `-${winnerCount * match.match_points} pts`, positive: false }
    }
  }

  async function handlePick(teamId) {
    if (saving) return
    setSaving(true); setError('')
    try {
      if (!hasPick) {
        await picksAPI.place({ match: match.id, selection: teamId })
      } else {
        await picksAPI.update(pick.id, { selection: teamId })
      }
      qc.invalidateQueries({ queryKey: ['picks', 'active'] })
      qc.invalidateQueries({ queryKey: ['picks', 'stats'] })
      setShowChangePick(false)
    } catch (err) {
      setError(err.response?.data?.non_field_errors?.[0] ?? 'Failed to save')
    } finally { setSaving(false) }
  }

  async function handleRemovePick() {
    if (!hasPick || powerup || saving) return
    setSaving(true); setError('')
    try {
      await picksAPI.remove(pick.id)
      qc.invalidateQueries({ queryKey: ['picks', 'active'] })
      qc.invalidateQueries({ queryKey: ['picks', 'stats'] })
      setShowChangePick(false)
    } catch (err) {
      setError(err.response?.data?.error ?? 'Failed to remove')
    } finally { setSaving(false) }
  }

  async function applyPowerup(type) {
    if (!hasPick || saving) return
    setSaving(true); setError('')
    try {
      await picksAPI.applyPowerup(pick.id, type)
      qc.invalidateQueries({ queryKey: ['picks', 'active'] })
      qc.invalidateQueries({ queryKey: ['picks', 'stats'] })
    } catch (err) {
      setError(err.response?.data?.error ?? 'Failed to apply')
    } finally { setSaving(false) }
  }

  // Card border
  const cardBorder = isUrgent ? 'border-2 border-amber-400' : 'border border-gray-200'
  const showPickButtons = isUpcoming && !isLocked && (!hasPick || showChangePick)

  // Team display state
  const t1Picked = hasPick && !showChangePick && (myPickId ? myPickId === match.team1?.id : myPickName === match.team1?.name)
  const t2Picked = hasPick && !showChangePick && (myPickId ? myPickId === match.team2?.id : myPickName === match.team2?.name)
  const t1Won = isCompleted && match.result === 'team1'
  const t2Won = isCompleted && match.result === 'team2'
  const t1Lost = isCompleted && t1Picked && !userWon
  const t2Lost = isCompleted && t2Picked && !userWon
  // Winner that I didn't pick — show differently from "my pick won"
  const t1WinnerNotPicked = t1Won && !t1Picked
  const t2WinnerNotPicked = t2Won && !t2Picked

  return (
    <div
      className={`bg-white rounded-xl relative transition-all ${cardBorder} ${isDragTarget ? 'ring-2 ring-blue-400 scale-[1.01]' : ''}`}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
    >
      {powerup && !isCompleted && (
        <BoosterBadge powerup={powerup} onRemove={() => applyPowerup(powerup)} />
      )}

      <div className="p-4 pt-5">
        {/* Header row: state badge + description + points */}
        <div className="flex items-start justify-between gap-2 mb-3">
          <div className="flex items-center gap-2 flex-wrap">
            <StateBadge
              isCompleted={isCompleted} isLive={isLive} isUrgent={isUrgent}
              hasPick={hasPick} userWon={userWon}
            />
            <span className="text-xs text-gray-400">{match.description}</span>
            {isApplying && <span className="loading loading-spinner loading-xs text-primary" />}
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

        {/* Teams row */}
        <div className="flex items-start justify-center gap-3 mb-3">
          {/* Team 1 */}
          <div className={`flex-1 flex flex-col items-center transition-opacity ${hasPick && !showChangePick && !t1Picked && !t1Won ? 'opacity-30' : ''}`}>
            <div className="relative mb-1.5">
              {/* My pick that won — green ✓ */}
              {t1Picked && !t1Lost && (
                <span className="absolute -top-1 -right-1 z-10 w-5 h-5 bg-green-500 rounded-full flex items-center justify-center text-white text-[10px] border-2 border-white">✓</span>
              )}
              {/* My pick that lost — red ✗ */}
              {t1Lost && (
                <span className="absolute -top-1 -left-1 z-10 w-5 h-5 bg-red-500 rounded-full flex items-center justify-center text-white text-[10px] border-2 border-white">✗</span>
              )}
              {/* Winner I didn't pick — amber ★ */}
              {t1WinnerNotPicked && (
                <span className="absolute -top-1 -right-1 z-10 w-5 h-5 bg-amber-400 rounded-full flex items-center justify-center text-white text-[10px] border-2 border-white">★</span>
              )}
              <div className={`${t1Picked && !t1Lost ? 'ring-2 ring-green-500 rounded-full' : t1Lost ? 'ring-2 ring-red-500 rounded-full' : t1WinnerNotPicked ? 'ring-2 ring-amber-400 rounded-full' : ''}`}>
                <TeamLogo team={match.team1} bgColor="#E6F1FB" />
              </div>
            </div>
            <span className={`text-sm font-medium text-center leading-tight ${t1Won && t1Picked ? 'text-green-600' : t1WinnerNotPicked ? 'text-amber-600' : t1Lost ? 'text-red-500' : 'text-gray-800'}`}>
              {match.team1?.name}
            </span>
          </div>

          <div className="text-gray-400 font-medium text-sm pt-3">VS</div>

          {/* Team 2 */}
          <div className={`flex-1 flex flex-col items-center transition-opacity ${hasPick && !showChangePick && !t2Picked && !t2Won ? 'opacity-30' : ''}`}>
            <div className="relative mb-1.5">
              {/* My pick that won — green ✓ */}
              {t2Picked && !t2Lost && (
                <span className="absolute -top-1 -right-1 z-10 w-5 h-5 bg-green-500 rounded-full flex items-center justify-center text-white text-[10px] border-2 border-white">✓</span>
              )}
              {/* My pick that lost — red ✗ */}
              {t2Lost && (
                <span className="absolute -top-1 -left-1 z-10 w-5 h-5 bg-red-500 rounded-full flex items-center justify-center text-white text-[10px] border-2 border-white">✗</span>
              )}
              {/* Winner I didn't pick — amber ★ */}
              {t2WinnerNotPicked && (
                <span className="absolute -top-1 -right-1 z-10 w-5 h-5 bg-amber-400 rounded-full flex items-center justify-center text-white text-[10px] border-2 border-white">★</span>
              )}
              <div className={`${t2Picked && !t2Lost ? 'ring-2 ring-green-500 rounded-full' : t2Lost ? 'ring-2 ring-red-500 rounded-full' : t2WinnerNotPicked ? 'ring-2 ring-amber-400 rounded-full' : ''}`}>
                <TeamLogo team={match.team2} bgColor="#EAF3DE" />
              </div>
            </div>
            <span className={`text-sm font-medium text-center leading-tight ${t2Won && t2Picked ? 'text-green-600' : t2WinnerNotPicked ? 'text-amber-600' : t2Lost ? 'text-red-500' : 'text-gray-800'}`}>
              {match.team2?.name}
            </span>
          </div>
        </div>

        {/* Match info */}
        <div className="border-t border-gray-100 pt-3 mb-3">
          <div className="text-xs text-gray-500">{format(dt, 'EEE d MMM · h:mm a')} · {match.venue}</div>
          {isUrgent && (
            <div className="text-xs font-medium mt-1" style={{ color: '#f59e0b' }}>
              ⏰ Locks in {Math.ceil((dt.getTime() - now) / 3600000)}h
            </div>
          )}
          {hasPick && !isCompleted && (
            <div className="text-xs font-medium mt-1 text-green-600">
              ✓ You picked {t1Picked ? match.team1?.name : match.team2?.name}
              {powerup && ` · ${POWERUP_META[powerup].emoji} ${POWERUP_META[powerup].label} ${POWERUP_META[powerup].suffix}`}
            </div>
          )}
          {isBeyondWindow && (
            <div className="text-xs text-gray-400 italic mt-1">Opens within {stats?.pick_window_days ?? 5} days of match</div>
          )}
        </div>

        {error && <div className="text-xs text-red-500 bg-red-50 rounded px-2 py-1 mb-2">{error}</div>}

        {/* Pick distribution */}
        {sel && (
          <PickDistribution
            team1={sel.team1} team2={sel.team2}
            team1Count={sel.team1_count} team2Count={sel.team2_count}
            hiddenCount={sel.hidden_count ?? 0}
            isCompleted={isCompleted}
          />
        )}

        {/* Points explanation */}
        {isSkipped && (
          <p className="text-xs mt-2 font-medium text-gray-400">
            You skipped this match — 0 points
          </p>
        )}
        {isCompleted && hasPick && pointsDisplay && sel && (
          <p className="text-xs mt-2 font-medium" style={pointsDisplay.positive ? { color: '#085041' } : { color: '#791F1F' }}>
            {pointsDisplay.positive
              ? `You earned ${pointsDisplay.text} (${match.match_points} pt × ${match.result === 'team1' ? sel.team2_count : sel.team1_count} opponents who picked the loser)`
              : `You lost ${pointsDisplay.text} (${match.match_points} pt × ${match.result === 'team1' ? sel.team1_count : sel.team2_count} opponents who picked the winner)`
            }
          </p>
        )}

        {/* Pick action buttons */}
        {showPickButtons && (
          <div className="flex flex-col gap-2 mt-3">
            <div className="flex gap-2">
              <button onClick={() => handlePick(match.team1?.id)} disabled={saving}
                className="flex-1 py-2.5 rounded-lg text-sm font-medium transition"
                style={{ background: '#E6F1FB', color: '#0C447C' }}>
                {saving ? '…' : `Pick ${match.team1?.name}`}
              </button>
              <button onClick={() => handlePick(match.team2?.id)} disabled={saving}
                className="flex-1 py-2.5 rounded-lg text-sm font-medium transition"
                style={{ background: '#EAF3DE', color: '#27500A' }}>
                {saving ? '…' : `Pick ${match.team2?.name}`}
              </button>
            </div>
            {showChangePick && (
              <div className="flex flex-col gap-2">
                <div className="flex gap-2">
                  {!powerup && (
                    <button onClick={handleRemovePick} disabled={saving}
                      className="flex-1 py-2 rounded-lg text-sm text-red-500 border border-red-200 bg-red-50">
                      Skip / Remove pick
                    </button>
                  )}
                  <button onClick={() => setShowChangePick(false)}
                    className="px-4 py-2 rounded-lg text-sm text-gray-500 border border-gray-200">
                    Cancel
                  </button>
                </div>
                {powerup && (
                  <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-2 py-1.5">
                    {POWERUP_META[powerup].emoji} {POWERUP_META[powerup].label} applied — remove it to see option to skip match
                  </p>
                )}
              </div>
            )}
          </div>
        )}

        {/* Change pick / remove */}
        {hasPick && !showChangePick && !isLocked && !isCompleted && (
          <button onClick={() => setShowChangePick(true)}
            className="w-full mt-3 py-2.5 rounded-lg border border-gray-200 text-sm font-medium text-gray-700">
            Change pick
          </button>
        )}

        {/* Tap-to-apply PowerPlay (mobile) */}
        {selectedBooster && hasPick && !isLocked && !isCompleted && !showChangePick && !powerup && !powersDisabled && (
          <button
            onClick={onApplySelectedBooster}
            disabled={isApplying}
            className="w-full mt-3 py-2.5 rounded-lg text-sm font-medium border-2 transition"
            style={{ background: '#EEEDFE', color: '#3C3489', borderColor: '#AFA9EC' }}
          >
            {isApplying
              ? <span className="loading loading-spinner loading-xs" />
              : `Apply ${POWERUP_META[selectedBooster]?.emoji} ${POWERUP_META[selectedBooster]?.label}`
            }
          </button>
        )}

        {/* Powerup buttons (mobile tap) */}
        {hasPick && !isLocked && !isCompleted && !powersDisabled && !showChangePick && (
          <div className="flex gap-2 flex-wrap mt-3">
            {Object.entries(POWERUP_META).map(([type, { emoji, label, key }]) => {
              const available = (stats?.[key] ?? 0) > 0
              const isActive = powerup === type
              const otherActive = !!powerup && !isActive
              return (
                <button key={type} onClick={() => applyPowerup(type)}
                  disabled={(!available && !isActive) || otherActive || saving}
                  className="flex-1 py-1.5 rounded-lg text-xs font-medium border transition disabled:opacity-40"
                  style={isActive
                    ? { background: '#EEEDFE', color: '#3C3489', borderColor: '#AFA9EC' }
                    : { background: 'transparent', color: '#6b7280', borderColor: '#e5e7eb' }
                  }>
                  {emoji} {label}{isActive ? ' ✓' : ''}
                </button>
              )
            })}
          </div>
        )}

        {/* Footer link */}
        <div className="mt-3">
          <Link to={`/matches/${match.id}`} className="text-xs text-blue-600 hover:underline">
            View details →
          </Link>
        </div>
      </div>
    </div>
  )
}

function StateBadge({ isCompleted, isLive, isUrgent, hasPick, userWon }) {
  if (isCompleted && hasPick) {
    return userWon
      ? <span className="text-xs font-bold px-2.5 py-1 rounded-xl" style={{ background: '#EAF3DE', color: '#27500A' }}>✓ WON</span>
      : <span className="text-xs font-bold px-2.5 py-1 rounded-xl" style={{ background: '#FCEBEB', color: '#791F1F' }}>✗ LOST</span>
  }
  if (isCompleted) return <span className="text-xs font-medium px-2.5 py-1 rounded-xl bg-gray-100 text-gray-500">SKIPPED</span>
  if (isLive) return <span className="text-xs font-bold px-2.5 py-1 rounded-xl bg-red-100 text-red-700 animate-pulse">🔴 LIVE</span>
  if (hasPick) return <span className="text-xs font-bold px-2.5 py-1 rounded-xl" style={{ background: '#E1F5EE', color: '#085041' }}>✓ PICKED</span>
  if (isUrgent) return <span className="text-xs font-bold px-2.5 py-1 rounded-xl" style={{ background: '#FAEEDA', color: '#633806' }}>⏰ URGENT</span>
  return <span className="text-xs font-medium px-2.5 py-1 rounded-xl bg-gray-100 text-gray-500">UPCOMING</span>
}
