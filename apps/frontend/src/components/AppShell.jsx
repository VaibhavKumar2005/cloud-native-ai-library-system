import { NavLink, useNavigate } from 'react-router-dom'
import { Activity, BarChart3, Home, LogOut, Shield } from 'lucide-react'
import { clearSession } from '@/lib/auth'

const navItems = [
  { to: '/app', label: 'Workspace', icon: Home },
  { to: '/app/monitoring', label: 'Mission Control', icon: Activity },
  { to: '/app/analytics', label: 'Analytics', icon: BarChart3 },
]

function navClassName(isActive) {
  return `group flex items-center gap-3 rounded-2xl px-4 py-3 text-sm transition-all ${
    isActive
      ? 'bg-cyan-400 text-slate-950 shadow-lg shadow-cyan-400/20'
      : 'text-slate-400 hover:bg-white/[0.04] hover:text-white'
  }`
}

export default function AppShell({
  title,
  subtitle,
  status,
  headerRight,
  children,
}) {
  const navigate = useNavigate()

  const handleLogout = () => {
    clearSession()
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-[#040207] text-slate-50">
      <div className="orb w-[460px] h-[460px] bg-cyan-600 top-[-10%] left-[-8%]" />
      <div className="orb w-[380px] h-[380px] bg-emerald-600 bottom-[8%] right-[-6%]" style={{ animationDelay: '8s' }} />

      <div className="relative z-10 flex min-h-screen">
        <aside className="hidden w-72 border-r border-white/[0.06] bg-black/20 px-5 py-6 backdrop-blur-2xl lg:block">
          <button
            className="flex w-full items-center gap-3 rounded-2xl border border-white/[0.06] bg-white/[0.03] p-4 text-left transition hover:bg-white/[0.05]"
            onClick={() => navigate('/')}
          >
            <div className="rounded-2xl border border-cyan-400/20 bg-cyan-400/10 p-3">
              <Shield className="h-5 w-5 text-cyan-300" />
            </div>
            <div>
              <div className="text-base font-bold tracking-tight text-white">VeriRAG</div>
              <div className="text-[10px] font-mono uppercase tracking-[0.22em] text-slate-500">
                Verified Workspace
              </div>
            </div>
          </button>

          <nav className="mt-8 space-y-2">
            {navItems.map(({ to, label, icon: Icon }) => (
              <NavLink key={to} to={to} className={({ isActive }) => navClassName(isActive)}>
                <Icon className="h-4 w-4" />
                <span>{label}</span>
              </NavLink>
            ))}
          </nav>

          <div className="mt-8 rounded-2xl border border-white/[0.06] bg-white/[0.03] p-4">
            <div className="text-[10px] font-mono uppercase tracking-[0.22em] text-slate-500">Current phase</div>
            <p className="mt-3 text-sm leading-6 text-slate-300">
              Product shell, better ingestion visibility, and auth cleanup are now in place. OAuth and evidence UX are next.
            </p>
          </div>

          <button
            className="mt-8 flex w-full items-center justify-center gap-2 rounded-2xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300 transition hover:bg-red-500/15 hover:text-red-200"
            onClick={handleLogout}
          >
            <LogOut className="h-4 w-4" />
            Sign Out
          </button>
        </aside>

        <div className="flex min-h-screen flex-1 flex-col">
          <header className="border-b border-white/[0.06] bg-[#040207]/70 px-6 py-5 backdrop-blur-2xl">
            <div className="mx-auto flex w-full max-w-7xl items-end justify-between gap-6">
              <div>
                <h1 className="text-2xl font-bold tracking-tight text-white">{title}</h1>
                {subtitle && (
                  <p className="mt-1 text-sm text-slate-400">{subtitle}</p>
                )}
              </div>
              <div className="flex items-center gap-3">
                {status && (
                  <span className="rounded-full border border-emerald-400/20 bg-emerald-400/10 px-3 py-1 text-[10px] font-mono uppercase tracking-[0.18em] text-emerald-300">
                    {status}
                  </span>
                )}
                {headerRight}
              </div>
            </div>
          </header>

          <main className="mx-auto w-full max-w-7xl flex-1 px-6 py-6">
            {children}
          </main>
        </div>
      </div>
    </div>
  )
}
