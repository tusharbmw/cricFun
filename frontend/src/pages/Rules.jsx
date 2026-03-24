import { useQuery } from '@tanstack/react-query'
import { picksAPI } from '@/api/picks'

export default function Rules() {
  const { data: stats } = useQuery({
    queryKey: ['picks', 'stats'],
    queryFn: () => picksAPI.stats().then(r => r.data),
    staleTime: 5 * 60 * 1000,
  })
  const pickWindowDays = stats?.pick_window_days ?? 5

  const sections = [
    {
      title: '🎯 How to Pick',
      content: (
        <p className="text-sm text-gray-600">
          Go to the <strong>Schedule</strong> page to see upcoming matches. Tap a team to place your pick — it's saved instantly.
          You can switch sides any time before the match starts. Picks are locked at the official start time of the match.
          Matches open for picking within <strong>{pickWindowDays} days</strong> of the match start.
        </p>
      ),
    },
    {
      title: '⏭️ Skipping a Match',
      content: (
        <p className="text-sm text-gray-600">
          You can skip up to <strong>5 matches</strong> per tournament - just don't place a pick.
          Skipped matches earn 0 points and appear on the Standings screen.
          Skipping more than 5 matches results in <strong>disqualification</strong> (score set to −999).
        </p>
      ),
    },
    {
      title: '✖️ Match Point Values',
      content: (
        <ul className="space-y-1 text-sm text-gray-600">
          {[
            ['Group Stage', '1 point'],
            ['Super 8 (IPL)', '2 points'],
            ['Eliminator (IPL)', '2 points'],
            ['Qualifier 1 & 2 (IPL)', '3 points'],
            ['Semi-finals', '3 points'],
            ['Final', '5 points'],
          ].map(([stage, pts]) => (
            <li key={stage} className="flex justify-between">
              <span>{stage}</span>
              <span className="font-medium text-secondary">{pts}</span>
            </li>
          ))}
        </ul>
      ),
    },
    {
      title: '📈 How Points Work',
      content: (
        <>
          <p className="text-sm text-gray-600 mb-3">
            Your points go against everyone who picked the other side.
            Points are based on the match point value (PV) and the number of opponents on the losing side.
          </p>
          <div className="bg-gray-50 rounded-lg p-3 space-y-1 text-sm text-gray-600">
            <div>✅ <strong>Win:</strong> +PV × (opponents who picked the loser)</div>
            <div>❌ <strong>Loss:</strong> −PV × (opponents who picked the winner)</div>
            <div>⏭️ <strong>Skip:</strong> 0 points (counts toward 5-skip limit)</div>
            <div>🤝 <strong>Tie / No Result:</strong> 0 points for everyone</div>
            <div>🔄 <strong>All same side:</strong> 0 points — no one on the other side</div>
          </div>
          <div className="mt-3 space-y-2 text-xs text-gray-500">
            <p><strong>Example 1 (PV=1):</strong> X & Y pick Team A, Z picks Team B. Team A wins → X & Y each get +1, Z gets −2.</p>
            <p><strong>Example 2 (PV=2):</strong> X picks Team C, Y & Z pick Team D. Team C wins → X gets +4, Y & Z each get −2.</p>
          </div>
        </>
      ),
    },
    {
      title: '🏆 Winner & Tiebreaker',
      content: (
        <>
          <p className="text-sm text-gray-600 mb-2">Player with the highest points at the end of the tournament wins.</p>
          <p className="text-sm text-gray-500">Tiebreaker order:</p>
          <ol className="mt-1 space-y-1 text-sm text-gray-600 list-decimal list-inside">
            <li>Fewest skipped matches</li>
            <li>Most matches won</li>
            <li>Head to head pick comparison</li>
            <li>Joint winners 🏆</li>
          </ol>
        </>
      ),
    },
    {
      title: '🏟️ Playoff Rules',
      content: (
        <ul className="space-y-1.5 text-sm text-gray-600">
          <li>• Playoff picks are <strong>hidden by default</strong> — no one can see others' picks until the match starts</li>
          <li>• Skipping a playoff match does <strong>not</strong> count toward your 5-skip limit</li>
          <li>• If you skip a playoff match, the <strong>losing team is automatically assigned</strong> to you as a penalty after the result</li>
          <li>• PowerPlays are <strong>not available</strong> during playoffs</li>
        </ul>
      ),
    },
    {
      title: '⚡ PowerPlays',
      subtitle: 'regular season only · 5 of each per season',
      content: (
        <div className="space-y-3 text-sm text-gray-600">
          <div>
            <span className="font-medium">🕵️ Hidden</span>
            <p className="text-xs text-gray-500 mt-0.5">Hides your team selection from other players until the match starts.</p>
          </div>
          <div>
            <span className="font-medium">🃏 Googly</span>
            <p className="text-xs text-gray-500 mt-0.5">Shows other players a decoy pick. Your real pick is revealed when the match starts.</p>
          </div>
          <div>
            <span className="font-medium">🛡️ The Wall</span>
            <p className="text-xs text-gray-500 mt-0.5">If your pick loses, you lose 0 points instead of the penalty.</p>
          </div>
          <div className="pt-2 border-t border-gray-200 space-y-1 text-xs text-gray-500">
            <p><strong>Mobile:</strong> Tap a PowerPlay chip at the top of the Schedule page to select it, then tap the match you want to apply it to.</p>
            <p><strong>Desktop:</strong> Drag a PowerPlay chip from the left sidebar and drop it onto a match card. You can also tap the PowerPlay buttons directly on the card.</p>
            <p>Only one PowerPlay per pick. Can be changed or removed any time before the match starts.</p>
            <p>PowerPlays can only be applied to matches where you have already made a pick.</p>
          </div>
        </div>
      ),
    },
    {
      title: '🔔 Enabling Notifications',
      content: (
        <div className="space-y-3 text-sm text-gray-600">
          <p>Get push alerts for pick results, leaderboard changes, and reminders before picks lock.</p>

          <div>
            <p className="font-medium text-gray-700 mb-1">Android / Desktop (Chrome, Edge, Firefox)</p>
            <p className="text-xs text-gray-500">Go to <strong>Profile → Notifications</strong> and toggle on. Your browser will ask for permission — tap Allow.</p>
          </div>

          <div>
            <p className="font-medium text-gray-700 mb-1">iPhone / iPad (Safari)</p>
            <p className="text-xs text-gray-500 mb-1.5">Push notifications on iOS require CricFun to be installed as an app first:</p>
            <ol className="space-y-1 text-xs text-gray-500 list-decimal list-inside">
              <li>Open CricFun in Safari</li>
              <li>Tap the <strong>Share</strong> button (box with arrow ↑) at the bottom</li>
              <li>Tap <strong>Add to Home Screen</strong></li>
              <li>Open CricFun from your Home Screen</li>
              <li>Go to <strong>Profile → Notifications</strong> and toggle on</li>
            </ol>
          </div>

          <p className="text-xs text-gray-400 pt-1 border-t border-gray-200">
            You receive: pick result after each match, rank #1 change alerts, and pick reminders at 24h and 1h before each match locks.
          </p>
        </div>
      ),
    },
    {
      title: '📜 Rule Changes',
      content: (
        <p className="text-sm text-gray-600">Any rule changes during the tournament require a majority vote from all players.</p>
      ),
    },
  ]

  return (
    <div className="space-y-3">
      <h1 className="text-xl font-bold text-gray-800">Game Rules</h1>

      {sections.map(({ title, subtitle, content }) => (
        <div key={title} className="bg-white border border-gray-100 rounded-xl shadow-sm">
          <div className="p-4">
            <h2 className="font-semibold text-gray-800 mb-2">
              {title}
              {subtitle && <span className="text-xs text-gray-400 font-normal ml-2">({subtitle})</span>}
            </h2>
            {content}
          </div>
        </div>
      ))}
    </div>
  )
}
