'use client'
import { useState } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { LayoutDashboard, Users, Brain, Bot, FileText, Mail, Scale, LogOut, Menu, X, ChevronLeft } from 'lucide-react'
import toast from 'react-hot-toast'

const NAV = [
  { href: '/admin', label: 'Overview', icon: LayoutDashboard, desc: 'System Metrics' },
  { href: '/admin/recruiters', label: 'Recruiters', icon: Users, desc: 'Per-ID Scoring' },
  { href: '/admin/llm-metrics', label: 'LLM Metrics', icon: Brain, desc: 'Model Performance' },
  { href: '/admin/agent-metrics', label: 'Agent Metrics', icon: Bot, desc: 'Agent Performance' },
  { href: '/admin/processing-time', label: 'Processing Time', icon: FileText, desc: 'Timeframes' },
  { href: '/admin/email-perf', label: 'Email Performance', icon: Mail, desc: 'Delivery Stats' },
  { href: '/admin/jd-accuracy', label: 'JD Accuracy', icon: Scale, desc: 'Weight Accuracy' },
]

export default function AdminLayout({ children }) {
  const pathname = usePathname()
  const router = useRouter()
  const [open, setOpen] = useState(false)
  const [collapsed, setCollapsed] = useState(false)

  return (
    <div className="min-h-screen bg-main flex">
      {open && <div className="fixed inset-0 bg-black/60 z-40 lg:hidden" onClick={() => setOpen(false)} />}
      <aside className={`fixed top-0 left-0 h-full z-50 ${collapsed ? 'w-[72px]' : 'w-[260px]'} bg-sidebar border-r border-white/5 flex flex-col transition-all duration-300 ${open ? 'translate-x-0' : '-translate-x-full'} lg:translate-x-0`}>
        <div className={`flex items-center ${collapsed ? 'justify-center px-2' : 'px-5'} h-16 border-b border-white/5`}>
          <Link href="/admin" className="flex items-center gap-3 group">
            <div className="w-10 h-10 rounded-xl overflow-hidden bg-white p-1 ring-2 ring-red-500/30 flex-shrink-0">
              <img src="/company_logo.jpeg" alt="Admin" className="w-full h-full object-contain rounded-lg" />
            </div>
            {!collapsed && <div><h1 className="text-sm font-extrabold text-red-400 leading-tight">RAIYA Admin</h1><p className="text-[10px] text-slate-500">System Dashboard</p></div>}
          </Link>
          {!collapsed && <button onClick={() => setCollapsed(true)} className="hidden lg:flex ml-auto p-1.5 rounded-lg hover:bg-white/5 text-slate-400"><ChevronLeft className="w-4 h-4" /></button>}
          {collapsed && <button onClick={() => setCollapsed(false)} className="hidden lg:flex p-1.5 rounded-lg hover:bg-white/5 text-slate-400"><ChevronLeft className="w-4 h-4 rotate-180" /></button>}
          <button onClick={() => setOpen(false)} className="lg:hidden ml-auto p-1.5 rounded-lg hover:bg-white/5 text-slate-400"><X className="w-5 h-5" /></button>
        </div>
        <nav className="flex-1 py-4 px-2 space-y-1 overflow-y-auto">
          {NAV.map(item => {
            const active = pathname === item.href
            return (
              <Link key={item.href} href={item.href} onClick={() => { if (window.innerWidth < 1024) setOpen(false) }}
                className={`flex items-center gap-3 rounded-xl transition-all ${collapsed ? 'justify-center p-3' : 'px-3 py-2.5'} ${active ? 'bg-red-600/20 text-red-300 border border-red-500/20' : 'text-slate-400 hover:text-white hover:bg-white/5 border border-transparent'}`}>
                <item.icon className={`w-5 h-5 flex-shrink-0 ${active ? 'text-red-400' : ''}`} />
                {!collapsed && <div><span className="text-sm font-medium block">{item.label}</span><span className="text-[10px] text-slate-500">{item.desc}</span></div>}
              </Link>
            )
          })}
        </nav>
        <div className={`border-t border-white/5 ${collapsed ? 'p-2' : 'p-4'}`}>
          <button onClick={() => { toast.success('Admin logged out'); router.push('/login') }} className={`flex items-center gap-3 w-full rounded-xl px-3 py-2.5 text-red-400 hover:bg-red-500/10 transition-colors ${collapsed ? 'justify-center' : ''}`}>
            <LogOut className="w-5 h-5" />{!collapsed && <span className="text-sm font-medium">Sign Out</span>}
          </button>
        </div>
      </aside>
      <div className={`flex-1 flex flex-col transition-all duration-300 ${collapsed ? 'lg:ml-[72px]' : 'lg:ml-[260px]'}`}>
        <header className="sticky top-0 z-30 h-14 flex items-center px-4 sm:px-6 bg-sidebar/80 backdrop-blur-xl border-b border-white/5">
          <button onClick={() => setOpen(true)} className="lg:hidden p-2 rounded-lg hover:bg-white/5 text-slate-400 mr-3"><Menu className="w-5 h-5" /></button>
          <h2 className="text-base font-semibold text-white">Admin Dashboard</h2>
          <div className="ml-auto flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-red-400 animate-pulse" />
            <span className="text-xs text-red-300 font-medium">Admin Mode</span>
          </div>
        </header>
        <main className="flex-1 p-4 sm:p-6 lg:p-8 overflow-y-auto">{children}</main>
      </div>
    </div>
  )
}
