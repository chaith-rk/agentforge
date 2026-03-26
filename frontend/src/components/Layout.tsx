import { type ReactNode } from 'react'
import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  PhoneCall,
  History,
  Bot,
  CheckCircle,
  Code,
  Settings,
  Mic,
} from 'lucide-react'

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard', exact: true },
  { to: '/calls/new', icon: PhoneCall, label: 'New Call' },
  { to: '/calls', icon: History, label: 'Call History' },
  { to: '/agents', icon: Bot, label: 'Agents' },
  { to: '/evals', icon: CheckCircle, label: 'Evals' },
  { to: '/api-docs', icon: Code, label: 'API Docs' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

interface Props {
  children: ReactNode
}

export function Layout({ children }: Props) {
  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="w-56 bg-slate-800 flex flex-col flex-shrink-0">
        {/* Logo */}
        <div className="flex items-center gap-2.5 px-4 py-5 border-b border-slate-700">
          <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center flex-shrink-0">
            <Mic className="w-4 h-4 text-white" />
          </div>
          <div>
            <div className="text-white font-semibold text-sm leading-tight">Vetty Voice</div>
            <div className="text-slate-400 text-xs">Command Center</div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-2 py-3 space-y-0.5">
          {navItems.map(({ to, icon: Icon, label, exact }) => (
            <NavLink
              key={to}
              to={to}
              end={exact}
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-colors ${
                  isActive
                    ? 'bg-blue-600 text-white'
                    : 'text-slate-300 hover:bg-slate-700 hover:text-white'
                }`
              }
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-slate-700">
          <div className="text-slate-500 text-xs">Vetty Inc. · v0.1.0</div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        {children}
      </main>
    </div>
  )
}
