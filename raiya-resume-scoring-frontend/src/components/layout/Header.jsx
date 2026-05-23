'use client'
import { Menu, Bell, Moon, Sun, Settings, LogOut, User, ChevronDown, X, Shield } from 'lucide-react'
import { useState, useRef, useEffect } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import toast from 'react-hot-toast'
import { useTheme } from '@/components/ThemeProvider'

const NOTIFICATIONS = [
  { id: 1, text: 'Gurjas_Singh_Gandhi_Resume.pdf scored 91.2 — Excellent Match', time: '2 min ago', type: 'success', read: false },
  { id: 2, text: 'Priya_Sharma_Resume.pdf scored 86.5 — Excellent Match', time: '3 min ago', type: 'success', read: false },
  { id: 3, text: 'Vikram_Joshi_Resume.pdf — Failed: corrupted PDF', time: '8 min ago', type: 'error', read: false },
  { id: 4, text: 'Batch progress: 50% complete (8/15 resumes)', time: '10 min ago', type: 'info', read: true },
  { id: 5, text: '4 new resumes added to processing queue', time: '12 min ago', type: 'info', read: true },
  { id: 6, text: 'Scoring weights confirmed — 100% total weight', time: '15 min ago', type: 'success', read: true },
  { id: 7, text: 'JD PDF extracted successfully', time: '18 min ago', type: 'success', read: true },
  { id: 8, text: 'Batch BATCH-2024-001 processing started', time: '20 min ago', type: 'info', read: true },
]

export default function Header({ onMenuToggle, title = '' }) {
  const router = useRouter()
  const { dark, toggle } = useTheme()
  const [showNotif, setShowNotif] = useState(false)
  const [showProfile, setShowProfile] = useState(false)
  const [notifications, setNotifications] = useState(NOTIFICATIONS)
  const notifRef = useRef(null)
  const profileRef = useRef(null)

  const unreadCount = notifications.filter(n => !n.read).length

  // Close dropdowns on outside click
  useEffect(() => {
    const handler = (e) => {
      if (notifRef.current && !notifRef.current.contains(e.target)) setShowNotif(false)
      if (profileRef.current && !profileRef.current.contains(e.target)) setShowProfile(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const markAllRead = () => {
    setNotifications(prev => prev.map(n => ({ ...n, read: true })))
    toast.success('All notifications marked as read')
  }

  const handleLogout = () => {
    toast.success('Logged out successfully')
    setTimeout(() => router.push('/login'), 600)
  }

  const handleThemeToggle = () => {
    toggle()
    toast(dark ? '☀️ Light mode activated' : '🌙 Dark mode activated', { duration: 1500 })
  }

  const dotColor = (type) => type === 'success' ? 'bg-green-400' : type === 'error' ? 'bg-red-400' : 'bg-blue-400'

  return (
    <header className="sticky top-0 z-30 h-14 flex items-center justify-between px-4 sm:px-6 backdrop-blur-xl" style={{ background: 'var(--sidebar-bg)', borderBottom: '1px solid var(--divider)' }}>
      <div className="flex items-center gap-3">
        <button onClick={onMenuToggle} className="lg:hidden p-2 rounded-lg t-row-hover t-muted hover:text-raiya-500 transition-colors">
          <Menu className="w-5 h-5" />
        </button>
        <h2 className="text-base sm:text-lg font-semibold t-heading truncate">{title}</h2>
      </div>

      <div className="flex items-center gap-1.5 sm:gap-2">
        {/* Dark Mode Toggle */}
        <button
          onClick={handleThemeToggle}
          className="p-2 rounded-lg t-muted hover:text-raiya-500 transition-colors"
          style={{ background: 'var(--row-hover)' }}
          title={dark ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
        >
          {dark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
        </button>

        {/* Notifications Dropdown */}
        <div className="relative" ref={notifRef}>
          <button
            onClick={() => { setShowNotif(!showNotif); setShowProfile(false) }}
            className="relative p-2 rounded-lg t-muted hover:text-raiya-500 transition-colors"
          >
            <Bell className="w-5 h-5" />
            {unreadCount > 0 && (
              <span className="absolute -top-0.5 -right-0.5 w-5 h-5 bg-red-500 rounded-full text-[10px] font-bold text-white flex items-center justify-center animate-pulse">
                {unreadCount}
              </span>
            )}
          </button>

          {showNotif && (
            <div className="absolute right-0 top-12 w-[340px] sm:w-[380px] rounded-2xl shadow-2xl overflow-hidden" style={{ background: 'var(--dropdown-bg)', border: '1px solid var(--dropdown-border)' }}>
              <div className="flex items-center justify-between px-4 py-3" style={{ borderBottom: '1px solid var(--divider)' }}>
                <h3 className="text-sm font-bold t-heading">Notifications</h3>
                <div className="flex items-center gap-2">
                  {unreadCount > 0 && (
                    <button onClick={markAllRead} className="text-[11px] text-raiya-400 hover:text-raiya-300 transition-colors">Mark all read</button>
                  )}
                  <button onClick={() => setShowNotif(false)} className="p-1 rounded t-faint"><X className="w-4 h-4" /></button>
                </div>
              </div>
              <div className="max-h-[360px] overflow-y-auto">
                {notifications.map(n => (
                  <div key={n.id} className={`flex items-start gap-3 px-4 py-3 t-row-hover transition-colors ${!n.read ? 'bg-raiya-500/5' : ''}`} style={{ borderBottom: '1px solid var(--divider)' }}>
                    <div className={`w-2 h-2 rounded-full ${dotColor(n.type)} mt-1.5 flex-shrink-0`} />
                    <div className="flex-1 min-w-0">
                      <p className={`text-xs leading-relaxed ${!n.read ? 't-heading' : 't-faint'}`}>{n.text}</p>
                      <p className="text-[10px] t-faintest mt-0.5">{n.time}</p>
                    </div>
                    {!n.read && <div className="w-1.5 h-1.5 rounded-full bg-raiya-400 mt-2 flex-shrink-0" />}
                  </div>
                ))}
              </div>
              <div className="px-4 py-2.5 text-center" style={{ borderTop: '1px solid var(--divider)' }}>
                <Link href="/processing" onClick={() => setShowNotif(false)} className="text-xs text-raiya-400 hover:text-raiya-300 font-medium">View All Activity →</Link>
              </div>
            </div>
          )}
        </div>

        {/* Profile Dropdown */}
        <div className="relative" ref={profileRef}>
          <button
            onClick={() => { setShowProfile(!showProfile); setShowNotif(false) }}
            className="flex items-center gap-2 p-1.5 rounded-xl transition-colors"
          >
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-raiya-500 to-raiya-700 flex items-center justify-center text-white text-xs font-bold ring-2 ring-transparent hover:ring-raiya-400/50 transition-all">
              R
            </div>
            <div className="hidden sm:block text-left">
              <p className="text-xs font-medium t-muted leading-tight">Recruiter Demo</p>
              <p className="text-[10px] t-faintest leading-tight">RAIYA:001</p>
            </div>
            <ChevronDown className={`w-3.5 h-3.5 t-faint hidden sm:block transition-transform ${showProfile ? 'rotate-180' : ''}`} />
          </button>

          {showProfile && (
            <div className="absolute right-0 top-12 w-[240px] rounded-2xl shadow-2xl overflow-hidden" style={{ background: 'var(--dropdown-bg)', border: '1px solid var(--dropdown-border)' }}>
              {/* Profile Info */}
              <div className="px-4 py-4" style={{ borderBottom: '1px solid var(--divider)' }}>
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-raiya-500 to-raiya-700 flex items-center justify-center text-white text-sm font-bold">R</div>
                  <div>
                    <p className="text-sm font-semibold t-heading">Recruiter Demo</p>
                    <p className="text-[11px] t-faint">recruiter@speedtech.ai</p>
                  </div>
                </div>
                <div className="mt-2 flex items-center gap-1.5">
                  <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
                  <span className="text-[10px] text-green-400 font-medium">Active Session</span>
                </div>
              </div>

              {/* Menu Items */}
              <div className="py-1.5">
                <Link href="/settings" onClick={() => setShowProfile(false)} className="flex items-center gap-3 px-4 py-2.5 text-sm t-muted t-row-hover transition-colors">
                  <User className="w-4 h-4 t-faint" /> Profile Settings
                </Link>
                <Link href="/settings" onClick={() => setShowProfile(false)} className="flex items-center gap-3 px-4 py-2.5 text-sm t-muted t-row-hover transition-colors">
                  <Shield className="w-4 h-4 t-faint" /> Access Control
                </Link>
                <Link href="/settings" onClick={() => setShowProfile(false)} className="flex items-center gap-3 px-4 py-2.5 text-sm t-muted t-row-hover transition-colors">
                  <Settings className="w-4 h-4 t-faint" /> Preferences
                </Link>
                <button
                  onClick={handleThemeToggle}
                  className="w-full flex items-center gap-3 px-4 py-2.5 text-sm t-muted t-row-hover transition-colors"
                >
                  {dark ? <Sun className="w-4 h-4 t-faint" /> : <Moon className="w-4 h-4 t-faint" />}
                  {dark ? 'Light Mode' : 'Dark Mode'}
                </button>
              </div>

              {/* Logout */}
              <div className="py-1.5" style={{ borderTop: '1px solid var(--divider)' }}>
                <button onClick={handleLogout} className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-red-400 hover:bg-red-500/10 hover:text-red-300 transition-colors">
                  <LogOut className="w-4 h-4" /> Sign Out
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
