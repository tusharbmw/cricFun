/**
 * Derived from decimal odds stored in Match.odds.
 * Used in Schedule (compact) and MatchDetail (full).
 */

function impliedProbs(odds) {
  if (!odds) return null
  const entries = [
    { key: 'team1', val: odds.team1 },
    { key: 'draw',  val: odds.draw  },
    { key: 'team2', val: odds.team2 },
  ].filter(e => e.val && e.val > 1)

  if (entries.length < 2) return null

  const raws = entries.map(e => ({ key: e.key, raw: 1 / e.val }))
  const total = raws.reduce((s, e) => s + e.raw, 0)
  return Object.fromEntries(raws.map(e => [e.key, Math.round((e.raw / total) * 100)]))
}

// ─── Compact bar for Schedule ────────────────────────────────────────────────

export function OddsBarCompact({ odds, team1Name, team2Name }) {
  const probs = impliedProbs(odds)
  if (!probs) return null

  const segments = [
    { key: 'team1', label: team1Name, pct: probs.team1, barColor: '#93C5FD', textColor: '#1d4ed8' },
    ...(probs.draw != null ? [{ key: 'draw', label: 'Draw', pct: probs.draw, barColor: '#FCD34D', textColor: '#b45309' }] : []),
    { key: 'team2', label: team2Name, pct: probs.team2, barColor: '#6EE7B7', textColor: '#047857' },
  ]

  const last = segments[segments.length - 1]

  return (
    <div className="mt-2">
      {/* Bar */}
      <div className="flex h-2 rounded-full overflow-hidden gap-px">
        {segments.map(s => (
          <div key={s.key} style={{ width: `${s.pct}%`, background: s.barColor }} />
        ))}
      </div>
      {/* Labels */}
      <div className="flex justify-between mt-1.5">
        <span className="flex items-center gap-1 text-[10px] font-medium" style={{ color: segments[0].textColor }}>
          <span className="inline-block w-2 h-2 rounded-sm shrink-0" style={{ background: segments[0].barColor }} />
          {segments[0].label} {segments[0].pct}%
        </span>
        {probs.draw != null && (
          <span className="flex items-center gap-1 text-[10px] font-medium" style={{ color: segments[1].textColor }}>
            <span className="inline-block w-2 h-2 rounded-sm shrink-0" style={{ background: segments[1].barColor }} />
            Draw {probs.draw}%
          </span>
        )}
        <span className="flex items-center gap-1 text-[10px] font-medium" style={{ color: last.textColor }}>
          {last.pct}% {last.label}
          <span className="inline-block w-2 h-2 rounded-sm shrink-0" style={{ background: last.barColor }} />
        </span>
      </div>
    </div>
  )
}

// ─── Full card for MatchDetail ────────────────────────────────────────────────

function ProbBar({ label, pct, color, bgColor }) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-sm text-gray-600 w-24 shrink-0 truncate">{label}</span>
      <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ background: '#f3f4f6' }}>
        <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="text-sm font-medium w-10 text-right" style={{ color: bgColor }}>{pct}%</span>
    </div>
  )
}

export function OddsCardFull({ odds, team1Name, team2Name }) {
  const probs = impliedProbs(odds)
  if (!probs || !odds) return null

  const hasTotals = odds.total_line != null && (odds.over_odds || odds.under_odds)
  const hasSpread = odds.spread_line != null && odds.spread_favored

  const overProb  = odds.over_odds  ? Math.round((1 / odds.over_odds)  / (1 / odds.over_odds + 1 / odds.under_odds) * 100) : null
  const underProb = odds.under_odds ? 100 - overProb : null

  const favored = hasSpread ? (odds.spread_favored === 'team1' ? team1Name : team2Name) : null

  const lastUpdated = odds.updated_at
    ? new Date(odds.updated_at).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', timeZone: 'UTC' }) + ' UTC'
    : null

  return (
    <div className="bg-white border border-gray-100 rounded-xl shadow-sm">
      <div className="p-4 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-gray-600">Pre-Match Odds</h2>
          {lastUpdated && (
            <span className="text-xs text-gray-400">Updated {lastUpdated}</span>
          )}
        </div>

        {/* Win probability */}
        <div className="space-y-2">
          <p className="text-xs font-medium text-gray-400 uppercase tracking-wide">Win Probability</p>
          <ProbBar label={team1Name} pct={probs.team1} color="#93C5FD" bgColor="#1e3a5f" />
          {probs.draw != null && (
            <ProbBar label="Draw" pct={probs.draw} color="#FCD34D" bgColor="#7c5005" />
          )}
          <ProbBar label={team2Name} pct={probs.team2} color="#6EE7B7" bgColor="#14532d" />
        </div>

        {/* Expected Total Goals */}
        {hasTotals && (
          <div className="border-t border-gray-100 pt-3 space-y-2">
            <p className="text-xs font-medium text-gray-400 uppercase tracking-wide">
              Expected Total Goals &nbsp;·&nbsp; O/U {odds.total_line}
            </p>
            {underProb != null && (
              <ProbBar label={`Under ${odds.total_line}`} pct={underProb} color="#C4B5FD" bgColor="#4c1d95" />
            )}
            {overProb != null && (
              <ProbBar label={`Over ${odds.total_line}`} pct={overProb} color="#F9A8D4" bgColor="#831843" />
            )}
          </div>
        )}

        {/* Expected Goal Difference */}
        {hasSpread && odds.spread_line > 0 && (
          <div className="border-t border-gray-100 pt-3">
            <p className="text-xs font-medium text-gray-400 uppercase tracking-wide mb-1">Expected Goal Difference</p>
            <p className="text-sm text-gray-700">
              <span className="font-medium">{favored}</span> favored by ~{odds.spread_line} goal{odds.spread_line !== 1 ? 's' : ''}
            </p>
          </div>
        )}

        <p className="text-xs text-gray-300">Consensus across bookmakers · For information only</p>
      </div>
    </div>
  )
}
