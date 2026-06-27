import { useParams } from 'react-router-dom'
import { useState, useEffect, useRef } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { format } from 'date-fns'
import { matchesAPI } from '@/api/matches'
import { picksAPI } from '@/api/picks'
import Spinner from '@/components/ui/Spinner'
import { matchStatusBadge } from '@/components/ui/Badge'
import { OddsCardFull } from '@/components/match/OddsBar'
import useTournamentStore from '@/store/tournamentStore'
import { useCountdown } from '@/hooks/useCountdown'

const POWERUP_META = {
  cricket: {
    hidden:      { emoji: '🕵️', label: 'Hidden',      key: 'hidden_count' },
    fake:        { emoji: '🃏', label: 'Googly',      key: 'fake_count' },
    no_negative: { emoji: '🛡️', label: 'The Wall',   key: 'no_negative_count' },
  },
  soccer: {
    hidden:      { emoji: '🕵️', label: 'Hidden',      key: 'hidden_count' },
    fake:        { emoji: '🪄', label: 'Dummy',        key: 'fake_count' },
    no_negative: { emoji: '🧤', label: 'Clean Sheet', key: 'no_negative_count' },
  },
}

function MatchDetailPicker({ match, existingPick, pickStats, PM, onPickChange }) {
  const [selected, setSelected] = useState(
    existingPick?.draw ? 'draw' : (existingPick?.selection ?? null)
  )
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState('')
  const [showChange, setShowChange] = useState(false)
  const [powerupLoading, setPowerupLoading] = useState(null)
  const [showDecoyPicker, setShowDecoyPicker] = useState(false)
  const [pendingDecoy, setPendingDecoy] = useState(null)

  useEffect(() => {
    setSelected(existingPick?.draw ? 'draw' : (existingPick?.selection ?? null))
  }, [existingPick])

  const now = Date.now()
  const dt = new Date(match.datetime)
  const pickWindowMs = (pickStats?.pick_window_days ?? 5) * 24 * 60 * 60 * 1000
  const isBeyondWindow = dt.getTime() - now > pickWindowMs
  const isLive = match.result === 'IP' || match.result === 'TOSS'
  const teamsConfirmed = !!(match.team1?.name && match.team1.name !== 'TBD' && match.team2?.name && match.team2.name !== 'TBD')
  const isLocked = match.result !== 'TBD' || isBeyondWindow || isLive || !teamsConfirmed
  const isUrgent = !isLocked && dt.getTime() - now < 24 * 3600 * 1000

  const hasPick = selected !== null
  const drawSelected = selected === 'draw'
  const t1Selected = selected === match.team1?.id
  const hasPowerup = existingPick?.hidden || existingPick?.fake || existingPick?.no_negative
  const appliedPowerup = existingPick?.hidden ? 'hidden' : existingPick?.fake ? 'fake' : existingPick?.no_negative ? 'no_negative' : null
  const powerupsDisabled = match.is_high_stakes
  const countdown = useCountdown(match.datetime)

  const showPickButtons = !isLocked && (!hasPick || showChange)

  async function handleSelect(teamIdOrDraw) {
    if (isLocked || teamIdOrDraw === selected) return
    const isDraw = teamIdOrDraw === 'draw'
    const prev = selected
    setSelected(teamIdOrDraw)
    setSaving(true)
    setSaveError('')
    try {
      if (!existingPick) {
        await picksAPI.place(isDraw ? { match: match.id, draw: true } : { match: match.id, selection: teamIdOrDraw })
      } else {
        await picksAPI.update(existingPick.id, isDraw ? { draw: true } : { draw: false, selection: teamIdOrDraw })
      }
      setShowChange(false)
      onPickChange()
    } catch (err) {
      setSaveError(err.response?.data?.detail ?? err.response?.data?.non_field_errors?.[0] ?? 'Failed to save')
      setSelected(prev)
    } finally {
      setSaving(false)
    }
  }

  async function handleRemove() {
    if (hasPowerup || isLocked || !existingPick) return
    const prev = selected
    setSelected(null)
    setSaving(true)
    setSaveError('')
    try {
      await picksAPI.remove(existingPick.id)
      setShowChange(false)
      onPickChange()
    } catch (err) {
      setSaveError(err.response?.data?.error ?? 'Failed to remove')
      setSelected(prev)
    } finally {
      setSaving(false)
    }
  }

  async function handlePowerup(type) {
    if (!existingPick) return
    if (type === 'fake' && !appliedPowerup && match.allows_draw) {
      setShowDecoyPicker(p => !p)
      setPendingDecoy(null)
      return
    }
    setPowerupLoading(type)
    setSaveError('')
    try {
      await picksAPI.applyPowerup(existingPick.id, type)
      onPickChange()
    } catch (err) {
      setSaveError(err.response?.data?.error ?? 'Failed to apply powerup')
    } finally {
      setPowerupLoading(null)
    }
  }

  async function handleApplyFakeWithDecoy(decoyKey) {
    if (!existingPick) return
    setPowerupLoading('fake')
    setSaveError('')
    const extra = decoyKey === 'draw'
      ? { fake_draw: true }
      : { fake_selection_id: decoyKey === 'team1' ? match.team1?.id : match.team2?.id }
    try {
      await picksAPI.applyPowerup(existingPick.id, 'fake', extra)
      onPickChange()
      setShowDecoyPicker(false)
      setPendingDecoy(null)
    } catch (err) {
      setSaveError(err.response?.data?.error ?? 'Failed to apply powerup')
    } finally {
      setPowerupLoading(null)
    }
  }

  return (
    <div className="bg-white border border-gray-100 rounded-xl shadow-sm">
      <div className="p-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold text-gray-600">Your Pick</h2>
          {saving && <span className="loading loading-spinner loading-xs text-primary" />}
        </div>

        {isBeyondWindow && (
          <p className="text-sm text-gray-400 italic">Pick window opens within {pickStats?.pick_window_days ?? 5} days of match.</p>
        )}
        {isLive && (
          <p className="text-sm text-gray-400 italic">Match in progress — picks are locked.</p>
        )}
        {!teamsConfirmed && (
          <p className="text-sm text-gray-400 italic">Teams not yet confirmed.</p>
        )}

        {hasPick && !showChange && (
          <div className="text-sm font-medium text-green-700 bg-green-50 rounded-lg px-3 py-2 mb-3">
            ✓ You picked {drawSelected ? '⚖ Draw' : t1Selected ? match.team1?.name : match.team2?.name}
            {appliedPowerup && ` · ${PM[appliedPowerup]?.emoji} ${PM[appliedPowerup]?.label}`}
          </div>
        )}
        {isUrgent && !hasPick && !isLocked && countdown && (
          <p className="text-xs text-amber-600 mb-2">⏱ {countdown} until lock</p>
        )}

        {saveError && <div className="text-xs text-red-500 bg-red-50 rounded px-2 py-1 mb-2">{saveError}</div>}

        {showPickButtons && (
          <div className="flex gap-2">
            <button onClick={() => handleSelect(match.team1?.id)} disabled={saving}
              className="flex-1 py-2.5 rounded-lg text-sm font-medium"
              style={{ background: '#E6F1FB', color: '#0C447C' }}>
              {saving ? '…' : `Pick ${match.team1?.name}`}
            </button>
            {match.allows_draw && (
              <button onClick={() => handleSelect('draw')} disabled={saving}
                className="py-2.5 px-3 rounded-lg text-sm font-medium border-2 border-dashed shrink-0"
                style={{ borderColor: '#C49A36', color: '#7A5A1A', background: drawSelected ? '#EFD89A' : '#FBF5E6' }}>
                {saving ? '…' : '⚖ Draw'}
              </button>
            )}
            <button onClick={() => handleSelect(match.team2?.id)} disabled={saving}
              className="flex-1 py-2.5 rounded-lg text-sm font-medium"
              style={{ background: '#EAF3DE', color: '#27500A' }}>
              {saving ? '…' : `Pick ${match.team2?.name}`}
            </button>
          </div>
        )}

        {showChange && (
          <div className="flex gap-2 mt-2">
            {!hasPowerup && (
              <button onClick={handleRemove} disabled={saving}
                className="flex-1 py-2 rounded-lg text-sm text-red-500 border border-red-200 bg-red-50">
                Skip / Remove
              </button>
            )}
            <button onClick={() => setShowChange(false)}
              className="px-4 py-2 rounded-lg text-sm text-gray-500 border border-gray-200">
              Cancel
            </button>
          </div>
        )}

        {hasPick && !showChange && !isLocked && (
          <button onClick={() => setShowChange(true)}
            className="w-full mt-3 py-2.5 rounded-lg border border-gray-200 text-sm font-medium text-gray-700">
            Change pick
          </button>
        )}

        {existingPick && !powerupsDisabled && !isLocked && !showChange && (
          <div className="mt-3">
            <div className="flex gap-2 flex-wrap">
              {Object.entries(PM).map(([type, { emoji, label, key }]) => {
                const available = (pickStats?.[key] ?? 0) > 0
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
                      : `${emoji} ${label}${isActive ? ' ✓' : ''}`}
                  </button>
                )
              })}
            </div>
            {showDecoyPicker && !appliedPowerup && hasPick && (
              <div className="mt-2 p-2.5 rounded-lg border" style={{ background: '#FBEAF0', borderColor: '#ED93B1' }}>
                <p className="text-[9px] font-bold tracking-widest uppercase mb-2" style={{ color: '#72243E' }}>
                  🪄 Decoy rivals will see
                </p>
                <div className="flex gap-2">
                  {[
                    { key: 'team1', label: match.team1?.name },
                    { key: 'draw',  label: 'Draw', glyph: '⚖' },
                    { key: 'team2', label: match.team2?.name },
                  ].filter(o => o.key !== (drawSelected ? 'draw' : t1Selected ? 'team1' : 'team2')).map(o => {
                    const active = pendingDecoy === o.key
                    return (
                      <button key={o.key} onClick={() => setPendingDecoy(active ? null : o.key)}
                        className="flex-1 flex items-center justify-center gap-1 py-2 px-1.5 rounded-lg text-xs font-bold transition"
                        style={{ background: active ? '#72243E' : 'white', border: `1.5px solid ${active ? '#72243E' : '#ED93B1'}`, color: active ? '#fff' : '#72243E' }}>
                        {o.glyph && <span>{o.glyph}</span>}{o.label}{active ? ' ✓' : ''}
                      </button>
                    )
                  })}
                </div>
                {pendingDecoy ? (
                  <div className="flex gap-2 mt-2">
                    <button onClick={() => handleApplyFakeWithDecoy(pendingDecoy)} disabled={powerupLoading !== null}
                      className="flex-1 py-1.5 rounded-lg text-xs font-bold"
                      style={{ background: '#72243E', color: '#fff' }}>
                      {powerupLoading === 'fake' ? <span className="loading loading-spinner loading-xs" /> : 'Apply Dummy'}
                    </button>
                    <button onClick={() => { setShowDecoyPicker(false); setPendingDecoy(null) }}
                      className="py-1.5 px-3 rounded-lg text-xs border border-gray-200 text-gray-500">
                      Cancel
                    </button>
                  </div>
                ) : (
                  <p className="text-[10px] mt-2 leading-snug" style={{ color: '#72243E', opacity: 0.85 }}>
                    Three outcomes — choose which one to flash as your decoy.
                  </p>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
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
  const qc = useQueryClient()
  const { currentTournament } = useTournamentStore()
  const tid = currentTournament?.id

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

  const { data: activePicks } = useQuery({
    queryKey: ['picks', 'active', tid],
    queryFn: () => picksAPI.active({ tournament: tid }).then(r => r.data),
    enabled: !!tid && !!match && match.result === 'TBD',
    staleTime: 30 * 1000,
  })

  const { data: pickStats } = useQuery({
    queryKey: ['picks', 'stats', tid],
    queryFn: () => picksAPI.stats({ tournament: tid }).then(r => r.data),
    staleTime: 60 * 1000,
    enabled: !!tid && !!match && match.result === 'TBD',
  })

  const existingPick = activePicks?.find(p => String(p.match) === String(id)) ?? null

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
                  <div className="flex flex-col">
                    <span className="text-lg font-bold text-gray-800">{match.team1?.name}</span>
                    {match.team1?.ranking != null && <span className="text-[10px] text-gray-400">#{match.team1.ranking}</span>}
                  </div>
                  <span className="text-2xl font-black text-gray-700 tabular-nums">
                    {match.home_score} — {match.away_score}
                  </span>
                  <div className="flex flex-col">
                    <span className="text-lg font-bold text-gray-800">{match.team2?.name}</span>
                    {match.team2?.ranking != null && <span className="text-[10px] text-gray-400">#{match.team2.ranking}</span>}
                  </div>
                </div>
              ) : (
                <h1 className="text-xl font-bold text-gray-800 mt-2">
                  {match.team1?.name} vs {match.team2?.name}
                  {(match.team1?.ranking != null || match.team2?.ranking != null) && (
                    <span className="text-sm font-normal text-gray-400 ml-2">
                      {match.team1?.ranking != null ? `#${match.team1.ranking}` : ''}{match.team1?.ranking != null && match.team2?.ranking != null ? ' vs ' : ''}{match.team2?.ranking != null ? `#${match.team2.ranking}` : ''}
                    </span>
                  )}
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

      {/* Pre-Match Odds */}
      {match.odds && match.result === 'TBD' && (
        <OddsCardFull
          odds={match.odds}
          team1Name={match.team1?.name}
          team2Name={match.team2?.name}
        />
      )}

      {/* Pick section — only for TBD matches */}
      {match.result === 'TBD' && tid && (
        <MatchDetailPicker
          match={match}
          existingPick={existingPick}
          pickStats={pickStats}
          PM={PM}
          onPickChange={() => {
            qc.invalidateQueries({ queryKey: ['picks', 'active', tid] })
            qc.invalidateQueries({ queryKey: ['picks', 'stats'] })
            qc.invalidateQueries({ queryKey: ['match', id, 'selections'] })
          }}
        />
      )}

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
