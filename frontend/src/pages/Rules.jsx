import { useQuery } from '@tanstack/react-query'
import { picksAPI } from '@/api/picks'
import useTournamentStore from '@/store/tournamentStore'

export default function Rules() {
  const { currentTournament } = useTournamentStore()
  const isSoccer = currentTournament?.sport === 'soccer'

  const { data: stats } = useQuery({
    queryKey: ['picks', 'stats'],
    queryFn: () => picksAPI.stats().then(r => r.data),
    staleTime: 5 * 60 * 1000,
  })
  const pickWindowDays = stats?.pick_window_days ?? 5

  const commonSections = [
    {
      title: '🎯 How to Pick',
      content: (
        <p className="text-sm text-gray-600">
          Go to the <strong>Schedule</strong> page to see upcoming matches. Tap a team to place your pick — it's saved instantly.
          You can switch sides any time before the match starts. Picks are locked at the official start time of the match.
          Matches open for picking within <strong>{pickWindowDays} days</strong> of the match start.
          {isSoccer && ' For group stage matches you can also pick a Draw.'}
        </p>
      ),
    },
    {
      title: '⏭️ Skipping a Match',
      content: (
        <p className="text-sm text-gray-600">
          You can skip up to <strong>5 matches</strong> per tournament — just don't place a pick.
          Skipped matches earn 0 points and appear on the Standings screen.
          Skipping more than 5 matches results in <strong>disqualification</strong> (score set to −999).
        </p>
      ),
    },
  ]

  const cricketSections = [
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
            <li>Most points won (gross points earned, before deductions)</li>
            <li>Most matches won</li>
            <li>Fewest PowerPlays used</li>
            <li>Head-to-head pick comparison</li>
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
  ]

  const soccerSections = [
    {
      title: '✖️ Match Point Values',
      content: (
        <ul className="space-y-1 text-sm text-gray-600">
          {[
            ['Group Stage', '1 point'],
            ['Round of 32', '2 points'],
            ['Round of 16', '3 points'],
            ['Quarter-final', '5 points'],
            ['Semi-final', '7 points'],
            ['Third Place', '7 points'],
            ['Final', '10 points'],
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
      title: '⚽ Draw Pick (group stage)',
      content: (
        <p className="text-sm text-gray-600">
          In group stage matches you can pick a <strong>Draw</strong> in addition to either team. Draw picks are not
          available from the Round of 32 onwards — knockout matches must have a winner.
        </p>
      ),
    },
    {
      title: '📈 How Points Work',
      content: (
        <>
          <p className="text-sm text-gray-600 mb-3">
            Soccer uses <strong>variable Base Points (BP)</strong> — the goal margin or total goals determine the stake.
            Points cancel out across pickers: the net sum per match is always 0 before powerups.
          </p>
          <div className="bg-gray-50 rounded-lg p-3 space-y-1.5 text-sm text-gray-600">
            <div className="font-medium text-gray-700">Base Points (BP) by result:</div>
            <div>⚽ <strong>Win:</strong> BP = PV × min(goal diff, 3) · min 1 (handles shootouts)</div>
            <div>⚖ <strong>Draw:</strong> BP = PV × (total goals + 1)</div>
            <div className="mt-2 font-medium text-gray-700">Net-zero scoring:</div>
            <div>✅ <strong>Correct pick:</strong> +BP × (rivals who picked wrong)</div>
            <div>❌ <strong>Wrong pick:</strong> −BP × (rivals who picked right)</div>
            <div>⏭️ <strong>Skip (group stage):</strong> 0 points (counts toward limit)</div>
          </div>
          <div className="mt-3 space-y-2 text-xs text-gray-500">
            <p><strong>Example (PV=1, 5 correct, 3 wrong):</strong></p>
            <p>Win 2–0: BP = 1×2 = 2 → correct: +2×3 = <strong>+6 each</strong>; wrong: −2×5 = <strong>−10 each</strong></p>
            <p>Draw 1–1: BP = 1×3 = 3 → draw pickers: +3×(others); others: −3×(draw pickers)</p>
            <p>Win on penalties (0–0 AET): BP = 1×1 = 1 (shootout treated as 1-goal margin)</p>
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
            <li>Most points won (gross points earned, before deductions)</li>
            <li>Most matches won</li>
            <li>Fewest PowerPlays used</li>
            <li>Head-to-head pick comparison</li>
            <li>Joint winners 🏆</li>
          </ol>
        </>
      ),
    },
    {
      title: '🏟️ Knockout Rules (R32 onwards)',
      content: (
        <ul className="space-y-1.5 text-sm text-gray-600">
          <li>• No draw pick available — you must pick a team to win</li>
          <li>• Picks are <strong>hidden by default</strong> — no one sees others' picks until kick-off</li>
          <li>• If you skip a knockout match, the <strong>losing team is auto-assigned</strong> as a penalty</li>
          <li>• Skipping a knockout match does <strong>not</strong> count toward your 5-skip limit</li>
          <li>• PowerPlays are <strong>not available from the Quarter-finals onwards</strong></li>
        </ul>
      ),
    },
    {
      title: '⚡ PowerPlays',
      subtitle: 'group stage & R32/R16 only · 5 of each per tournament',
      content: (
        <div className="space-y-3 text-sm text-gray-600">
          <div>
            <span className="font-medium">🕵️ Hidden</span>
            <p className="text-xs text-gray-500 mt-0.5">Hides your team selection from other players until kick-off.</p>
          </div>
          <div>
            <span className="font-medium">🪄 Dummy</span>
            <p className="text-xs text-gray-500 mt-0.5">Shows others a decoy pick (you choose which team or draw they see). Your real pick is revealed at kick-off.</p>
          </div>
          <div>
            <span className="font-medium">🧤 Clean Sheet</span>
            <p className="text-xs text-gray-500 mt-0.5">If your pick loses, you lose 0 points instead of the penalty.</p>
          </div>
          <div className="pt-2 border-t border-gray-200 space-y-1 text-xs text-gray-500">
            <p><strong>Mobile:</strong> Tap a PowerPlay chip at the top of the Schedule page, then tap the match to apply it.</p>
            <p><strong>Desktop:</strong> Drag a PowerPlay chip onto a match card, or tap the PowerPlay buttons on the card directly.</p>
            <p>Only one PowerPlay per pick. Can be changed or removed before the match starts.</p>
          </div>
        </div>
      ),
    },
  ]

  const notificationSection = {
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
          <p className="text-xs text-gray-500 mb-1.5">Push notifications on iOS require TushFun to be installed as an app first:</p>
          <ol className="space-y-1 text-xs text-gray-500 list-decimal list-inside">
            <li>Open TushFun in Safari</li>
            <li>Tap the <strong>Share</strong> button (box with arrow ↑) at the bottom</li>
            <li>Tap <strong>Add to Home Screen</strong></li>
            <li>Open TushFun from your Home Screen</li>
            <li>Go to <strong>Profile → Notifications</strong> and toggle on</li>
          </ol>
        </div>

        <p className="text-xs text-gray-400 pt-1 border-t border-gray-200">
          You receive: pick result after each match, rank #1 change alerts, and pick reminders at 24h and 1h before each match locks.
        </p>
      </div>
    ),
  }

  const ruleChangeSection = {
    title: '📜 Rule Changes',
    content: (
      <p className="text-sm text-gray-600">Any rule changes during the tournament require a majority vote from all players.</p>
    ),
  }

  const sportSections = isSoccer ? soccerSections : cricketSections
  const sections = [...commonSections, ...sportSections, notificationSection, ruleChangeSection]

  return (
    <div className="space-y-3">
      <h1 className="text-xl font-bold text-gray-800">Game Rules</h1>
      {currentTournament && (
        <p className="text-xs text-gray-400">
          {isSoccer ? '⚽' : '🏏'} {currentTournament.name}
          {currentTournament.season && ` · ${currentTournament.season}`}
        </p>
      )}

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
