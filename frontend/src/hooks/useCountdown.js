import { useState, useEffect } from 'react'

// Returns a human-readable countdown string to the target datetime.
// Updates every minute (every second when < 2 minutes away).
export function useCountdown(targetDatetime) {
  const [label, setLabel] = useState('')

  useEffect(() => {
    function compute() {
      const diff = new Date(targetDatetime).getTime() - Date.now()
      if (diff <= 0) return { label: 'Picks locked', urgent: false }

      const totalSeconds = Math.floor(diff / 1000)
      const days    = Math.floor(totalSeconds / 86400)
      const hours   = Math.floor((totalSeconds % 86400) / 3600)
      const minutes = Math.floor((totalSeconds % 3600) / 60)

      let label
      if (days > 0)        label = `${days}d ${hours}h left`
      else if (hours > 0)  label = `${hours}h ${minutes}m left`
      else if (minutes > 1) label = `${minutes} mins left`
      else                 label = 'Starting soon'

      return { label, urgent: diff < 60 * 60 * 1000 }  // urgent if < 1 hour
    }

    function tick() {
      const { label } = compute()
      setLabel(label)
    }

    tick()

    const diff = new Date(targetDatetime).getTime() - Date.now()
    // Refresh every second if < 2 minutes, else every minute
    const interval = diff < 120_000 ? 1000 : 60_000
    const id = setInterval(tick, interval)
    return () => clearInterval(id)
  }, [targetDatetime])

  return label
}
