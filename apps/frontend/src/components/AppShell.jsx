import React from 'react'
import { useEffect, useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { Activity, BarChart3, Home, LogOut, Shield, Sparkles, Keyboard } from 'lucide-react'
import { clearSession } from '@/lib/auth'
import CommandPalette from '@/components/CommandPalette'

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
  const [paletteOpen, setPaletteOpen] = useState(false)

  useEffect(() => {
    const handleKeyDown = (event) => {
      const isShortcut = (event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k'
      if (!isShortcut) return
      event.preventDefault()
      setPaletteOpen((current) => !current)
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  const handleLogout = () => {
    clearSession()
    navigate('/login')
  }

  const commandActions = [
    {
      id: 'home',
      label: 'Open home',
      description: 'Return to the product landing page.',
      keywords: ['landing', 'homepage', 'start'],
      icon: Shield,
      shortcut: 'G H',
      run: () => navigate('/'),
    },
    {
      id: 'workspace',
      label: 'Open workspace',
      description: 'Go to the verified document chat workspace.',
      keywords: ['documents', 'chat', 'workspace'],
      icon: Home,
      shortcut: 'G W',
      run: () => navigate('/app'),
    },
    {
      id: 'monitoring',
      label: 'Open operations',
      description: 'Inspect CostOps, QualityOps, and service health.',
      keywords: ['ops', 'monitoring', 'cost', 'quality'],
      icon: Activity,
      shortcut: 'G O',
      run: () => navigate('/app/monitoring'),
    },
    {
      id: 'analytics',
      label: 'Open analytics',
      description: 'Review faithfulness, query trends, and document readiness.',
      keywords: ['metrics', 'charts', 'insights'],
      icon: BarChart3,
      shortcut: 'G A',
      run: () => navigate('/app/analytics'),
    },
    {
      id: 'login',
      label: 'Open sign in',
      description: 'Jump to the authentication screen.',
      keywords: ['auth', 'sign in', 'login'],
      icon: Sparkles,
      shortcut: 'G L',
      run: () => navigate('/login'),
    },
    {
      id: 'logout',
      label: 'Sign out',
      description: 'Clear the current session and return to login.',
      keywords: ['logout', 'sign out', 'session'],
      icon: LogOut,
      shortcut: '⌘⇧L',
      run: handleLogout,
    },
  ]

  return (
    <div className="min-h-screen overflow-x-hidden bg-[#040207] text-slate-50">
      <div className="hero-grid" />
      <div className="orb w-[460px] h-[460px] bg-cyan-600 top-[-10%] left-[-8%]" />
      <div className="orb w-[380px] h-[380px] bg-emerald-600 bottom-[8%] right-[-6%]" style={{ animationDelay: '8s' }} />

      <div className="relative z-10 flex min-h-screen">
        <aside className="hidden w-80 border-r border-white/[0.06] bg-black/20 px-5 py-6 backdrop-blur-2xl lg:block">
          <button
            className="flex w-full items-center gap-3 rounded-2xl border border-white/[0.06] bg-white/[0.03] p-4 text-left transition hover:-translate-y-0.5 hover:bg-white/[0.05]"
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
            {navItems.map(({ to, label, icon }) => (
              <NavLink key={to} to={to} className={({ isActive }) => navClassName(isActive)}>
                {icon ? React.createElement(icon, { className: 'h-4 w-4' }) : null}
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
          <header className="sticky top-0 z-30 border-b border-white/[0.06] bg-[#040207]/70 px-6 py-5 backdrop-blur-2xl">
            <div className="mx-auto flex w-full max-w-7xl flex-wrap items-end justify-between gap-4">
              <div>
                <h1 className="text-2xl font-bold tracking-tight text-white">{title}</h1>
                {subtitle && (
                  <p className="mt-1 text-sm text-slate-400">{subtitle}</p>
                )}
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  onClick={() => setPaletteOpen(true)}
                  className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.03] px-3 py-1.5 text-[10px] font-mono uppercase tracking-[0.18em] text-slate-300 transition hover:-translate-y-0.5 hover:border-cyan-400/20 hover:bg-white/[0.06]"
                >
                  <Sparkles className="h-3 w-3 text-cyan-300" />
                  Command Palette
                  <span className="rounded-full border border-white/10 bg-black/20 px-1.5 py-0.5 text-[9px] text-slate-500">
                    Ctrl K
                  </span>
                </button>
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

      <CommandPalette
        open={paletteOpen}
        onOpenChange={setPaletteOpen}
        actions={commandActions}
      />
    </div>
  )
}
