'use client'
import { useState } from 'react'
import { DEMO_CANDIDATES, getScoreColor, getScoreBadgeClass } from '@/data/static-data'
import { Search, Download, GitCompare, TrendingUp, Award, Users, Mail, FileText, X, CheckCircle } from 'lucide-react'
import Link from 'next/link'
import toast from 'react-hot-toast'

export default function ResultsPage() {
  const [search, setSearch] = useState('')
  const [sortKey, setSortKey] = useState('final_score')
  const [sortDir, setSortDir] = useState('desc')
  const [showEmailModal, setShowEmailModal] = useState(false)
  const [emailSending, setEmailSending] = useState(false)

  const filtered = DEMO_CANDIDATES
    .filter(c => c.name.toLowerCase().includes(search.toLowerCase()))
    .sort((a, b) => sortDir === 'desc' ? b[sortKey] - a[sortKey] : a[sortKey] - b[sortKey])

  const topScore = Math.max(...DEMO_CANDIDATES.map(c => c.final_score))
  const avgScore = (DEMO_CANDIDATES.reduce((s, c) => s + c.final_score, 0) / DEMO_CANDIDATES.length).toFixed(1)
  const excellent = DEMO_CANDIDATES.filter(c => c.final_score >= 85).length
  const good = DEMO_CANDIDATES.filter(c => c.final_score >= 70 && c.final_score < 85).length
  const topCandidates = DEMO_CANDIDATES.filter(c => c.final_score >= 70).sort((a,b) => b.final_score - a.final_score)

  const toggleSort = (key) => {
    if (sortKey === key) setSortDir(d => d === 'desc' ? 'asc' : 'desc')
    else { setSortKey(key); setSortDir('desc') }
  }

  const handleDownloadCSV = () => {
    const headers = 'Rank,Name,Email,Score,Status,Top Section,Match Level\n'
    const rows = filtered.map((c, i) => `${i+1},${c.name},${c.email},${c.final_score},${c.score_status},${c.top_section},${c.match_level}`).join('\n')
    const blob = new Blob([headers + rows], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a'); a.href = url; a.download = 'RAIYA_Results_Report.csv'; a.click()
    URL.revokeObjectURL(url)
    toast.success('CSV downloaded!')
  }

  const handleDownloadPDF = () => {
    const content = `RAIYA: Recruiting Resume Scoring System\nResults Report\n${'='.repeat(50)}\nGenerated: ${new Date().toLocaleString()}\nTotal Candidates: ${DEMO_CANDIDATES.length}\nAverage Score: ${avgScore}\n\n${'─'.repeat(50)}\nRANKED CANDIDATES\n${'─'.repeat(50)}\n\n${filtered.map((c, i) => `#${i+1} ${c.name} (${c.final_score}/100) — ${c.score_status}\n    Email: ${c.email}\n    Top Section: ${c.top_section}\n    Match Level: ${c.match_level}\n    Recommendation: ${c.recommendation}\n    Strengths: ${c.strengths.join('; ')}\n    Weaknesses: ${c.weaknesses.join('; ')}\n`).join('\n')}`
    const blob = new Blob([content], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a'); a.href = url; a.download = 'RAIYA_Results_Report.txt'; a.click()
    URL.revokeObjectURL(url)
    toast.success('Report downloaded!')
  }

  const handleSendEmails = () => {
    setEmailSending(true)
    setTimeout(() => {
      setEmailSending(false)
      setShowEmailModal(false)
      toast.success('Email shared to these candidates for interview call!', { duration: 4000 })
    }, 2000)
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white flex items-center gap-3"><span className="text-3xl">📊</span> Results Dashboard</h1>
          <p className="text-slate-400 text-sm mt-1">All candidates ranked by AI score</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href="/compare" className="inline-flex items-center gap-2 px-3 py-2 rounded-xl bg-white/5 border border-white/10 text-slate-300 text-sm hover:bg-white/10 transition-colors">
            <GitCompare className="w-4 h-4" /> Compare
          </Link>
          <button onClick={handleDownloadCSV} className="inline-flex items-center gap-2 px-3 py-2 rounded-xl bg-white/5 border border-white/10 text-slate-300 text-sm hover:bg-white/10 transition-colors">
            <Download className="w-4 h-4" /> CSV
          </button>
          <button onClick={handleDownloadPDF} className="inline-flex items-center gap-2 px-3 py-2 rounded-xl bg-white/5 border border-white/10 text-slate-300 text-sm hover:bg-white/10 transition-colors">
            <FileText className="w-4 h-4" /> Report
          </button>
          {topCandidates.length > 0 && (
            <button onClick={() => setShowEmailModal(true)} className="inline-flex items-center gap-2 px-3 py-2 rounded-xl bg-raiya-600/20 border border-raiya-500/30 text-raiya-300 text-sm hover:bg-raiya-600/30 transition-colors">
              <Mail className="w-4 h-4" /> Email Top Candidates
            </button>
          )}
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
        {[
          { label: 'Top Match', value: topScore.toFixed(1), icon: Award, color: 'text-green-400', bg: 'bg-green-500/10' },
          { label: 'Average', value: avgScore, icon: TrendingUp, color: 'text-raiya-400', bg: 'bg-raiya-500/10' },
          { label: 'Excellent', value: excellent, icon: Award, color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
          { label: 'Good+', value: good, icon: Users, color: 'text-blue-400', bg: 'bg-blue-500/10' },
        ].map(s => (
          <div key={s.label} className={`glass-card p-4 ${s.bg} border-none`}>
            <div className="flex items-center gap-2 mb-1"><s.icon className={`w-4 h-4 ${s.color}`} /><span className="text-xs text-slate-500">{s.label}</span></div>
            <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
          </div>
        ))}
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
        <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search candidates..."
          className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-raiya-500" />
      </div>

      {/* Candidates Table */}
      <div className="glass-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/5">
                <th className="text-left px-4 py-3 text-xs text-slate-500 font-medium">Rank</th>
                <th className="text-left px-4 py-3 text-xs text-slate-500 font-medium">Candidate</th>
                <th className="text-left px-4 py-3 text-xs text-slate-500 font-medium cursor-pointer hover:text-white" onClick={() => toggleSort('final_score')}>
                  Score {sortKey === 'final_score' && (sortDir === 'desc' ? '↓' : '↑')}
                </th>
                <th className="text-left px-4 py-3 text-xs text-slate-500 font-medium hidden sm:table-cell">Status</th>
                <th className="text-left px-4 py-3 text-xs text-slate-500 font-medium hidden md:table-cell">Top Section</th>
                <th className="text-left px-4 py-3 text-xs text-slate-500 font-medium">Action</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((c, i) => (
                <tr key={c.id} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                  <td className="px-4 py-3">
                    <span className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${i === 0 ? 'bg-amber-500/20 text-amber-400' : i === 1 ? 'bg-slate-400/20 text-slate-300' : i === 2 ? 'bg-amber-700/20 text-amber-600' : 'bg-white/5 text-slate-500'}`}>{i + 1}</span>
                  </td>
                  <td className="px-4 py-3"><p className="text-white font-medium">{c.name}</p><p className="text-xs text-slate-500">{c.email}</p></td>
                  <td className="px-4 py-3"><span className="text-lg font-bold" style={{ color: getScoreColor(c.final_score) }}>{c.final_score}</span></td>
                  <td className="px-4 py-3 hidden sm:table-cell"><span className={`px-2 py-1 rounded-full text-xs font-medium ${getScoreBadgeClass(c.final_score)}`}>{c.score_status}</span></td>
                  <td className="px-4 py-3 hidden md:table-cell text-xs text-slate-400">{c.top_section}</td>
                  <td className="px-4 py-3">
                    <Link href={`/results/${c.id}`} className="px-3 py-1.5 rounded-lg bg-raiya-500/10 text-raiya-300 text-xs font-medium hover:bg-raiya-500/20 transition-colors">View Report</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Email Modal */}
      {showEmailModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={() => setShowEmailModal(false)} />
          <div className="relative rounded-2xl bg-slate-900/95 border border-white/10 shadow-2xl p-6 sm:p-8 max-w-lg w-full">
            <button onClick={() => setShowEmailModal(false)} className="absolute top-4 right-4 p-2 rounded-lg hover:bg-white/5 text-slate-400"><X className="w-5 h-5" /></button>
            <Mail className="w-10 h-10 text-raiya-400 mx-auto mb-4" />
            <h3 className="text-lg font-bold text-white text-center mb-2">Send Interview Scheduling Email</h3>
            <p className="text-sm text-slate-400 text-center mb-4">Send email to the following top-ranked candidates (score ≥ 70):</p>
            <div className="space-y-2 max-h-48 overflow-y-auto mb-4">
              {topCandidates.map(c => (
                <div key={c.id} className="flex items-center justify-between p-2.5 rounded-xl bg-white/5 border border-white/5">
                  <div><p className="text-sm text-white font-medium">{c.name}</p><p className="text-xs text-slate-500">{c.email}</p></div>
                  <span className="text-sm font-bold" style={{ color: getScoreColor(c.final_score) }}>{c.final_score}</span>
                </div>
              ))}
            </div>
            <button onClick={handleSendEmails} disabled={emailSending} className="w-full py-3 rounded-xl bg-gradient-to-r from-raiya-600 to-raiya-500 text-white font-semibold flex items-center justify-center gap-2 transition-all shadow-lg shadow-raiya-500/20 disabled:opacity-50">
              {emailSending ? <><div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />Sending...</> : <><Mail className="w-5 h-5" />Send Interview Email to {topCandidates.length} Candidates</>}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
