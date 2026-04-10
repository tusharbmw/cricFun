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
  const [hoveredUser, setHoveredUser] = useState(null)
  const [pinnedUser, setPinnedUser]   = useState(null)
  const activeUser = pinnedUser ?? hoveredUser

  if (!history?.length) return <ChartEmptyState />

  const allUsers = [...new Set(
    history.flatMap(snap => snap.rankings.map(r => r.username))
  )]
  const totalUsers = allUsers.length

  const chartData = history.map(snap => {
    const point = { label: snap.label, full_label: snap.full_label }
    snap.rankings.forEach(r => { point[r.username] = r.rank })
    return point
  })

  return (
    <div className="bg-white border border-gray-100 rounded-xl shadow-sm p-4">
      <h2 className="text-sm font-semibold text-gray-700 mb-4">Rank Progression</h2>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={chartData} margin={{ top: 4, right: 16, bottom: 48, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 10, fill: '#9ca3af' }}
            interval={0}
            angle={-35}
            textAnchor="end"
          />
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
            const isMe = username === currentUsername
            const isActive = activeUser === username
            const dimmed = activeUser && !isActive
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
  const [hoveredUser, setHoveredUser] = useState(null)
  const [pinnedUser, setPinnedUser]   = useState(null)
  const activeUser = pinnedUser ?? hoveredUser

  if (!history?.length) return <ChartEmptyState />

  const allUsers = [...new Set(
    history.flatMap(snap => snap.rankings.map(r => r.username))
  )]

  const chartData = history.map(snap => {
    const point = { label: snap.label, full_label: snap.full_label }
    snap.rankings.forEach(r => { point[r.username] = r.total })
    return point
  })

  return (
    <div className="bg-white border border-gray-100 rounded-xl shadow-sm p-4">
      <h2 className="text-sm font-semibold text-gray-700 mb-4">Points Progression</h2>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={chartData} margin={{ top: 4, right: 16, bottom: 48, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 10, fill: '#9ca3af' }}
            interval={0}
            angle={-35}
            textAnchor="end"
          />
          <YAxis
            allowDecimals={false}
            tick={{ fontSize: 11, fill: '#6b7280' }}
            label={{ value: 'Points', angle: -90, position: 'insideLeft', fontSize: 11, fill: '#9ca3af' }}
          />
          <Tooltip
            formatter={(value, name) => [value, displayNames?.[name] || name]}
            labelFormatter={(_, payload) => payload?.[0]?.payload?.full_label ?? ''}
            contentStyle={{ fontSize: 12 }}
          />
          {allUsers.map(username => {
            const isMe = username === currentUsername
            const isActive = activeUser === username
            const dimmed = activeUser && !isActive
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

  const { data: board, isLoading } = useQuery({
    queryKey: ['leaderboard'],
    queryFn: () => leaderboardAPI.global().then(r => r.data),
    staleTime: 60000,
  })

  const { data: history, isLoading: historyLoading } = useQuery({
    queryKey: ['leaderboard', 'history'],
    queryFn: () => leaderboardAPI.history().then(r => r.data),
    staleTime: 5 * 60 * 1000,
  })

  if (isLoading) return <Spinner />

  return (
    <div className="space-y-4">
      <div className="flex items-baseline justify-between gap-2 flex-wrap">
        <h1 className="text-xl font-bold text-gray-800">Standings</h1>
        {board && (
          <span className="text-xs text-gray-400">
            <span className="font-medium text-gray-600">{board.matches_completed}</span> of{' '}
            <span className="font-medium text-gray-600">{board.matches_total}</span> matches completed
          </span>
        )}
      </div>

      {/* Standings table */}
      <div className="bg-white border border-gray-100 rounded-xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="table table-sm w-full">
            <thead>
              <tr className="text-gray-500 text-xs uppercase tracking-wider">
                <th className="w-10">#</th>
                <th>Player</th>
                <th className="text-right">W</th>
                <th className="text-right">L</th>
                <th className="text-right">S</th>
                <th className="text-right">MW</th>
                <th className="text-right">Pts</th>
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
                        <span>{i < 3 ? ['🥇','🥈','🥉'][i] : i === entries.length - 1 ? '🐢' : i + 1}</span>
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
                              s === 'W' ? 'bg-green-100 text-green-700' :
                              s === 'L' ? 'bg-red-100 text-red-700' :
                              s === 'N' ? 'bg-yellow-100 text-yellow-700' :
                              'bg-gray-100 text-gray-400'
                            }`}>{s}</span>
                          ))}
                        </div>
                      )}
                    </td>
                    <td className="text-right text-success">{row.won ?? 0}</td>
                    <td className="text-right text-error">{row.lost ?? 0}</td>
                    <td className="text-right text-gray-400">{row.skipped ?? 0}</td>
                    <td className="text-right text-gray-600">{row.matches_won ?? 0}</td>
                    <td className="text-right font-bold text-gray-800">{row.total ?? 0}</td>
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
        W = Points Won · L = Points Lost · S = Skipped · MW = Matches Won
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
