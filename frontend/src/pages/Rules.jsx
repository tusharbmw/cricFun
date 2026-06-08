import { useQuery } from '@tanstack/react-query'
import { picksAPI } from '@/api/picks'
import useTournamentStore from '@/store/tournamentStore'

export default function Rules() {
  const { currentTournament } = useTournamentStore()
  const isSoccer = currentTournament?.sport === 'soccer'

  const { data: stats } = useQuery({
    queryKey: ['picks', 'stats', currentTournament?.id],
    queryFn: () => picksAPI.stats({ tournament: currentTournament?.id }).then(r => r.data),
    enabled: !!currentTournament?.id,
    staleTime: 5 * 60 * 1000,
  })
  const pickWindowDays = stats?.pick_window_days ?? 5

  // ─── How it works ──────────────────────────────────────────────────────────

  const howItWorks = {
    title: '👋 How the Game Works',
    content: (
      <div className="space-y-2.5 text-sm text-gray-600">
        <p>
          Before each match, everyone picks who they think will win. Simple.
          The twist: <strong>your score depends on what everyone else picks</strong>.
        </p>
        <ul className="space-y-1.5 pl-1">
          <li>✅ Pick the winner → you earn points from every person who picked the loser</li>
          <li>❌ Pick the loser → you lose points to every person who picked the winner</li>
          <li>🤝 Everyone picks the same side → no points change hands</li>
        </ul>
        <p>
          The player with the <strong>most points at the end of the tournament wins</strong>.
          You can skip up to 5 matches — but skipping too many hurts your chances.
        </p>
        {isSoccer && (
          <p>
            In group stage matches you can also pick a <strong>Draw</strong> as a third option.
            From the Round of 32 onwards, there's no draw — you must pick a team.
          </p>
        )}
      </div>
    ),
  }

  // ─── Common sections ───────────────────────────────────────────────────────

  const pickingSection = {
    title: '📱 Making a Pick',
    content: (
      <div className="space-y-2 text-sm text-gray-600">
        <p>
          Go to the <strong>Schedule</strong> page, find an upcoming match, and tap a team to pick them.
          Your pick is saved instantly — you can change sides any time until the match kicks off.
        </p>
        <p className="text-xs text-gray-400">
          Picks open <strong>{pickWindowDays} days</strong> before each match and lock at the official start time.
        </p>
      </div>
    ),
  }

  const skippingSection = {
    title: '⏭️ Skipping a Match',
    content: (
      <div className="space-y-2 text-sm text-gray-600">
        <p>
          Don't feel like picking? You can skip — just leave a match without placing a pick.
          Skips earn <strong>0 points</strong> and you're allowed up to <strong>5 skips</strong> per tournament.
        </p>
        <p className="text-xs text-amber-600 font-medium">
          ⚠ Skipping more than 5 matches disqualifies you (score drops to −999).
        </p>
      </div>
    ),
  }

  // ─── Cricket-specific ──────────────────────────────────────────────────────

  const cricketPointsSection = {
    title: '✖️ Match Point Values',
    content: (
      <ul className="space-y-1 text-sm text-gray-600">
        {[
          ['Group Stage',              '1 point'],
          ['Super 8 (IPL)',            '2 points'],
          ['Eliminator (IPL)',         '2 points'],
          ['Qualifier 1 & 2 (IPL)',    '3 points'],
          ['Semi-finals',              '3 points'],
          ['Final',                    '5 points'],
        ].map(([stage, pts]) => (
          <li key={stage} className="flex justify-between">
            <span>{stage}</span>
            <span className="font-medium text-secondary">{pts}</span>
          </li>
        ))}
      </ul>
    ),
  }

  const cricketScoringSection = {
    title: '📈 How Points Are Calculated',
    content: (
      <>
        <p className="text-sm text-gray-600 mb-3">
          Every match has a <strong>Point Value (PV)</strong> based on its stage (see above).
          Your score changes by PV × the number of opponents who picked differently.
        </p>
        <div className="bg-gray-50 rounded-lg p-3 space-y-1 text-sm text-gray-600">
          <div>✅ <strong>Win:</strong> +PV × (opponents who picked the loser)</div>
          <div>❌ <strong>Loss:</strong> −PV × (opponents who picked the winner)</div>
          <div>⏭️ <strong>Skip:</strong> 0 points (counts toward 5-skip limit)</div>
          <div>🤝 <strong>Tie / No Result:</strong> 0 points for everyone</div>
          <div>🚫 <strong>Abandoned / No Result:</strong> match is voided — no points awarded or deducted for anyone</div>
        </div>
        <div className="mt-3 space-y-2 text-xs text-gray-500">
          <p><strong>Example (PV=1):</strong> Tushar & Raj pick Team A, Sam picks Team B. Team A wins → Tushar & Raj each get +1, Sam gets −2.</p>
        </div>
      </>
    ),
  }

  const cricketTiebreakerSection = {
    title: '🏆 Winner & Tiebreaker',
    content: (
      <>
        <p className="text-sm text-gray-600 mb-2">Highest points at the end wins.</p>
        <p className="text-sm text-gray-500">If it's a tie, this order decides:</p>
        <ol className="mt-1 space-y-1 text-sm text-gray-600 list-decimal list-inside">
          <li>Fewest skipped matches</li>
          <li>Most points earned (before deductions)</li>
          <li>Most matches won</li>
          <li>Fewest PowerPlays used</li>
          <li>Head-to-head pick comparison</li>
          <li>Joint winners 🏆</li>
        </ol>
      </>
    ),
  }

  const cricketPlayoffSection = {
    title: '🏟️ Playoff Rules',
    content: (
      <ul className="space-y-1.5 text-sm text-gray-600">
        <li>• Your pick is <strong>hidden from everyone</strong> — no one sees picks until the match starts</li>
        <li>• <strong>PowerPlays are not available</strong> in playoff matches</li>
        <li>• If you skip a playoff match, the <strong>losing team is automatically assigned to you</strong> as a penalty — you lose points as if you had picked the loser</li>
        <li>• Playoff skips do <strong>not</strong> count toward your 5-skip limit</li>
      </ul>
    ),
  }

  const cricketPowerplaysSection = {
    title: '⚡ PowerPlays',
    subtitle: 'regular season only · 5 of each per tournament',
    content: (
      <div className="space-y-3 text-sm text-gray-600">
        <p className="text-xs text-gray-500">Apply one PowerPlay per pick to get an edge. You can change or remove it any time before the match starts.</p>
        <div>
          <span className="font-medium">🕵️ Hidden</span>
          <p className="text-xs text-gray-500 mt-0.5">Others can't see which team you picked until the match starts.</p>
        </div>
        <div>
          <span className="font-medium">🃏 Googly</span>
          <p className="text-xs text-gray-500 mt-0.5">Everyone sees a fake pick from you. Your real pick is revealed when the match starts.</p>
        </div>
        <div>
          <span className="font-medium">🛡️ The Wall</span>
          <p className="text-xs text-gray-500 mt-0.5">If your pick loses, you lose <strong>0 points</strong> instead of the penalty.</p>
        </div>
        <div className="pt-2 border-t border-gray-200 space-y-1 text-xs text-gray-500">
          <p><strong>Mobile:</strong> Tap a PowerPlay chip at the top of the Schedule page, then tap the match to apply it.</p>
          <p><strong>Desktop:</strong> Drag a PowerPlay chip onto a match card, or tap the buttons on the card directly.</p>
        </div>
      </div>
    ),
  }

  const cricketSections = [
    cricketPointsSection,
    cricketScoringSection,
    cricketTiebreakerSection,
    cricketPlayoffSection,
    cricketPowerplaysSection,
  ]

  // ─── Soccer-specific ───────────────────────────────────────────────────────

  const soccerPointsSection = {
    title: '✖️ Match Point Values',
    content: (
      <ul className="space-y-1 text-sm text-gray-600">
        {[
          ['Group Stage',   '1 pt (PV=1)'],
          ['Round of 32',   '2 pts (PV=2)'],
          ['Round of 16',   '3 pts (PV=3)'],
          ['Quarter-final', '5 pts (PV=5)'],
          ['Semi-final',    '7 pts (PV=7)'],
          ['Third Place',   '7 pts (PV=7)'],
          ['Final',         '10 pts (PV=10)'],
        ].map(([stage, pts]) => (
          <li key={stage} className="flex justify-between">
            <span>{stage}</span>
            <span className="font-medium text-secondary">{pts}</span>
          </li>
        ))}
      </ul>
    ),
  }

  const soccerScoringSection = {
    title: '📈 How Points Are Calculated',
    content: (
      <>
        <p className="text-sm text-gray-600 mb-3">
          Soccer scoring uses <strong>variable Base Points (BP)</strong> — a bigger win or more goals means higher stakes for everyone.
        </p>
        <div className="bg-gray-50 rounded-lg p-3 space-y-1.5 text-sm text-gray-600">
          <div className="font-medium text-gray-700">Base Points (BP):</div>
          <div>⚽ <strong>Win:</strong> PV × goal difference (min 1, max 3 goals counted)</div>
          <div>⚖ <strong>Draw:</strong> PV × (total goals + 1)</div>
          <div className="mt-2 font-medium text-gray-700">Your score:</div>
          <div>✅ <strong>Correct pick:</strong> +BP × (opponents who picked wrong)</div>
          <div>❌ <strong>Wrong pick:</strong> −BP × (opponents who picked right)</div>
          <div>🚫 <strong>Abandoned / No Result:</strong> match is voided — no points awarded or deducted for anyone</div>
        </div>
        <div className="mt-3 space-y-1.5 text-xs text-gray-500">
          <p><strong>Example (PV=1):</strong> England win 2–0. Goal diff = 2, so BP = 2.</p>
          <p>5 picked England, 3 picked Germany → England pickers: +2×3 = <strong>+6 each</strong>; Germany pickers: −2×5 = <strong>−10 each</strong>.</p>
          <p>Win on penalties (0–0 after extra time): BP = 1 × 1 = 1 (treated as 1-goal margin).</p>
        </div>
      </>
    ),
  }

  const soccerTiebreakerSection = {
    title: '🏆 Winner & Tiebreaker',
    content: (
      <>
        <p className="text-sm text-gray-600 mb-2">Highest points at the end wins.</p>
        <p className="text-sm text-gray-500">If it's a tie, this order decides:</p>
        <ol className="mt-1 space-y-1 text-sm text-gray-600 list-decimal list-inside">
          <li>Fewest skipped matches</li>
          <li>Most points earned (before deductions)</li>
          <li>Most matches won</li>
          <li>Fewest PowerPlays used</li>
          <li>Head-to-head pick comparison</li>
          <li>Joint winners 🏆</li>
        </ol>
      </>
    ),
  }

  const soccerKnockoutSection = {
    title: '🏟️ Knockout Rules',
    content: (
      <div className="space-y-4 text-sm text-gray-600">
        <div>
          <p className="font-medium text-gray-700 mb-1.5">Round of 32 & Round of 16</p>
          <ul className="space-y-1 text-sm text-gray-600">
            <li>• No draw pick — you must pick a team to win</li>
            <li>• PowerPlays are still available</li>
            <li>• Picks are visible to everyone (same as group stage)</li>
            <li>• Skipping is allowed and <strong>counts toward your 5-skip limit</strong> as normal</li>
          </ul>
        </div>
        <div className="border-t border-gray-100 pt-3">
          <p className="font-medium text-gray-700 mb-1.5">Quarter-finals, Semi-finals, Third Place & Final</p>
          <ul className="space-y-1 text-sm text-gray-600">
            <li>• No draw pick — you must pick a team to win</li>
            <li>• Your pick is <strong>automatically hidden</strong> — no one sees picks until the official kick-off time</li>
            <li>• <strong>PowerPlays are not available</strong> at this stage</li>
            <li>• If you skip, the <strong>losing team is auto-assigned</strong> to you as a penalty</li>
            <li>• These skips do <strong>not</strong> count toward your 5-skip limit</li>
          </ul>
        </div>
      </div>
    ),
  }

  const soccerPowerplaysSection = {
    title: '⚡ PowerPlays',
    subtitle: 'group stage, R32 & R16 only · 5 of each per tournament',
    content: (
      <div className="space-y-3 text-sm text-gray-600">
        <p className="text-xs text-gray-500">Apply one PowerPlay per pick. You can change or remove it any time before the official kick-off time. Not available from the Quarter-finals onwards.</p>
        <div>
          <span className="font-medium">🕵️ Hidden</span>
          <p className="text-xs text-gray-500 mt-0.5">Others can't see which team you picked until the official kick-off time.</p>
        </div>
        <div>
          <span className="font-medium">🪄 Dummy</span>
          <p className="text-xs text-gray-500 mt-0.5">Everyone sees a fake pick from you. You choose the decoy. Your real pick is revealed at the official kick-off time.</p>
        </div>
        <div>
          <span className="font-medium">🧤 Clean Sheet (no negative)</span>
          <p className="text-xs text-gray-500 mt-0.5">If your pick loses, you lose <strong>0 points</strong> instead of the usual penalty — you can never go negative on that match.</p>
        </div>
        <div className="pt-2 border-t border-gray-200 space-y-1 text-xs text-gray-500">
          <p><strong>Mobile:</strong> Tap a PowerPlay chip at the top of the Schedule page, then tap the match to apply it.</p>
          <p><strong>Desktop:</strong> Drag a PowerPlay chip onto a match card, or tap the buttons on the card directly.</p>
        </div>
      </div>
    ),
  }

  const soccerSections = [
    soccerPointsSection,
    soccerScoringSection,
    soccerTiebreakerSection,
    soccerKnockoutSection,
    soccerPowerplaysSection,
  ]

  // ─── Shared tail sections ──────────────────────────────────────────────────

  const notificationSection = {
    title: '🔔 Enabling Notifications',
    content: (
      <div className="space-y-3 text-sm text-gray-600">
        <p>Get push alerts for pick results, leaderboard changes, and reminders before picks lock.</p>
        <div>
          <p className="font-medium text-gray-700 mb-1">Android / Desktop (Chrome, Edge, Firefox)</p>
          <p className="text-xs text-gray-500">Go to <strong>Profile → Notifications</strong> and toggle on.</p>
        </div>
        <div>
          <p className="font-medium text-gray-700 mb-1">iPhone / iPad (Safari)</p>
          <ol className="space-y-1 text-xs text-gray-500 list-decimal list-inside">
            <li>Open TushFun in Safari</li>
            <li>Tap the <strong>Share</strong> button (↑) at the bottom</li>
            <li>Tap <strong>Add to Home Screen</strong></li>
            <li>Open TushFun from your Home Screen</li>
            <li>Go to <strong>Profile → Notifications</strong> and toggle on</li>
          </ol>
        </div>
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
  const sections = [howItWorks, pickingSection, skippingSection, ...sportSections, notificationSection, ruleChangeSection]

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
