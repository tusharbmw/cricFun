import { useEffect, useRef, useState } from 'react'
import { useInfiniteQuery, useQuery, useQueryClient } from '@tanstack/react-query'
import { format } from 'date-fns'
import { matchesAPI } from '@/api/matches'
import { picksAPI } from '@/api/picks'
import Spinner from '@/components/ui/Spinner'
import PickDistribution from '@/components/home/PickDistribution'
import { useCountdown } from '@/hooks/useCountdown'

const POWERUP_META = {
  hidden:      { emoji: '🕵️', label: 'Hidden',   key: 'hidden_count',      suffix: 'from others' },
  fake:        { emoji: '🃏', label: 'Googly',   key: 'fake_count',        suffix: 'for others' },
  no_negative: { emoji: '🛡️', label: 'The Wall', key: 'no_negative_count', suffix: 'applied' },
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

function StateBadge({ isLive, isUrgent, hasPick, isBeyondWindow }) {
  if (isLive) return <span className="text-xs font-bold px-2.5 py-1 rounded-xl bg-red-100 text-red-700 animate-pulse">🔴 LIVE</span>
  if (isBeyondWindow) return <span className="text-xs font-medium px-2.5 py-1 rounded-xl bg-gray-100 text-gray-500">UPCOMING</span>
  if (hasPick) return <span className="text-xs font-bold px-2.5 py-1 rounded-xl" style={{ background: '#E1F5EE', color: '#085041' }}>✓ PICKED</span>
  if (isUrgent) return <span className="text-xs font-bold px-2.5 py-1 rounded-xl" style={{ background: '#FAEEDA', color: '#633806' }}>⏰ URGENT</span>
  return <span className="text-xs font-medium px-2.5 py-1 rounded-xl bg-gray-100 text-gray-500">UPCOMING</span>
}

function MatchPickRow({ match, existingPick, stats }) {
  const qc = useQueryClient()
  const [selected, setSelected] = useState(existingPick?.selection ?? null)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState('')
  const [powerupLoading, setPowerupLoading] = useState(null)
  const [showChangePick, setShowChangePick] = useState(false)

  // eslint-disable-next-line react-hooks/purity
  const now = Date.now()
  const dt = new Date(match.datetime)
  const pickWindowMs = (stats?.pick_window_days ?? 5) * 24 * 60 * 60 * 1000
  const isBeyondWindow = match.result === 'TBD' && dt.getTime() - now > pickWindowMs
  const isLive = match.result === 'IP' || match.result === 'TOSS'
  const isLocked = match.result !== 'TBD' || isBeyondWindow || isLive
  const isUrgent = !isLocked && dt.getTime() - now < 24 * 3600 * 1000

  const hasPick = selected !== null
  const hasPowerup = existingPick?.hidden || existingPick?.fake || existingPick?.no_negative
  const powerupsDisabled = stats?.powerups_disabled ?? true
  const appliedPowerup = existingPick?.hidden ? 'hidden' : existingPick?.fake ? 'fake' : existingPick?.no_negative ? 'no_negative' : null

  const countdown = useCountdown(match.datetime)
  const isUrgentTimer = !isLocked && dt.getTime() - now < 60 * 60 * 1000

  const { data: sel } = useQuery({
    queryKey: ['match', match.id, 'selections'],
    queryFn: () => matchesAPI.selections(match.id).then(r => r.data),
    staleTime: 60 * 1000,
  })

  const showPickButtons = !isLocked && (!hasPick || showChangePick)
  const t1Selected = selected === match.team1?.id
  const t2Selected = selected === match.team2?.id

  async function handleSelect(teamId) {
    if (isLocked || teamId === selected) return
    const prevSelected = selected
    setSelected(teamId)
    setSaving(true)
    setSaveError('')
    try {
      if (!existingPick) {
        await picksAPI.place({ match: match.id, selection: teamId })
      } else {
        await picksAPI.update(existingPick.id, { selection: teamId })
      }
      qc.invalidateQueries({ queryKey: ['picks', 'active'] })
      qc.invalidateQueries({ queryKey: ['picks', 'stats'] })
      setShowChangePick(false)
    } catch (err) {
      setSaveError(err.response?.data?.non_field_errors?.[0] ?? 'Failed to save')
      setSelected(prevSelected)
    } finally {
      setSaving(false)
    }
  }

  async function handleRemove() {
    if (hasPowerup || isLocked) return
    const prevSelected = selected
    setSelected(null)
    setSaving(true)
    setSaveError('')
    try {
      if (existingPick) await picksAPI.remove(existingPick.id)
      qc.invalidateQueries({ queryKey: ['picks', 'active'] })
      qc.invalidateQueries({ queryKey: ['picks', 'stats'] })
      setShowChangePick(false)
    } catch (err) {
      setSaveError(err.response?.data?.error ?? 'Failed to remove')
      setSelected(prevSelected)
    } finally {
      setSaving(false)
    }
  }

  async function handlePowerup(type) {
    if (!existingPick) return
    setPowerupLoading(type)
    setSaveError('')
    try {
      await picksAPI.applyPowerup(existingPick.id, type)
      qc.invalidateQueries({ queryKey: ['picks', 'active'] })
      qc.invalidateQueries({ queryKey: ['picks', 'stats'] })
    } catch (err) {
      setSaveError(err.response?.data?.error ?? 'Failed to apply powerup')
    } finally {
      setPowerupLoading(null)
    }
  }

  const cardBorder = isUrgent && !hasPick ? 'border-2 border-amber-400' : 'border border-gray-200'

  return (
    <div className={`bg-white rounded-xl relative transition-all ${cardBorder}`}>
      {appliedPowerup && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2 z-10 flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded-full shadow border"
          style={{ background: '#EEEDFE', color: '#3C3489', borderColor: '#AFA9EC' }}>
          <span>{POWERUP_META[appliedPowerup].emoji}</span>
          <span>{POWERUP_META[appliedPowerup].label}</span>
          {!isLocked && (
            <button onClick={() => handlePowerup(appliedPowerup)} className="ml-1 font-bold hover:opacity-70">×</button>
          )}
        </div>
      )}

      <div className="p-4 pt-5">
        {/* Header */}
        <div className="flex items-start justify-between gap-2 mb-3">
          <div className="flex items-center gap-2 flex-wrap">
            <StateBadge isLive={isLive} isUrgent={isUrgent} hasPick={hasPick} isBeyondWindow={isBeyondWindow} />
            <span className="text-xs text-gray-400">{match.description}</span>
            {saving && <span className="loading loading-spinner loading-xs text-primary" />}
          </div>
          <span className="text-xs font-medium px-2 py-0.5 rounded shrink-0" style={{ background: '#E6F1FB', color: '#0C447C' }}>
            {match.match_points}× pts
          </span>
        </div>

        {/* Teams */}
        <div className="flex items-start justify-center gap-3 mb-3">
          <div className={`flex-1 flex flex-col items-center transition-opacity ${hasPick && !showChangePick && !t1Selected ? 'opacity-30' : ''}`}>
            <div className="relative mb-1.5">
              {t1Selected && !showChangePick && (
                <span className="absolute -top-1 -right-1 z-10 w-5 h-5 bg-green-500 rounded-full flex items-center justify-center text-white text-[10px] border-2 border-white">✓</span>
              )}
              <div className={t1Selected && !showChangePick ? 'ring-2 ring-green-500 rounded-full' : ''}>
                <TeamLogo team={match.team1} bgColor="#E6F1FB" />
              </div>
            </div>
            <span className="text-sm font-medium text-center leading-tight text-gray-800">{match.team1?.name}</span>
          </div>

          <div className="text-gray-400 font-medium text-sm pt-3">VS</div>

          <div className={`flex-1 flex flex-col items-center transition-opacity ${hasPick && !showChangePick && !t2Selected ? 'opacity-30' : ''}`}>
            <div className="relative mb-1.5">
              {t2Selected && !showChangePick && (
                <span className="absolute -top-1 -right-1 z-10 w-5 h-5 bg-green-500 rounded-full flex items-center justify-center text-white text-[10px] border-2 border-white">✓</span>
              )}
              <div className={t2Selected && !showChangePick ? 'ring-2 ring-green-500 rounded-full' : ''}>
                <TeamLogo team={match.team2} bgColor="#EAF3DE" />
              </div>
            </div>
            <span className="text-sm font-medium text-center leading-tight text-gray-800">{match.team2?.name}</span>
          </div>
        </div>

        {/* Match info */}
        <div className="border-t border-gray-100 pt-3 mb-3">
          <div className="text-xs text-gray-500">{format(dt, 'EEE d MMM · h:mm a')} · {match.venue}</div>
          {countdown && !isLocked && (
            <span className={`inline-flex items-center gap-1 mt-1 text-xs font-medium ${isUrgentTimer ? 'text-amber-600' : 'text-gray-500'}`}>
              ⏱ {countdown}
            </span>
          )}
          {hasPick && !showChangePick && (
            <div className="text-xs font-medium mt-1 text-green-600">
              ✓ You picked {t1Selected ? match.team1?.name : match.team2?.name}
              {appliedPowerup && ` · ${POWERUP_META[appliedPowerup].emoji} ${POWERUP_META[appliedPowerup].label} ${POWERUP_META[appliedPowerup].suffix}`}
            </div>
          )}
          {isBeyondWindow && (
            <div className="text-xs text-gray-400 italic mt-1">Opens within {stats?.pick_window_days ?? 5} days of match</div>
          )}
          {isLive && (
            <div className="text-xs text-gray-400 italic mt-1">Match in progress — picks locked</div>
          )}
        </div>

        {saveError && <div className="text-xs text-red-500 bg-red-50 rounded px-2 py-1 mb-2">{saveError}</div>}

        {/* Pick distribution */}
        {sel && (
          <PickDistribution
            team1={sel.team1} team2={sel.team2}
            team1Count={sel.team1_count} team2Count={sel.team2_count}
            hiddenCount={sel.hidden_count ?? 0}
            isCompleted={false}
          />
        )}

        {/* Pick buttons */}
        {showPickButtons && (
          <div className="flex flex-col gap-2 mt-3">
            <div className="flex gap-2">
              <button onClick={() => handleSelect(match.team1?.id)} disabled={saving}
                className="flex-1 py-2.5 rounded-lg text-sm font-medium transition"
                style={{ background: '#E6F1FB', color: '#0C447C' }}>
                {saving ? '…' : `Pick ${match.team1?.name}`}
              </button>
              <button onClick={() => handleSelect(match.team2?.id)} disabled={saving}
                className="flex-1 py-2.5 rounded-lg text-sm font-medium transition"
                style={{ background: '#EAF3DE', color: '#27500A' }}>
                {saving ? '…' : `Pick ${match.team2?.name}`}
              </button>
            </div>
            {showChangePick && (
              <div className="flex flex-col gap-2">
                <div className="flex gap-2">
                  {!hasPowerup && (
                    <button onClick={handleRemove} disabled={saving}
                      className="flex-1 py-2 rounded-lg text-sm text-red-500 border border-red-200 bg-red-50">
                      Skip / Remove pick
                    </button>
                  )}
                  <button onClick={() => setShowChangePick(false)}
                    className="px-4 py-2 rounded-lg text-sm text-gray-500 border border-gray-200">
                    Cancel
                  </button>
                </div>
                {hasPowerup && (
                  <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-2 py-1.5">
                    {POWERUP_META[appliedPowerup].emoji} {POWERUP_META[appliedPowerup].label} applied — remove it to see option to skip match
                  </p>
                )}
              </div>
            )}
          </div>
        )}

        {/* Change pick */}
        {hasPick && !showChangePick && !isLocked && (
          <button onClick={() => setShowChangePick(true)}
            className="w-full mt-3 py-2.5 rounded-lg border border-gray-200 text-sm font-medium text-gray-700">
            Change pick
          </button>
        )}

        {/* PowerPlay buttons */}
        {existingPick && !powerupsDisabled && !isLocked && !showChangePick && (
          <div className="flex gap-2 flex-wrap mt-3">
            {Object.entries(POWERUP_META).map(([type, { emoji, label, key }]) => {
              const available = (stats?.[key] ?? 0) > 0
              const isActive = appliedPowerup === type
              const otherApplied = !!appliedPowerup && !isActive
              return (
                <button key={type}
                  onClick={() => handlePowerup(type)}
                  disabled={(!available && !isActive) || otherApplied || powerupLoading !== null}
                  className="flex-1 py-1.5 rounded-lg text-xs font-medium border transition disabled:opacity-40"
                  style={isActive
                    ? { background: '#EEEDFE', color: '#3C3489', borderColor: '#AFA9EC' }
                    : { background: 'transparent', color: '#6b7280', borderColor: '#e5e7eb' }
                  }>
                  {powerupLoading === type
                    ? <span className="loading loading-spinner loading-xs" />
                    : `${emoji} ${label}${isActive ? ' ✓' : ''}`
                  }
                </button>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

export default function Schedule() {
  const sentinelRef = useRef(null)

  const {
    data,
    isLoading,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfiniteQuery({
    queryKey: ['matches', 'upcoming'],
    queryFn: ({ pageParam = 0 }) =>
      matchesAPI.upcoming({ offset: pageParam, limit: 10 }).then(r => r.data),
    initialPageParam: 0,
    getNextPageParam: (lastPage, allPages) =>
      lastPage.has_more ? allPages.length * 10 : undefined,
  })

  const upcoming = data?.pages.flatMap(p => p.results) ?? []

  useEffect(() => {
    const el = sentinelRef.current
    if (!el) return
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && hasNextPage && !isFetchingNextPage) fetchNextPage()
      },
      { threshold: 0.1 }
    )
    observer.observe(el)
    return () => observer.disconnect()
  }, [hasNextPage, isFetchingNextPage, fetchNextPage])
  const { data: activePicks } = useQuery({
    queryKey: ['picks', 'active'],
    queryFn: () => picksAPI.active().then(r => r.data),
  })
  const { data: stats } = useQuery({
    queryKey: ['picks', 'stats'],
    queryFn: () => picksAPI.stats().then(r => r.data),
  })

  const pickMap = {}
  activePicks?.forEach(b => { pickMap[b.match] = b })

  if (isLoading) return <Spinner />

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-800">Schedule</h1>
        {stats?.missing_picks > 0 && (
          <span className="badge badge-warning gap-1">
            ⚠ {stats.missing_picks} missing pick{stats.missing_picks !== 1 ? 's' : ''}
          </span>
        )}
      </div>

      {stats && !stats.powerups_disabled && (
        <div className="stats stats-horizontal bg-gray-50 shadow w-full">
          {[
            { key: 'hidden_count',      emoji: '🕵️', label: 'Hidden' },
            { key: 'fake_count',        emoji: '🃏',  label: 'Googly' },
            { key: 'no_negative_count', emoji: '🛡️', label: 'The Wall' },
          ].map(({ key, emoji, label }) => (
            <div key={key} className="stat place-items-center py-2">
              <div className="stat-value text-base text-secondary">{stats[key]}</div>
              <div className="stat-desc text-xs">{emoji} {label}</div>
            </div>
          ))}
        </div>
      )}

      {!upcoming.length && !isLoading ? (
        <div className="bg-white border border-gray-100 rounded-xl">
          <div className="text-center text-gray-400 py-10">No upcoming matches.</div>
        </div>
      ) : (
        upcoming.map(m => (
          <MatchPickRow
            key={m.id}
            match={m}
            existingPick={pickMap[m.id] ?? null}
            stats={stats}
          />
        ))
      )}

      <div ref={sentinelRef} className="flex items-center justify-center py-4">
        {isFetchingNextPage && <Spinner />}
      </div>
    </div>
  )
}
