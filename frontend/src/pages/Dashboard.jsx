import { useRef, useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { matchesAPI } from '@/api/matches'
import { picksAPI } from '@/api/picks'
import { leaderboardAPI } from '@/api/leaderboard'
import useAuthStore from '@/store/authStore'
import HomeMatchCard from '@/components/home/HomeMatchCard'
import AlertBanner from '@/components/home/AlertBanner'
import Sidebar from '@/components/layout/Sidebar'
import Spinner from '@/components/ui/Spinner'

function liveRefetchInterval(query, upcomingRef) {
  const liveData = query.state.data
  if (liveData?.length > 0) return 30_000
  const now = Date.now()
  const twoHours = 2 * 60 * 60 * 1000
  const hasMatchSoon = upcomingRef.current?.some(m => {
    const dt = new Date(m.datetime).getTime()
    return dt > now && dt - now < twoHours
  })
  return hasMatchSoon ? 5 * 60_000 : false
}

export default function Dashboard() {
  const { user } = useAuthStore()
  const qc = useQueryClient()
  const upcomingRef = useRef([])
  const [dragTargetId, setDragTargetId] = useState(null)
  const [selectedBooster, setSelectedBooster] = useState(null)
  const [applyingBoosterId, setApplyingBoosterId] = useState(null)

  const { data: upcoming } = useQuery({
    queryKey: ['matches', 'upcoming'],
    queryFn: () => matchesAPI.upcoming().then(r => r.data),
  })
  useEffect(() => {
    if (upcoming) upcomingRef.current = upcoming
  }, [upcoming])

  const { data: live } = useQuery({
    queryKey: ['matches', 'live'],
    queryFn: () => matchesAPI.live().then(r => r.data),
    refetchInterval: query => liveRefetchInterval(query, upcomingRef),
  })

  const { data: completed, isLoading: completedLoading } = useQuery({
    queryKey: ['matches', 'completed'],
    queryFn: () => matchesAPI.completed().then(r => r.data),
  })

  const { data: stats } = useQuery({
    queryKey: ['picks', 'stats'],
    queryFn: () => picksAPI.stats().then(r => r.data),
  })

  const { data: myRank } = useQuery({
    queryKey: ['leaderboard', 'me'],
    queryFn: () => leaderboardAPI.me().then(r => r.data),
  })

  const { data: active } = useQuery({
    queryKey: ['picks', 'active'],
    queryFn: () => picksAPI.active().then(r => r.data),
  })

  const { data: historyData } = useQuery({
    queryKey: ['picks', 'history', 'all'],
    queryFn: () => picksAPI.history({ page_size: 200 }).then(r => r.data),
  })

  // Map match id → pick (active picks take priority; history fills in completed matches)
  const pickMap = {}
  historyData?.results?.forEach(b => { pickMap[b.match] = b })
  active?.forEach(b => { pickMap[b.match] = b })

  // Matches to show on home
  const upcomingToShow = [...(live ?? []), ...(upcoming ?? [])].slice(0, 2)
  const recentResults = (completed ?? []).slice(0, 2)

  async function handleBoosterApply(matchId, pickId, boosterType) {
    if (!boosterType || !pickId) return
    setApplyingBoosterId(matchId)
    setSelectedBooster(null)
    try {
      await picksAPI.applyPowerup(pickId, boosterType)
      qc.invalidateQueries({ queryKey: ['picks', 'active'] })
      qc.invalidateQueries({ queryKey: ['picks', 'stats'] })
    } catch {
      // error shown in card via its own applyPowerup handler
    } finally {
      setApplyingBoosterId(null)
    }
  }

  function makeDragHandlers(matchId, pickId) {
    return {
      isDragTarget: dragTargetId === matchId,
      onDragOver: (e) => { e.preventDefault(); setDragTargetId(matchId) },
      onDragLeave: () => setDragTargetId(null),
      onDrop: (e) => {
        e.preventDefault()
        setDragTargetId(null)
        const boosterType = e.dataTransfer.getData('boosterType')
        handleBoosterApply(matchId, pickId, boosterType)
      },
    }
  }

  return (
    <div>
      {/* Responsive layout: sidebar on lg+ */}
      <div className="lg:grid lg:grid-cols-[320px_1fr] lg:gap-6 lg:items-start">

        {/* Sidebar (desktop only) */}
        <aside className="hidden lg:block">
          <Sidebar
            myRank={myRank}
            stats={stats}
            selectedBooster={selectedBooster}
            onSelectBooster={setSelectedBooster}
          />
        </aside>

        {/* Main content */}
        <div className="space-y-4">

          {/* Mobile stats grid */}
          <div className="lg:hidden grid grid-cols-3 gap-2.5">
            <div className="bg-white rounded-lg p-3 text-center border-2 border-blue-400">
              <p className="text-xs text-gray-500 mb-1">Rank</p>
              <p className="text-2xl font-medium text-blue-500">{myRank ? `#${myRank.rank}` : '–'}</p>
            </div>
            <div className="bg-white rounded-lg p-3 text-center border border-gray-200">
              <p className="text-xs text-gray-500 mb-1">Points</p>
              <p className="text-2xl font-medium text-gray-800">{myRank?.total ?? '–'}</p>
            </div>
            <div className="bg-white rounded-lg p-3 text-center border border-gray-200">
              <p className="text-xs text-gray-500 mb-1">Skips</p>
              <p className="text-2xl font-medium">
                <span style={{ color: (myRank?.skipped ?? 0) > 3 ? '#f59e0b' : '#1f2937' }}>
                  {myRank?.skipped ?? '–'}
                </span>
                {myRank && <small className="text-sm text-gray-400">/5</small>}
              </p>
            </div>
          </div>

          {/* Mobile boosters card — sticky below header */}
          {stats && !stats.powerups_disabled && (
            <div className="lg:hidden sticky top-16 z-40 bg-white rounded-xl border border-gray-100 shadow-md py-2.5 px-3">
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-gray-500 shrink-0">
                  {selectedBooster ? 'Tap match →' : 'PowerPlays:'}
                </span>
                <div className="flex gap-2 flex-1">
                  {[
                    { type: 'hidden',      label: 'Hidden', emoji: '🕵️', count: stats.hidden_count,      bg: '#EEEDFE', border: '#AFA9EC', nameColor: '#3C3489' },
                    { type: 'fake',        label: 'Googly', emoji: '🎭', count: stats.fake_count,        bg: '#FBEAF0', border: '#ED93B1', nameColor: '#72243E' },
                    { type: 'no_negative', label: 'The Wall', emoji: '🛡️', count: stats.no_negative_count, bg: '#E1F5EE', border: '#5DCAA5', nameColor: '#085041' },
                  ].map(({ type, label, emoji, count, bg, border, nameColor }) => {
                    const isSelected = selectedBooster === type
                    return (
                      <button
                        key={type}
                        draggable={count > 0}
                        onDragStart={count > 0 ? (e) => {
                          e.dataTransfer.setData('boosterType', type)
                          e.dataTransfer.effectAllowed = 'copy'
                        } : undefined}
                        onClick={() => count > 0 && setSelectedBooster(prev => prev === type ? null : type)}
                        disabled={count === 0}
                        title={label}
                        className="flex-1 flex flex-col items-center justify-center gap-0.5 py-1.5 rounded-lg border-2 transition-all disabled:opacity-40 cursor-grab active:cursor-grabbing min-w-0"
                        style={{
                          background: bg,
                          borderColor: isSelected ? nameColor : border,
                          borderStyle: isSelected ? 'solid' : 'dashed',
                          outline: isSelected ? `2px solid ${nameColor}` : 'none',
                          outlineOffset: '2px',
                        }}
                      >
                        <span className="text-lg leading-none">{emoji}</span>
                        <span className="text-xs font-bold leading-none" style={{ color: nameColor }}>{count}</span>
                      </button>
                    )
                  })}
                </div>
              </div>
            </div>
          )}

          {/* Alert banner */}
          <AlertBanner missingPicks={stats?.missing_picks} urgentMissing={stats?.urgent_missing_picks ?? 0} />

          {/* Upcoming + Live section */}
          <section>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-base font-medium text-gray-800">
                {live?.length > 0 ? '🔴 Live & Upcoming' : 'Upcoming matches'}
              </h2>
              <Link to="/schedule" className="text-sm font-medium text-blue-600 hover:underline">All predictions →</Link>
            </div>

            {!upcoming && !live ? (
              <Spinner />
            ) : upcomingToShow.length === 0 ? (
              <div className="bg-white rounded-xl border border-gray-100 p-8 text-center text-gray-400">No upcoming matches.</div>
            ) : (
              <div className="grid grid-cols-[repeat(auto-fit,minmax(min(400px,100%),1fr))] gap-4">
                {upcomingToShow.map(m => {
                  const pick = pickMap[m.id] ?? null
                  const dragHandlers = makeDragHandlers(m.id, pick?.id)
                  return (
                    <HomeMatchCard
                      key={m.id}
                      match={m}
                      pick={pick}
                      stats={stats}
                      {...dragHandlers}
                      isApplying={applyingBoosterId === m.id}
                      selectedBooster={selectedBooster}
                      onApplySelectedBooster={() => handleBoosterApply(m.id, pick?.id, selectedBooster)}
                    />
                  )
                })}
              </div>
            )}
          </section>

          {/* Recent results section */}
          <section>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-base font-medium text-gray-800">Recent results</h2>
              <Link to="/results" className="text-sm font-medium text-blue-600 hover:underline">See all results →</Link>
            </div>

            {completedLoading ? (
              <Spinner />
            ) : recentResults.length === 0 ? (
              <div className="bg-white rounded-xl border border-gray-100 p-8 text-center text-gray-400">No results yet.</div>
            ) : (
              <div className="grid grid-cols-[repeat(auto-fit,minmax(min(400px,100%),1fr))] gap-4">
                {recentResults.map(m => (
                  <HomeMatchCard
                    key={m.id}
                    match={m}
                    pick={pickMap[m.id] ?? null}
                    stats={stats}
                  />
                ))}
              </div>
            )}
          </section>

        </div>
      </div>
    </div>
  )
}
