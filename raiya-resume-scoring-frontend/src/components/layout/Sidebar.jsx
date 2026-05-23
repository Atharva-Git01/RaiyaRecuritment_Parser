'use client'
import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { LayoutDashboard, FileText, Scale, Zap, BarChart3, GitCompare, Clock, Settings, Menu, X, ChevronLeft, Briefcase } from 'lucide-react'

const NAV_ITEMS = [
  { href: '/platform', label: 'Platform', icon: LayoutDashboard, desc: 'Upload & Score' },
  { href: '/create-job', label: 'Create Job', icon: Briefcase, desc: 'New JD' },
  { href: '/jd-weights', label: 'JD Weights', icon: Scale, desc: 'Weight Assignment' },
  { href: '/processing', label: 'Processing', icon: Zap, desc: 'Queue Status' },
  { href: '/results', label: 'Results', icon: BarChart3, desc: 'Dashboard' },
  { href: '/compare', label: 'Compare', icon: GitCompare, desc: 'Side-by-Side' },
  { href: '/history', label: 'History', icon: Clock, desc: 'Past Batches' },
  { href: '/settings', label: 'Settings', icon: Settings, desc: 'Preferences' },
]

export default function Sidebar({ isOpen, onToggle }) {
  const pathname = usePathname()
  const [collapsed, setCollapsed] = useState(false)

  return (
    <>
      {/* Mobile Overlay */}
      {isOpen && (
        <div className="fixed inset-0 z-40 lg:hidden" style={{ background: 'var(--overlay-bg)' }} onClick={onToggle} />
      )}

      {/* Sidebar */}
      <aside className={`
        fixed top-0 left-0 h-full z-50
        ${collapsed ? 'w-[72px]' : 'w-[260px]'}
        flex flex-col
        transition-all duration-300 ease-in-out
        ${isOpen ? 'translate-x-0' : '-translate-x-full'}
        lg:translate-x-0
      `} style={{ background: 'var(--sidebar-bg)', borderRight: '1px solid var(--divider)' }}>
        {/* Logo */}
        <div className={`flex items-center ${collapsed ? 'justify-center px-2' : 'px-5'} h-20`} style={{ borderBottom: '1px solid var(--divider)' }}>
          <Link href="/platform" className="flex items-center gap-3 group">
            <div className="w-12 h-12 rounded-xl overflow-hidden bg-white p-1 ring-2 ring-raiya-500/30 group-hover:ring-raiya-400/60 transition-all shadow-lg shadow-raiya-500/10 flex-shrink-0">
              <img src="/company_logo.jpeg" alt="SpeedTech.ai" className="w-full h-full object-contain rounded-lg" />
            </div>
            {!collapsed && (
              <div className="overflow-hidden">
                <h1 className="text-base font-extrabold gradient-text leading-tight tracking-tight">RAIYA</h1>
                <p className="text-[11px] t-faint leading-tight">Resume Scoring System</p>
              </div>
            )}
          </Link>

          {/* Collapse Toggle (Desktop) */}
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="hidden lg:flex ml-auto p-1.5 rounded-lg t-faint hover:text-raiya-500 transition-colors"
          >
            <ChevronLeft className={`w-4 h-4 transition-transform ${collapsed ? 'rotate-180' : ''}`} />
          </button>

          {/* Close Toggle (Mobile) */}
          <button onClick={onToggle} className="lg:hidden ml-auto p-1.5 rounded-lg t-faint">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 py-4 px-2 space-y-1 overflow-y-auto">
          {NAV_ITEMS.map((item) => {
            const isActive = pathname === item.href || pathname?.startsWith(item.href + '/')
            const Icon = item.icon
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => { if (window.innerWidth < 1024) onToggle?.() }}
                className={`
                  flex items-center gap-3 rounded-xl transition-all duration-200 group
                  ${collapsed ? 'justify-center p-3' : 'px-3 py-2.5'}
                  ${isActive
                    ? 'bg-raiya-600/20 text-raiya-300 border border-raiya-500/20 shadow-lg shadow-raiya-500/5'
                    : 'border border-transparent'
                  }
                `}
                style={!isActive ? { color: 'var(--text-muted)' } : undefined}
                title={collapsed ? item.label : undefined}
              >
                <Icon className={`w-5 h-5 flex-shrink-0 ${isActive ? 'text-raiya-400' : 'group-hover:text-raiya-400'} transition-colors`} />
                {!collapsed && (
                  <div className="min-w-0">
                    <span className="text-sm font-medium block">{item.label}</span>
                    <span className="text-[10px] block" style={{ color: 'var(--text-faintest)' }}>{item.desc}</span>
                  </div>
                )}
                {isActive && !collapsed && (
                  <div className="ml-auto w-1.5 h-1.5 rounded-full bg-raiya-400 animate-pulse" />
                )}
              </Link>
            )
          })}
        </nav>

        {/* Footer */}
        <div className={`${collapsed ? 'p-2' : 'p-4'}`} style={{ borderTop: '1px solid var(--divider)' }}>
          <div className={`flex items-center gap-3 ${collapsed ? 'justify-center' : ''}`}>
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-raiya-500 to-raiya-700 flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
              R
            </div>
            {!collapsed && (
              <div className="min-w-0">
                <p className="text-xs font-medium truncate" style={{ color: 'var(--text-muted)' }}>Recruiter Demo</p>
                <p className="text-[10px]" style={{ color: 'var(--text-faintest)' }}>RAIYA:001</p>
              </div>
            )}
          </div>
        </div>
      </aside>
    </>
  )
}
