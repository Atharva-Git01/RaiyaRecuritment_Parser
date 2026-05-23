'use client'
import { useState } from 'react'
import Sidebar from '@/components/layout/Sidebar'
import Header from '@/components/layout/Header'

const PAGE_TITLES = {
  '/platform': '📤 Recruiter Platform',
  '/create-job': '💼 Create Job Description',
  '/jd-weights': '⚖️ JD Weight Assignment',
  '/processing': '⚡ Processing Queue',
  '/results': '📊 Results Dashboard',
  '/compare': '⚖️ Compare Candidates',
  '/history': '📜 Batch History',
  '/settings': '⚙️ Settings',
}

export default function DashboardLayout({ children }) {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="min-h-screen">
      <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />
      <div className="lg:ml-[260px] transition-all duration-300">
        <Header onMenuToggle={() => setSidebarOpen(!sidebarOpen)} />
        <main className="p-4 sm:p-6 lg:p-8 min-h-[calc(100vh-56px)]">
          {children}
        </main>
      </div>
    </div>
  )
}
