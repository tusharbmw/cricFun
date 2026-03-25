import { useQuery } from '@tanstack/react-query'
import {
  CartesianGrid, Line, LineChart, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from 'recharts'
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

function RankHistoryChart({ history, currentUsername }) {
  if (!history?.length) return <ChartEmptyState />

  // All usernames that appear in any snapshot
  const allUsers = [...new Set(
    history.flatMap(snap => snap.rankings.map(r => r.username))
  )]
  const totalUsers = allUsers.length

  // Transform API shape → recharts shape: [{label, full_label, alice: 1, bob: 2, ...}]
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
            formatter={(value, name) => [`#${value}`, name]}
            labelFormatter={(_, payload) => payload?.[0]?.payload?.full_label ?? ''}
            contentStyle={{ fontSize: 12 }}
          />
          {allUsers.map(username => {
            const isMe = username === currentUsername
            return (
              <Line
                key={username}
                type="monotone"
                dataKey={username}
                stroke={isMe ? '#2563eb' : '#d1d5db'}
                strokeWidth={isMe ? 2.5 : 1}
                dot={isMe ? { r: 3, fill: '#2563eb' } : false}
                activeDot={{ r: isMe ? 5 : 3 }}
                connectNulls
              />
            )
          })}
        </LineChart>
      </ResponsiveContainer>
      <p className="text-xs text-gray-400 text-center mt-1">
        Your line is highlighted in blue · Rank 1 = top
      </p>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Points progression line chart
// ---------------------------------------------------------------------------

function PointsProgressionChart({ history, currentUsername }) {
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
            formatter={(value, name) => [value, name]}
            labelFormatter={(_, payload) => payload?.[0]?.payload?.full_label ?? ''}
            contentStyle={{ fontSize: 12 }}
          />
          {allUsers.map(username => {
            const isMe = username === currentUsername
            return (
              <Line
                key={username}
                type="monotone"
                dataKey={username}
                stroke={isMe ? '#2563eb' : '#d1d5db'}
                strokeWidth={isMe ? 2.5 : 1}
                dot={isMe ? { r: 3, fill: '#2563eb' } : false}
                activeDot={{ r: isMe ? 5 : 3 }}
                connectNulls
              />
            )
          })}
        </LineChart>
      </ResponsiveContainer>
      <p className="text-xs text-gray-400 text-center mt-1">
        Your line is highlighted in blue · Higher = more points
      </p>
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
      <h1 className="text-xl font-bold text-gray-800">Standings</h1>

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
                <th className="text-right">Pts</th>
              </tr>
            </thead>
            <tbody>
              {board?.map((row, i) => {
                const isMe = row.username === user?.username
                return (
                  <tr key={row.username} className={isMe ? 'bg-primary/10' : ''}>
                    <td className="text-gray-400 font-medium">
                      {i < 3 ? ['🥇','🥈','🥉'][i] : i + 1}
                    </td>
                    <td>
                      <span className={`font-medium ${isMe ? 'text-primary' : 'text-gray-800'}`}>
                        {row.display_name || row.username}
                      </span>
                      {isMe && <span className="ml-1 text-xs text-gray-400">(you)</span>}
                    </td>
                    <td className="text-right text-success">{row.won ?? 0}</td>
                    <td className="text-right text-error">{row.lost ?? 0}</td>
                    <td className="text-right text-gray-400">{row.skipped ?? 0}</td>
                    <td className="text-right font-bold text-gray-800">{row.total ?? 0}</td>
                  </tr>
                )
              })}
              {!board?.length && (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-gray-400">
                    No data yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="text-xs text-gray-400 text-center">
        W = Won · L = Lost · S = Skipped
      </div>

      {/* Rank progression chart */}
      {historyLoading
        ? <Spinner />
        : <RankHistoryChart history={history} currentUsername={user?.username} />
      }

      {/* Points progression chart */}
      {historyLoading
        ? <Spinner />
        : <PointsProgressionChart history={history} currentUsername={user?.username} />
      }
    </div>
  )
}
