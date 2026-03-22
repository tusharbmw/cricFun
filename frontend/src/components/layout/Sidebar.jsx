import useAuthStore from '@/store/authStore'

const BOOSTERS = [
  {
    type: 'hidden',
    emoji: '🕵️',
    label: 'Hidden',
    desc: 'Conceal your pick',
    key: 'hidden_count',
    bg: '#EEEDFE', border: '#AFA9EC', nameColor: '#3C3489', descColor: '#534AB7', countColor: '#3C3489',
  },
  {
    type: 'fake',
    emoji: '🎭',
    label: 'Googly',
    desc: 'Show decoy pick',
    key: 'fake_count',
    bg: '#FBEAF0', border: '#ED93B1', nameColor: '#72243E', descColor: '#993556', countColor: '#72243E',
  },
  {
    type: 'no_negative',
    emoji: '🛡️',
    label: 'The Wall',
    desc: 'No point loss',
    key: 'no_negative_count',
    bg: '#E1F5EE', border: '#5DCAA5', nameColor: '#085041', descColor: '#0F6E56', countColor: '#085041',
  },
]

export default function Sidebar({ myRank, stats, onDragStart, selectedBooster, onSelectBooster }) {
  const { user } = useAuthStore()
  const name = user?.first_name || user?.username || ''

  const skipped = myRank?.skipped ?? 0
  const winRate = myRank && (myRank.won + myRank.lost) > 0
    ? Math.round(myRank.won / (myRank.won + myRank.lost) * 100)
    : 0

  return (
    <div className="space-y-5 sticky top-24">
      {/* Stats card */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6">
        <p className="text-sm text-gray-500 mb-1">Welcome back</p>
        <p className="text-xl font-medium text-gray-800 mb-5">{name}</p>

        <div className="grid grid-cols-2 gap-4 mb-5">
          <div className="text-center">
            <p className="text-xs text-gray-500 mb-1.5">Rank</p>
            <p className="text-4xl font-medium text-blue-500">{myRank ? `#${myRank.rank}` : '–'}</p>
          </div>
          <div className="text-center">
            <p className="text-xs text-gray-500 mb-1.5">Points</p>
            <p className="text-4xl font-medium text-gray-800">{myRank?.total ?? '–'}</p>
          </div>
        </div>

        <div className="border-t border-gray-100 pt-4 space-y-2.5">
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-500">Closed skips</span>
            <span className="text-sm font-medium" style={{ color: skipped > 3 ? '#f59e0b' : '#1f2937' }}>
              {myRank ? `${skipped}/5` : '–'}
            </span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-500">Win rate</span>
            <span className="text-sm font-medium text-gray-800">{myRank ? `${winRate}%` : '–'}</span>
          </div>
          {(stats?.missing_picks ?? 0) > 0 && (
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-500">Missing picks</span>
              <span className="text-sm font-medium text-amber-500">{stats.missing_picks}</span>
            </div>
          )}
        </div>
      </div>

      {/* PowerPlays card */}
      {stats && !stats.powerups_disabled && (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
          <div className="flex items-center justify-between mb-4">
            <span className="text-[15px] font-medium text-gray-800">PowerPlays</span>
            <span className="text-xs text-gray-400">
              {selectedBooster ? 'Drop or tap a match' : 'Drag or tap to select'}
            </span>
          </div>
          <div className="space-y-3">
            {BOOSTERS.map(({ type, emoji, label, desc, key, bg, border, nameColor, descColor, countColor }) => {
              const count = stats?.[key] ?? 0
              const isSelected = selectedBooster === type
              return (
                <div
                  key={type}
                  draggable={count > 0}
                  onDragStart={count > 0 ? (e) => {
                    e.dataTransfer.setData('boosterType', type)
                    e.dataTransfer.effectAllowed = 'copy'
                    onDragStart?.(type)
                  } : undefined}
                  onClick={() => count > 0 && onSelectBooster?.(isSelected ? null : type)}
                  className={`flex items-center gap-3 p-3 rounded-lg border-2 transition-all ${
                    count > 0 ? 'cursor-pointer active:scale-[0.98]' : 'opacity-40 cursor-not-allowed'
                  } ${isSelected ? '' : 'border-dashed'}`}
                  style={{
                    background: bg,
                    borderColor: border,
                    outline: isSelected ? `2px solid ${nameColor}` : 'none',
                    outlineOffset: '2px',
                  }}
                >
                  <span className="text-xl">{emoji}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium leading-tight" style={{ color: nameColor }}>{label}</p>
                    <p className="text-xs leading-tight" style={{ color: descColor }}>{desc}</p>
                  </div>
                  <span className="text-base font-medium" style={{ color: countColor }}>{count}</span>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
