'use client'
import { Users, TrendingUp, FileText, Mail, Award, Search } from 'lucide-react'
import { useState } from 'react'

const RECRUITERS = [
  { id: 'REC-001', name: 'Gurjas Singh Gandhi', email: 'gurjas@speedtech.ai', batches: 8, resumes: 156, avgScore: 79.4, topScore: 96.2, emailsSent: 42, jdAccuracy: 95.1, lastActive: '2024-04-29 10:32 AM', status: 'active' },
  { id: 'REC-002', name: 'Priya Sharma', email: 'priya@speedtech.ai', batches: 5, resumes: 98, avgScore: 74.8, topScore: 91.5, emailsSent: 28, jdAccuracy: 92.3, lastActive: '2024-04-28 04:15 PM', status: 'active' },
  { id: 'REC-003', name: 'Arjun Patel', email: 'arjun@speedtech.ai', batches: 3, resumes: 67, avgScore: 69.2, topScore: 88.1, emailsSent: 15, jdAccuracy: 88.7, lastActive: '2024-04-27 02:45 PM', status: 'idle' },
  { id: 'REC-004', name: 'Sneha Reddy', email: 'sneha@speedtech.ai', batches: 2, resumes: 34, avgScore: 82.1, topScore: 93.7, emailsSent: 10, jdAccuracy: 96.8, lastActive: '2024-04-26 11:20 AM', status: 'idle' },
]

export default function RecruitersPage() {
  const [search, setSearch] = useState('')
  const filtered = RECRUITERS.filter(r => r.name.toLowerCase().includes(search.toLowerCase()) || r.id.toLowerCase().includes(search.toLowerCase()))

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-3"><Users className="w-6 h-6 text-blue-400" /> Recruiter Scoring Dashboard</h1>
        <p className="text-slate-400 text-sm mt-1">Scoring performance per recruiter ID</p>
      </div>

      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
        <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search by name or ID..."
          className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-raiya-500" />
      </div>

      <div className="grid gap-4">
        {filtered.map(r => (
          <div key={r.id} className="glass-card p-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-raiya-500 to-raiya-700 flex items-center justify-center text-white text-xs font-bold">{r.name.split(' ').map(n => n[0]).join('')}</div>
                <div>
                  <p className="text-white font-semibold">{r.name} <span className="text-xs text-slate-500 font-mono ml-2">{r.id}</span></p>
                  <p className="text-xs text-slate-500">{r.email}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${r.status === 'active' ? 'bg-green-400 animate-pulse' : 'bg-slate-500'}`} />
                <span className="text-xs text-slate-400 capitalize">{r.status}</span>
                <span className="text-[10px] text-slate-600 ml-2">Last: {r.lastActive}</span>
              </div>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
              {[
                { label: 'Batches', value: r.batches, icon: FileText },
                { label: 'Resumes', value: r.resumes, icon: FileText },
                { label: 'Avg Score', value: r.avgScore, icon: TrendingUp },
                { label: 'Top Score', value: r.topScore, icon: Award },
                { label: 'Emails', value: r.emailsSent, icon: Mail },
                { label: 'JD Accuracy', value: `${r.jdAccuracy}%`, icon: TrendingUp },
              ].map(s => (
                <div key={s.label} className="p-2.5 rounded-xl bg-white/5 text-center">
                  <p className="text-[10px] text-slate-500 mb-0.5">{s.label}</p>
                  <p className="text-sm font-bold text-white">{s.value}</p>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
