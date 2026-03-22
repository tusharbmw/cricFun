import { NavLink } from 'react-router-dom'
import { Home, CalendarDays, CheckSquare, BarChart2, BookOpen } from 'lucide-react'

const links = [
  { to: '/',          icon: Home,         label: 'Home'      },
  { to: '/schedule',  icon: CalendarDays, label: 'Schedule'  },
  { to: '/results',   icon: CheckSquare,  label: 'Results'   },
  { to: '/standings', icon: BarChart2,    label: 'Standings' },
  { to: '/rules',     icon: BookOpen,     label: 'Rules'     },
]

export default function BottomNav() {
  return (
    <nav className="dock bg-neutral text-neutral-content border-t border-base-300 md:hidden z-50">
      {/* eslint-disable-next-line no-unused-vars */}
      {links.map(({ to, icon: NavIcon, label }) => (
        <NavLink
          key={to}
          to={to}
          end={to === '/'}
          className={({ isActive }) => isActive ? 'dock-active text-primary' : 'text-neutral-content/50'}
        >
          <NavIcon size={20} />
          <span className="dock-label">{label}</span>
        </NavLink>
      ))}
    </nav>
  )
}
