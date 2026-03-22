export default function PickDistribution({ team1, team2, team1Count, team2Count, hiddenCount, isCompleted }) {
  const total = team1Count + team2Count + hiddenCount
  if (total === 0) return null

  return (
    <div className="bg-gray-50 rounded-lg p-2.5 mb-2">
      <p className="text-xs text-gray-500 mb-1.5">
        {hiddenCount > 0 && !isCompleted ? 'Pick distribution (some hidden)' : 'Pick distribution'}
      </p>
      <div className="flex gap-1.5">
        {team1Count > 0 && (
          <div
            className="flex items-center justify-center text-xs font-medium rounded px-1.5 py-1.5"
            style={{ flex: team1Count, background: '#E6F1FB', color: '#0C447C' }}
          >
            {team1 ? `${team1.split(' ').map(w => w[0]).join('')}: ` : ''}{team1Count}
          </div>
        )}
        {team2Count > 0 && (
          <div
            className="flex items-center justify-center text-xs font-medium rounded px-1.5 py-1.5"
            style={{ flex: team2Count, background: '#EAF3DE', color: '#27500A' }}
          >
            {team2 ? `${team2.split(' ').map(w => w[0]).join('')}: ` : ''}{team2Count}
          </div>
        )}
        {hiddenCount > 0 && !isCompleted && (
          <div
            className="flex items-center justify-center text-xs font-medium rounded px-1.5 py-1.5"
            style={{ flex: hiddenCount, background: '#e5e7eb', color: '#6b7280' }}
          >
            🕵️ {hiddenCount}
          </div>
        )}
      </div>
    </div>
  )
}
