import { useEffect, useRef, useState } from 'react'
import { NavLink, Link } from 'react-router-dom'
import { Bell } from 'lucide-react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { formatDistanceToNow } from 'date-fns'
import useAuthStore from '@/store/authStore'
import { picksAPI } from '@/api/picks'
import { notificationsAPI } from '@/api/notifications'

const navLinks = [
  { to: '/',          label: 'Home',      end: true },
  { to: '/schedule',  label: 'Schedule' },
  { to: '/results',   label: 'Results' },
  { to: '/standings', label: 'Standings' },
  { to: '/rules',     label: 'Rules' },
]

// ---------------------------------------------------------------------------
// Notification dropdown
// ---------------------------------------------------------------------------

function NotificationDropdown({ onClose }) {
  const qc = useQueryClient()

  const { data: notifications } = useQuery({
    queryKey: ['notifications', 'list'],
    queryFn: () => notificationsAPI.list().then(r => r.data),
  })

  // Auto mark-as-read when dropdown opens
  useEffect(() => {
    notificationsAPI.markRead().then(() => {
      qc.invalidateQueries({ queryKey: ['notifications', 'unread'] })
      qc.invalidateQueries({ queryKey: ['notifications', 'list'] })
    })
  }, [qc])

  return (
    <div
      className="absolute right-0 top-full mt-2 w-80 bg-white rounded-xl border border-gray-100 shadow-lg z-50 overflow-hidden"
      onClick={e => e.stopPropagation()}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
        <span className="text-sm font-semibold text-gray-800">Notifications</span>
        <div className="flex items-center gap-3">
          {notifications?.length > 0 && (
            <button
              onClick={() => {
                notificationsAPI.clear().then(() => {
                  qc.invalidateQueries({ queryKey: ['notifications'] })
                })
              }}
              className="text-xs text-red-400 hover:text-red-600"
            >
              Clear all
            </button>
          )}
          <button onClick={onClose} className="text-xs text-gray-400 hover:text-gray-600">✕</button>
        </div>
      </div>

      {/* List */}
      <div className="max-h-72 overflow-y-auto divide-y divide-gray-50">
        {!notifications?.length ? (
          <p className="text-sm text-gray-400 text-center py-8">No notifications yet</p>
        ) : (
          notifications.slice(0, 10).map(n => {
            const url = n.type === 'pick_result'
              ? `/results${n.meta?.match_id ? `?match=${n.meta.match_id}` : ''}`
              : n.type === 'custom'
                ? (n.meta?.url ?? '/')
                : '/standings'
            return (
              <div key={n.id} className={`flex items-start gap-2 px-4 py-3 group ${n.is_read ? '' : 'bg-blue-50/50'}`}>
                <Link
                  to={url}
                  onClick={onClose}
                  className="flex-1 min-w-0"
                >
                  <p className="text-sm text-gray-800 leading-snug">{n.message}</p>
                  <p className="text-xs text-gray-400 mt-0.5">
                    {formatDistanceToNow(new Date(n.created_at), { addSuffix: true })}
                  </p>
                </Link>
                <button
                  onClick={() => {
                    notificationsAPI.deleteOne(n.id).then(() =>
                      qc.invalidateQueries({ queryKey: ['notifications'] })
                    )
                  }}
                  className="shrink-0 text-gray-300 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity mt-0.5"
                >
                  ✕
                </button>
              </div>
            )
          })
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-2.5 border-t border-gray-100">
        <Link
          to="/standings"
          onClick={onClose}
          className="text-xs text-blue-600 hover:underline"
        >
          View standings →
        </Link>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Bell button (shared between mobile + desktop)
// ---------------------------------------------------------------------------

function BellButton({ missingCount, isUrgent, className }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  const { data: unreadData } = useQuery({
    queryKey: ['notifications', 'unread'],
    queryFn: () => notificationsAPI.unreadCount().then(r => r.data),
    staleTime: 60 * 1000,
    refetchInterval: 60 * 1000,
  })
  const unreadCount = unreadData?.count ?? 0

  // Close on outside click
  useEffect(() => {
    if (!open) return
    function handleClick(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [open])

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(v => !v)}
        className={`relative flex items-center justify-center text-gray-500 hover:bg-gray-50 ${className}`}
      >
        <Bell size={18} />
        {/* Amber badge: missing picks (actionable) */}
        {!isUrgent && missingCount > 0 && (
          <span className="absolute -top-1 -right-1 min-w-4.5 h-4.5 bg-amber-400 text-white text-[10px] font-medium rounded-full flex items-center justify-center border-2 border-white px-1">
            {missingCount}
          </span>
        )}
        {/* Blue dot: unread notifications (informational) */}
        {unreadCount > 0 && (
          <span className="absolute top-0 right-0 w-2 h-2 bg-blue-500 rounded-full border border-white" />
        )}
      </button>

      {open && <NotificationDropdown onClose={() => setOpen(false)} />}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Header
// ---------------------------------------------------------------------------

export default function Header() {
  const { user } = useAuthStore()

  const { data: stats } = useQuery({
    queryKey: ['picks', 'stats'],
    queryFn: () => picksAPI.stats().then(r => r.data),
    staleTime: 60 * 1000,
  })

  const missingCount = stats?.missing_picks ?? 0
  const urgent = stats?.urgent_missing_picks ?? 0
  const isUrgent = urgent > 0
  const name = user?.first_name || user?.username || ''
  const initial = user?.username?.[0]?.toUpperCase() ?? '?'

  return (
    <>
      {/* ── Mobile header ── */}
      <header className="md:hidden bg-white border-b border-gray-100 px-4 py-3 sticky top-0 z-50 shadow-sm">
        <div className="flex items-center justify-between">
          {/* Left: logo + brand + greeting */}
          <Link to="/" className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gray-900 flex items-center justify-center shrink-0"
              style={{ boxShadow: '0 0 0 2px #fbbf24' }}>
              <img src="/logo.PNG" alt="CricFun" className="w-7 h-7 object-contain rounded-full" />
            </div>
            <div>
              <div className="text-base font-medium text-indigo-500 leading-tight">CricFun</div>
              <div className="text-xs text-gray-500 leading-tight">Hey, {name}! 👋</div>
            </div>
          </Link>

          {/* Right: alert buttons */}
          <div className="flex items-center gap-2">
            {/* STATE 1: urgent → amber ⚠️ */}
            {isUrgent && (
              <Link to="/schedule"
                className="relative w-9 h-9 rounded-lg flex items-center justify-center text-base"
                style={{ background: '#FAEEDA' }}>
                ⚠️
                <span className="absolute -top-1 -right-1 min-w-4.5 h-4.5 bg-red-500 text-white text-[10px] font-medium rounded-full flex items-center justify-center border-2 border-white px-1">
                  {urgent}
                </span>
              </Link>
            )}

            <BellButton
              missingCount={missingCount}
              isUrgent={isUrgent}
              className="w-9 h-9 rounded-lg border border-gray-200"
            />

            <Link to="/profile" className="w-9 h-9 rounded-lg border border-gray-200 flex items-center justify-center text-sm font-semibold text-gray-600">
              {initial}
            </Link>
          </div>
        </div>
      </header>

      {/* ── Desktop header ── */}
      <header className="hidden md:block bg-white border-b border-gray-100 sticky top-0 z-50 shadow-sm">
        <div className="max-w-400 mx-auto px-10 py-4 flex items-center justify-between">
          {/* Left: logo + brand + nav */}
          <div className="flex items-center gap-12">
            <Link to="/" className="flex items-center gap-3 shrink-0">
              <div className="w-10 h-10 rounded-full bg-gray-900 flex items-center justify-center"
                style={{ boxShadow: '0 0 0 2px #fbbf24' }}>
                <img src="/logo.PNG" alt="CricFun" className="w-7 h-7 object-contain rounded-full" />
              </div>
              <span className="text-lg font-medium text-indigo-500">CricFun</span>
            </Link>

            <nav className="flex gap-1">
              {navLinks.map(({ to, label, end }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={end}
                  className={({ isActive }) =>
                    `relative px-5 py-2.5 rounded-lg text-[15px] transition ${
                      isActive
                        ? 'bg-blue-50 text-blue-900 font-medium'
                        : 'text-gray-500 hover:bg-gray-50'
                    }`
                  }
                >
                  {({ isActive }) => (
                    <>
                      {label}
                      {label === 'Schedule' && missingCount > 0 && !isActive && (
                        <span className="absolute top-2 right-3 w-1.75 h-1.75 bg-red-500 rounded-full border border-white" />
                      )}
                    </>
                  )}
                </NavLink>
              ))}
            </nav>
          </div>

          {/* Right: alert badge + bell + avatar */}
          <div className="flex items-center gap-3">
            {/* STATE 1: amber alert badge */}
            {isUrgent && (
              <Link to="/schedule"
                className="flex items-center gap-2.5 rounded-lg px-4 py-2.5"
                style={{ background: '#FAEEDA', border: '1px solid #f59e0b' }}>
                <span>⚠️</span>
                <span className="text-sm font-medium" style={{ color: '#633806' }}>{urgent} urgent</span>
              </Link>
            )}

            <BellButton
              missingCount={missingCount}
              isUrgent={isUrgent}
              className="w-10 h-10 rounded-lg border border-gray-200"
            />

            <Link
              to="/profile"
              className="w-10 h-10 rounded-full flex items-center justify-center font-medium text-[15px] cursor-pointer"
              style={{ background: '#E6F1FB', color: '#0C447C' }}
            >
              {initial}
            </Link>
          </div>
        </div>
      </header>
    </>
  )
}
