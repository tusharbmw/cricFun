const variants = {
  live:      'badge-error animate-pulse',
  upcoming:  'badge-info',
  completed: 'badge-ghost',
  toss:      'badge-warning',
  delayed:   'badge-warning',
  win:       'badge-success',
  loss:      'badge-error',
  default:   'badge-ghost',
}

export default function Badge({ label, variant = 'default', className = '' }) {
  return (
    <span className={`badge badge-sm font-medium ${variants[variant]} ${className}`}>
      {label}
    </span>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export function matchStatusBadge(result) {
  const map = {
    IP:    { label: 'LIVE',      variant: 'live'      },
    TOSS:  { label: 'TOSS',      variant: 'toss'      },
    DLD:   { label: 'DELAYED',   variant: 'delayed'   },
    TBD:   { label: 'UPCOMING',  variant: 'upcoming'  },
    team1: { label: 'DONE',      variant: 'completed' },
    team2: { label: 'DONE',      variant: 'completed' },
    NR:    { label: 'NO RESULT', variant: 'completed' },
  }
  const { label, variant } = map[result] ?? { label: result, variant: 'default' }
  return <Badge label={label} variant={variant} />
}
