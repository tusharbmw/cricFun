import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  CartesianGrid, Line, LineChart, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from 'recharts'
import { TrendingUp, TrendingDown, MoveHorizontal } from 'lucide-react'
import { leaderboardAPI } from '@/api/leaderboard'
import useAuthStore from '@/store/authStore'
import Spinner from '@/components/ui/Spinner'
import useTournamentStore from '@/store/tournamentStore'

// ---------------------------------------------------------------------------
// X-axis label thinning helpers
// ---------------------------------------------------------------------------

function _stageKey(label) {
  const prefix = (label ?? '').split(':')[0]
  return /^M\d+$/.test(prefix) ? 'M' : prefix
}

function computeShownLabels(n, containerWidth, chartData) {
  if (n === 0) return new Set()
  const plotW     = Math.max(100, containerWidth - 60)
  const maxLabels = Math.max(2, Math.floor(plotW / 46))
  const labelStep = Math.max(1, Math.ceil((n - 1) / (maxLabels - 1)))

  const shown = new Set()
  for (let i = 0; i < n; i += labelStep) shown.add(i)

  // Always include the last; drop a near-last step to avoid crowding
  if (n > 1) {
    const last = n - 1
    for (const i of [...shown]) {
      if (i !== 0 && last - i < labelStep * 0.6) shown.delete(i)
    }
    shown.add(last)
  }

  // Force-show the first match of every non-group-stage round (R32, R16, QF, SF, Final…)
  if (chartData.length > 0) {
    let prevStage = null
    for (let i = 0; i < n; i++) {
      const stage = _stageKey(chartData[i]?.label ?? '')
      if (stage !== prevStage) {
        prevStage = stage
        if (stage !== 'M') {
          const tooClose = [...shown].some(s => Math.abs(s - i) < labelStep * 0.6)
          if (!tooClose) shown.add(i)
        }
      }
    }
  }

  return shown
}

function makeXTick(shownLabels) {
  return function CustomTick({ x, y, payload, index }) {
    if (!shownLabels.has(index)) return null
    const anchor = index === 0 ? 'start' : 'end'
    return (
      <g transform={`translate(${x},${y})`}>
        <text transform="rotate(-35)" textAnchor={anchor} fontSize={10} fill="#9ca3af" dy={4}>
          {payload.value}
        </text>
      </g>
    )
  }
}

// ---------------------------------------------------------------------------
// Shared empty state
// ---------------------------------------------------------------------------

function ChartEmptyState() {
  return (
    <div className="bg-white border border-gray-100 rounded-xl p-8 text-center text-gray-400 text-sm">
      Chart will appear after the first match result is recorded.
    </div>
  )
}

// ---------------------------------------------------------------------------
// Rank history line chart
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Shared chart legend
// ---------------------------------------------------------------------------

function ChartLegend({ allUsers, currentUsername, displayNames, activeUser, onHover, onLeave, onPin }) {
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-2 mt-3 pt-3 border-t border-gray-100">
      {allUsers.map(username => {
        const isMe = username === currentUsername
        const color = isMe ? '#2563eb' : '#94a3b8'
        const isActive = activeUser === username
        const isDimmed = activeUser && !isActive
        return (
          <button
            key={username}
            type="button"
            onMouseEnter={() => onHover(username)}
            onMouseLeave={onLeave}
            onClick={() => onPin(username)}
            className={`flex items-center gap-1.5 text-xs transition-opacity select-none ${isDimmed ? 'opacity-25' : 'opacity-100'}`}
          >
            <span className="inline-block w-5 shrink-0" style={{ height: 2, background: color, borderRadius: 1 }} />
            <span className={`${isActive ? 'font-semibold' : ''} ${isMe ? 'text-blue-600' : 'text-gray-500'}`}>
              {displayNames?.[username] || username}
            </span>
          </button>
        )
      })}
      <span className="w-full text-[10px] text-gray-300">Tap a name to highlight · tap again to clear</span>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Rank history line chart
// ---------------------------------------------------------------------------

function RankHistoryChart({ history, currentUsername, displayNames }) {
  const [hoveredUser, setHoveredUser]       = useState(null)
  const [pinnedUser, setPinnedUser]         = useState(null)
  const [containerWidth, setContainerWidth] = useState(300)
  const activeUser = pinnedUser ?? hoveredUser

  // Compute before early return so hooks are always called in the same order
  const chartData = (history ?? []).map(snap => {
    const point = { label: snap.label, full_label: snap.full_label }
    snap.rankings.forEach(r => { point[r.username] = r.rank })
    return point
  })
  const n           = chartData.length
  const shownLabels = computeShownLabels(n, containerWidth, chartData)
  const CustomTick  = makeXTick(shownLabels)

  if (!history?.length) return <ChartEmptyState />

  const allUsers = [...new Set(
    history.flatMap(snap => snap.rankings.map(r => r.username))
  )]
  const totalUsers = allUsers.length

  return (
    <div className="bg-white border border-gray-100 rounded-xl shadow-sm p-4">
      <h2 className="text-sm font-semibold text-gray-700 mb-4">Rank Progression</h2>
      <ResponsiveContainer width="100%" height={280} onResize={(w) => setContainerWidth(w)}>
        <LineChart data={chartData} margin={{ top: 4, right: 16, bottom: 48, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="label" interval={0} tick={CustomTick} />
          <YAxis
            reversed
            domain={[1, totalUsers]}
            tickCount={totalUsers}
            allowDecimals={false}
            tick={{ fontSize: 11, fill: '#6b7280' }}
            label={{ value: 'Rank', angle: -90, position: 'insideLeft', fontSize: 11, fill: '#9ca3af' }}
          />
          <Tooltip
            formatter={(value, name) => [`#${value}`, displayNames?.[name] || name]}
            labelFormatter={(_, payload) => payload?.[0]?.payload?.full_label ?? ''}
            contentStyle={{ fontSize: 12 }}
          />
          {allUsers.map(username => {
            const isMe     = username === currentUsername
            const isActive = activeUser === username
            const dimmed   = activeUser && !isActive
            return (
              <Line
                key={username}
                type="monotone"
                dataKey={username}
                stroke={isMe ? '#2563eb' : '#94a3b8'}
                strokeWidth={isActive ? (isMe ? 3 : 2.5) : (isMe ? 2.5 : 1)}
                strokeOpacity={dimmed ? 0.1 : 1}
                dot={isActive || isMe ? { r: 3, fill: isMe ? '#2563eb' : '#94a3b8' } : false}
                activeDot={{ r: isActive || isMe ? 5 : 3 }}
                connectNulls
              />
            )
          })}
        </LineChart>
      </ResponsiveContainer>
      <ChartLegend
        allUsers={allUsers}
        currentUsername={currentUsername}
        displayNames={displayNames}
        activeUser={activeUser}
        onHover={setHoveredUser}
        onLeave={() => setHoveredUser(null)}
        onPin={u => setPinnedUser(prev => prev === u ? null : u)}
      />
    </div>
  )
}

// ---------------------------------------------------------------------------
// Points progression line chart
// ---------------------------------------------------------------------------

function PointsProgressionChart({ history, currentUsername, displayNames }) {
  const [hoveredUser, setHoveredUser]       = useState(null)
  const [pinnedUser, setPinnedUser]         = useState(null)
  const [containerWidth, setContainerWidth] = useState(300)
  const activeUser = pinnedUser ?? hoveredUser

  const DQ_SCORE = -999

  // Compute before early return so hooks are always called in the same order
  const allTotals = (history ?? []).flatMap(snap =>
    snap.rankings.map(r => r.total).filter(t => t !== DQ_SCORE)
  )
  const minVal = allTotals.length ? Math.min(...allTotals) : 0
  const maxVal = allTotals.length ? Math.max(...allTotals) : 100
  const range  = Math.max(maxVal - minVal, 20)
  // DQ renders 20% below the chart floor so it's visually at the bottom
  const dqY    = Math.round(minVal - range * 0.2)

  const chartData = (history ?? []).map(snap => {
    const point = { label: snap.label, full_label: snap.full_label }
    snap.rankings.forEach(r => { point[r.username] = r.total === DQ_SCORE ? dqY : r.total })
    return point
  })
  const n           = chartData.length
  const shownLabels = computeShownLabels(n, containerWidth, chartData)
  const CustomTick  = makeXTick(shownLabels)

  if (!history?.length) return <ChartEmptyState />

  const allUsers = [...new Set(
    history.flatMap(snap => snap.rankings.map(r => r.username))
  )]

  return (
    <div className="bg-white border border-gray-100 rounded-xl shadow-sm p-4">
      <h2 className="text-sm font-semibold text-gray-700 mb-4">Points Progression</h2>
      <ResponsiveContainer width="100%" height={280} onResize={(w) => setContainerWidth(w)}>
        <LineChart data={chartData} margin={{ top: 4, right: 16, bottom: 48, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="label" interval={0} tick={CustomTick} />
          <YAxis
            domain={[dqY, maxVal + Math.round(range * 0.05)]}
            allowDecimals={false}
            tickFormatter={v => v < minVal ? 'DQ' : v}
            tick={{ fontSize: 11, fill: '#6b7280' }}
            label={{ value: 'Points', angle: -90, position: 'insideLeft', fontSize: 11, fill: '#9ca3af' }}
          />
          <Tooltip
            formatter={(value, name) => [value < minVal ? 'DQ' : value, displayNames?.[name] || name]}
            labelFormatter={(_, payload) => payload?.[0]?.payload?.full_label ?? ''}
            contentStyle={{ fontSize: 12 }}
          />
          {allUsers.map(username => {
            const isMe     = username === currentUsername
            const isActive = activeUser === username
            const dimmed   = activeUser && !isActive
            return (
              <Line
                key={username}
                type="monotone"
                dataKey={username}
                stroke={isMe ? '#2563eb' : '#94a3b8'}
                strokeWidth={isActive ? (isMe ? 3 : 2.5) : (isMe ? 2.5 : 1)}
                strokeOpacity={dimmed ? 0.1 : 1}
                dot={isActive || isMe ? { r: 3, fill: isMe ? '#2563eb' : '#94a3b8' } : false}
                activeDot={{ r: isActive || isMe ? 5 : 3 }}
                connectNulls
              />
            )
          })}
        </LineChart>
      </ResponsiveContainer>
      <ChartLegend
        allUsers={allUsers}
        currentUsername={currentUsername}
        displayNames={displayNames}
        activeUser={activeUser}
        onHover={setHoveredUser}
        onLeave={() => setHoveredUser(null)}
        onPin={u => setPinnedUser(prev => prev === u ? null : u)}
      />
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function Leaderboard() {
  const { user } = useAuthStore()
  const { currentTournament } = useTournamentStore()
  const tid = currentTournament?.id

  const { data: board, isLoading } = useQuery({
    queryKey: ['leaderboard', tid],
    queryFn: () => leaderboardAPI.global(tid).then(r => r.data),
    staleTime: 60000,
    enabled: !!tid,
  })

  const { data: history, isLoading: historyLoading } = useQuery({
    queryKey: ['leaderboard', 'history', tid],
    queryFn: () => leaderboardAPI.history(tid).then(r => r.data),
    staleTime: 5 * 60 * 1000,
    enabled: !!tid,
  })

  if (isLoading) return <Spinner />

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-2 flex-wrap">
        <div>
          <h1 className="text-xl font-bold text-gray-800">
            {board?.tournament_name ?? currentTournament?.name ?? 'Standings'}
            {board?.tournament_season && (
              <span className="ml-2 text-sm font-normal text-gray-400">{board.tournament_season}</span>
            )}
          </h1>
          {board?.player_count > 0 && (
            <p className="text-xs text-gray-400 mt-0.5">
              {board.player_count} players · separate from other arenas
            </p>
          )}
        </div>
        {board && (
          <span className="text-xs text-gray-400 shrink-0">
            <span className="font-medium text-gray-600">{board.matches_completed}</span> of{' '}
            <span className="font-medium text-gray-600">{board.matches_total}</span> completed
          </span>
        )}
      </div>

      {/* Standings table */}
      <div className="bg-white border border-gray-100 rounded-xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="table table-sm w-full">
            <thead className="sticky top-0 z-10 bg-white shadow-sm">
              <tr className="text-gray-500 text-xs uppercase tracking-wider">
                <th className="w-10">#</th>
                <th>Player</th>
                <th className="text-right">Pts</th>
                <th className="text-right">W</th>
                <th className="text-right">L</th>
                <th className="text-right">S</th>
                <th className="text-right">MW</th>
              </tr>
            </thead>
            <tbody>
              {board?.entries?.map((row, i) => {
                const entries = board.entries
                const isMe = row.username === user?.username
                return (
                  <tr key={row.username} className={isMe ? 'bg-primary/10' : ''}>
                    <td className="text-gray-400 font-medium">
                      <div className="flex items-center gap-0.5">
                        <span>{row.rank === 1 ? '🥇' : row.rank === 2 ? '🥈' : row.rank === 3 ? '🥉' : i === entries.length - 1 ? '🐢' : row.rank}</span>
                        {row.rank_change === 'up'   && <TrendingUp size={12} className="text-green-500" />}
                        {row.rank_change === 'down' && <TrendingDown size={12} className="text-red-400" />}
                        {row.rank_change === 'same' && <MoveHorizontal size={12} className="text-gray-300" />}
                      </div>
                    </td>
                    <td>
                      <span className={`font-medium ${isMe ? 'text-primary' : 'text-gray-800'}`}>
                        {row.display_name || row.username}
                      </span>
                      {isMe && <span className="ml-1 text-xs text-gray-400">(you)</span>}
                      {row.streak?.length > 0 && (
                        <div className="flex gap-0.5 mt-0.5">
                          {row.streak.map((s, idx) => (
                            <span key={idx} className={`text-[9px] font-bold px-1 py-px rounded ${
                              s === 'W'  ? 'bg-green-100 text-green-700' :
                              s === 'L'  ? 'bg-red-100 text-red-700' :
                              s === 'N'  ? 'bg-yellow-100 text-yellow-700' :
                              s === '💀' ? 'bg-amber-100 text-amber-700' :
                              (s === '🛡' || s === '🧤') ? 'bg-purple-100 text-purple-700' :
                              'bg-gray-100 text-gray-400'
                            } ${idx === 0 ? (
                              s === 'W'  ? 'ring-1 ring-green-400' :
                              s === 'L'  ? 'ring-1 ring-red-400' :
                              s === 'N'  ? 'ring-1 ring-yellow-400' :
                              s === '💀' ? 'ring-1 ring-amber-400' :
                              (s === '🛡' || s === '🧤') ? 'ring-1 ring-purple-400' :
                              'ring-1 ring-gray-400'
                            ) : ''}`}>{s}</span>
                          ))}
                        </div>
                      )}
                    </td>
                    <td className="text-right font-bold text-gray-800">{row.total ?? 0}</td>
                    <td className="text-right text-success">{row.won ?? 0}</td>
                    <td className="text-right text-error">{row.lost ?? 0}</td>
                    <td className="text-right text-gray-400">{row.skipped ?? 0}</td>
                    <td className="text-right text-gray-600">{row.matches_won ?? 0}</td>
                  </tr>
                )
              })}
              {!board?.entries?.length && (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-gray-400">
                    No data yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="text-xs text-gray-400 text-center">
        W = Points Won · L = Points Lost · S = Free Skips (max 5) · MW = Matches Won
      </div>

      {(() => {
        const displayNames = Object.fromEntries(
          (board?.entries ?? []).map(e => [e.username, e.display_name || e.username])
        )
        return historyLoading ? <Spinner /> : (
          <>
            <RankHistoryChart history={history} currentUsername={user?.username} displayNames={displayNames} />
            <PointsProgressionChart history={history} currentUsername={user?.username} displayNames={displayNames} />
          </>
        )
      })()}
    </div>
  )
}
