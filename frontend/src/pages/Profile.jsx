import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { authAPI } from '@/api/auth'
import { picksAPI } from '@/api/picks'
import { leaderboardAPI } from '@/api/leaderboard'
import useAuthStore from '@/store/authStore'
import Spinner from '@/components/ui/Spinner'
import { usePush } from '@/hooks/usePush'

export default function Profile() {
  const { user, logout, setUser } = useAuthStore()

  const { data: stats } = useQuery({
    queryKey: ['picks', 'stats'],
    queryFn: () => picksAPI.stats().then(r => r.data),
  })

  const { data: myRank } = useQuery({
    queryKey: ['leaderboard', 'me'],
    queryFn: () => leaderboardAPI.me().then(r => r.data),
  })

  const { supported: pushSupported, subscribed, loading: pushLoading, denied, subscribe, unsubscribe } = usePush()

  const [editing, setEditing] = useState(false)
  const [displayName, setDisplayName] = useState(user?.first_name ?? '')
  const [saveError, setSaveError] = useState('')

  const { mutate: saveProfile, isPending: saving } = useMutation({
    mutationFn: (data) => authAPI.updateMe(data),
    onSuccess: (response) => {
      setUser(response.data)
      setEditing(false)
    },
    onError: (err) => {
      setSaveError(err.response?.data?.detail ?? 'Failed to save')
    },
  })

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-gray-800">Profile</h1>

      {/* Identity */}
      <div className="bg-white border border-gray-100 rounded-xl shadow-sm">
        <div className="p-4">
          <div className="flex items-center gap-3">
            <div className="avatar placeholder">
              <div className="bg-neutral text-neutral-content rounded-full w-12">
                <span className="text-xl font-bold">{user?.username?.[0]?.toUpperCase() ?? '?'}</span>
              </div>
            </div>
            <div>
              <div className="font-semibold text-gray-800">{user?.username}</div>
              <div className="text-sm text-gray-500">{user?.email}</div>
            </div>
          </div>

          {editing ? (
            <div className="mt-4 space-y-3">
              <div className="form-control">
                <label className="label py-1">
                  <span className="label-text text-xs">Display name</span>
                </label>
                <input
                  type="text"
                  value={displayName}
                  onChange={e => setDisplayName(e.target.value)}
                  className="input input-sm input-bordered w-full"
                />
              </div>
              {saveError && <p className="text-xs text-error">{saveError}</p>}
              <div className="flex gap-2">
                <button
                  onClick={() => saveProfile({ first_name: displayName })}
                  disabled={saving}
                  className="btn btn-sm btn-primary"
                >
                  {saving ? <span className="loading loading-spinner loading-xs" /> : 'Save'}
                </button>
                <button onClick={() => setEditing(false)} className="btn btn-sm btn-ghost">
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <button onClick={() => setEditing(true)} className="mt-2 btn btn-xs btn-ghost self-start">
              Edit profile
            </button>
          )}
        </div>
      </div>

      {/* Stats */}
      <div className="bg-white border border-gray-100 rounded-xl shadow-sm">
        <div className="p-4">
          <h2 className="font-semibold text-gray-600 mb-3 text-sm uppercase tracking-wider">Season stats</h2>
          <div className="stats stats-horizontal bg-gray-50 shadow w-full flex-wrap">
            {[
              { label: 'Rank',    value: myRank ? `#${myRank.rank}` : '–' },
              { label: 'Points',  value: myRank?.total ?? '–' },
              { label: 'Won',     value: myRank?.won ?? '–' },
              { label: 'Lost',    value: myRank?.lost ?? '–' },
              { label: 'Skipped', value: myRank?.skipped ?? '–' },
              { label: 'Missing', value: stats?.missing_picks ?? '–' },
            ].map(({ label, value }) => (
              <div key={label} className="stat place-items-center py-3">
                <div className="stat-value text-lg text-primary">{value}</div>
                <div className="stat-desc text-xs">{label}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Powerups */}
      {stats && !stats.powerups_disabled && (
        <div className="bg-white border border-gray-100 rounded-xl shadow-sm">
          <div className="p-4">
            <h2 className="font-semibold text-gray-600 mb-3 text-sm uppercase tracking-wider">PowerPlays remaining</h2>
            <div className="stats stats-horizontal bg-gray-50 shadow w-full">
              {[
                { label: '🕵️ Hidden',  key: 'hidden_count' },
                { label: '🃏 Googly',  key: 'fake_count' },
                { label: '🛡️ The Wall', key: 'no_negative_count' },
              ].map(({ label, key }) => (
                <div key={key} className="stat place-items-center py-3">
                  <div className="stat-value text-lg text-secondary">{stats[key] ?? 0}</div>
                  <div className="stat-desc text-xs">{label}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Push notifications */}
      {pushSupported && (
        <div className="bg-white border border-gray-100 rounded-xl shadow-sm">
          <div className="p-4">
            <h2 className="font-semibold text-gray-600 mb-3 text-sm uppercase tracking-wider">Notifications</h2>
            {denied ? (
              <p className="text-sm text-gray-500">
                Push notifications are blocked in your browser settings. Enable them to receive match updates.
              </p>
            ) : (
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-sm font-medium text-gray-800">Push notifications</p>
                  <p className="text-xs text-gray-400 mt-0.5">Match results &amp; leaderboard changes</p>
                </div>
                <input
                  type="checkbox"
                  className="toggle toggle-primary"
                  checked={subscribed}
                  disabled={pushLoading}
                  onChange={() => subscribed ? unsubscribe() : subscribe()}
                />
              </div>
            )}
          </div>
        </div>
      )}

      {/* Logout */}
      <button
        onClick={() => logout()}
        className="btn btn-outline btn-error w-full"
      >
        Sign out
      </button>
    </div>
  )
}
