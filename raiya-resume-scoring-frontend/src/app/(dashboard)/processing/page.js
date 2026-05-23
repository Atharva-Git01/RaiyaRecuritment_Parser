'use client'
import { useState } from 'react'
import { DEMO_JOBS, getScoreColor } from '@/data/static-data'
import { CheckCircle, Clock, Loader2, XCircle, ArrowRight, Search, Download, X, Eye, AlertTriangle } from 'lucide-react'
import Link from 'next/link'
import toast from 'react-hot-toast'
import dynamic from 'next/dynamic'

const ScoreDistChart = dynamic(() => import('@/components/charts/ScoreDistChart'), { ssr: false })
const StatusDonutChart = dynamic(() => import('@/components/charts/StatusDonutChart'), { ssr: false })

const STATUS_ICON = {
  completed: <CheckCircle className="w-4 h-4 text-green-400" />,
  processing: <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />,
  queued: <Clock className="w-4 h-4 text-slate-400" />,
  failed: <XCircle className="w-4 h-4 text-red-400" />,
}
const STATUS_BADGE = {
  completed: 'bg-green-500/15 text-green-400',
  processing: 'bg-blue-500/15 text-blue-400',
  queued: 'bg-slate-500/15 text-slate-400',
  failed: 'bg-red-500/15 text-red-400',
}

export default function ProcessingPage() {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [sortBy, setSortBy] = useState('date')
  const [showModal, setShowModal] = useState(null)

  const completed = DEMO_JOBS.filter(j => j.status === 'completed').length
  const processing = DEMO_JOBS.filter(j => j.status === 'processing').length
  const failed = DEMO_JOBS.filter(j => j.status === 'failed').length
  const queued = DEMO_JOBS.filter(j => j.status === 'queued').length
  const remaining = processing + queued
  const total = DEMO_JOBS.length
  const progressPercent = Math.round(((completed + processing * 0.5) / total) * 100)
  const avgScore = DEMO_JOBS.filter(j => j.score).reduce((s, j) => s + j.score, 0) / (completed || 1)

  // ETA
  const timePerJob = 20
  const etaSeconds = remaining * timePerJob
  const etaDisplay = etaSeconds > 60 ? `${Math.ceil(etaSeconds / 60)} min` : etaSeconds > 0 ? `${etaSeconds} sec` : '—'

  // Batch Status
  const batchStatus = remaining > 0 ? 'Processing' : failed > 0 ? 'Completed with Errors' : 'Completed'
  const batchStatusClass = remaining > 0 ? 'bg-blue-500/15 text-blue-400 animate-pulse' : failed > 0 ? 'bg-amber-500/15 text-amber-400' : 'bg-green-500/15 text-green-400'

  // Filter & Sort
  let filtered = DEMO_JOBS.filter(j => {
    const textMatch = j.filename.toLowerCase().includes(search.toLowerCase()) || j.id.toLowerCase().includes(search.toLowerCase())
    const statMatch = statusFilter === 'all' || j.status === statusFilter
    return textMatch && statMatch
  })
  if (sortBy === 'score') filtered.sort((a, b) => (b.score || 0) - (a.score || 0))
  else if (sortBy === 'status') filtered.sort((a, b) => a.status.localeCompare(b.status))
  else if (sortBy === 'filename') filtered.sort((a, b) => a.filename.localeCompare(b.filename))

  // Score distribution for chart
  const scoreDist = { poor: 0, average: 0, good: 0, excellent: 0 }
  DEMO_JOBS.forEach(j => {
    if (j.score != null) {
      if (j.score >= 80) scoreDist.excellent++
      else if (j.score >= 50) scoreDist.good++
      else if (j.score >= 30) scoreDist.average++
      else scoreDist.poor++
    }
  })

  const handleExportCSV = () => {
    const headers = 'Job ID,Filename,Status,Progress,Step,Score\n'
    const rows = DEMO_JOBS.map(j => `${j.id},${j.filename},${j.status},${j.progress}%,${j.step},${j.score || '-'}`).join('\n')
    const blob = new Blob([headers + rows], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a'); a.href = url; a.download = 'RAIYA_Processing_Queue.csv'; a.click()
    URL.revokeObjectURL(url)
    toast.success('CSV exported!')
  }

  const PIPELINE_STAGES = [
    { name: 'Text Extraction', status: 'done', time: '10:23 AM' },
    { name: 'Text Normalization', status: 'done', time: '10:24 AM' },
    { name: 'Section Mapping', status: 'done', time: '10:24 AM' },
    { name: 'AI Scoring', status: 'active', time: 'In progress...' },
    { name: 'Score Aggregation', status: 'pending', time: 'Pending' },
    { name: 'Report Generation', status: 'pending', time: 'Pending' },
  ]

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white flex items-center gap-3"><span className="text-3xl">⚡</span> Bulk Processing Queue</h1>
          <p className="text-slate-400 text-sm mt-1">Real-time resume processing status</p>
        </div>
        <div className="flex gap-2">
          <button onClick={handleExportCSV} className="inline-flex items-center gap-2 px-3 py-2 rounded-xl bg-green-500/10 border border-green-500/20 text-green-300 text-sm hover:bg-green-500/20 transition-colors">
            <Download className="w-4 h-4" /> Export CSV
          </button>
          {completed > 0 && (
            <Link href="/results" className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-raiya-600 to-raiya-500 text-white text-sm font-medium hover:shadow-lg hover:shadow-raiya-500/20 transition-all">
              Top Candidates <ArrowRight className="w-4 h-4" />
            </Link>
          )}
        </div>
      </div>

      {/* Batch Summary Panel */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
        <div className="glass-card p-4">
          <p className="text-xs text-slate-500 mb-1">Batch ID</p>
          <p className="text-lg font-bold text-white font-mono">BATCH-2024-001</p>
        </div>
        <div className="glass-card p-4">
          <p className="text-xs text-slate-500 mb-1">Total Files</p>
          <p className="text-2xl font-bold text-raiya-400">{total}</p>
        </div>
        <div className="glass-card p-4">
          <p className="text-xs text-slate-500 mb-1">Status</p>
          <span className={`px-3 py-1 text-xs font-semibold rounded-full ${batchStatusClass}`}>{batchStatus}</span>
        </div>
        <div className="glass-card p-4">
          <p className="text-xs text-slate-500 mb-1">ETA</p>
          <p className={`text-2xl font-bold ${remaining > 0 ? 'text-green-400' : 'text-slate-500'}`}>{etaDisplay}</p>
        </div>
      </div>

      {/* Global Progress */}
      <div className="glass-card p-5">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-base font-bold text-white">Global Progress</h3>
          <span className="text-sm font-semibold text-slate-400">{completed} / {total} ({progressPercent}%)</span>
        </div>
        <div className="w-full h-3 bg-white/5 rounded-full overflow-hidden">
          <div className="h-full bg-gradient-to-r from-raiya-600 to-green-400 rounded-full transition-all duration-1000" style={{ width: `${progressPercent}%` }} />
        </div>
        <div className="mt-2 flex flex-wrap gap-4 text-xs text-slate-400">
          <span className="flex items-center gap-1.5"><div className="w-2 h-2 rounded-full bg-green-400" /> Completed: {completed}</span>
          <span className="flex items-center gap-1.5"><div className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" /> In Progress: {processing}</span>
          <span className="flex items-center gap-1.5"><div className="w-2 h-2 rounded-full bg-slate-500" /> Queued: {queued}</span>
          <span className="flex items-center gap-1.5"><div className="w-2 h-2 rounded-full bg-red-400" /> Failed: {failed}</span>
          <span>Avg Score: <span className="text-raiya-300 font-medium">{avgScore.toFixed(1)}</span></span>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="glass-card p-4 flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search by filename or job ID..."
            className="w-full pl-10 pr-4 py-2 rounded-xl bg-white/5 border border-white/10 text-white placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-raiya-500" />
        </div>
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
          className="px-3 py-2 rounded-xl bg-white/5 border border-white/10 text-white text-sm focus:ring-2 focus:ring-raiya-500 focus:outline-none appearance-none">
          <option value="all" className="bg-slate-900">All Status</option>
          <option value="completed" className="bg-slate-900">Completed</option>
          <option value="processing" className="bg-slate-900">In Progress</option>
          <option value="queued" className="bg-slate-900">Queued</option>
          <option value="failed" className="bg-slate-900">Failed</option>
        </select>
        <select value={sortBy} onChange={e => setSortBy(e.target.value)}
          className="px-3 py-2 rounded-xl bg-white/5 border border-white/10 text-white text-sm focus:ring-2 focus:ring-raiya-500 focus:outline-none appearance-none">
          <option value="date" className="bg-slate-900">Sort by Date</option>
          <option value="score" className="bg-slate-900">Sort by Score</option>
          <option value="status" className="bg-slate-900">Sort by Status</option>
          <option value="filename" className="bg-slate-900">Sort by Filename</option>
        </select>
      </div>

      {/* Processing Queue Table */}
      <div className="glass-card overflow-hidden">
        <div className="p-4 border-b border-white/5 flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-white">Processing Queue</h2>
            <p className="text-xs text-slate-500 mt-0.5">Real-time status of all resume processing jobs</p>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/5">
                <th className="text-left px-4 py-3 text-xs text-slate-500 font-medium uppercase tracking-wider">Job ID</th>
                <th className="text-left px-4 py-3 text-xs text-slate-500 font-medium uppercase tracking-wider">File Name</th>
                <th className="text-left px-4 py-3 text-xs text-slate-500 font-medium uppercase tracking-wider">Status</th>
                <th className="text-left px-4 py-3 text-xs text-slate-500 font-medium uppercase tracking-wider">Progress</th>
                <th className="text-left px-4 py-3 text-xs text-slate-500 font-medium uppercase tracking-wider">Last Step</th>
                <th className="text-left px-4 py-3 text-xs text-slate-500 font-medium uppercase tracking-wider">Score</th>
                <th className="text-left px-4 py-3 text-xs text-slate-500 font-medium uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr><td colSpan={7} className="px-4 py-8 text-center text-slate-500">No jobs found matching criteria.</td></tr>
              ) : filtered.map(job => (
                <tr key={job.id} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                  <td className="px-4 py-3 text-slate-400 font-mono text-xs">{job.id}</td>
                  <td className="px-4 py-3 text-white truncate max-w-[200px]">{job.filename}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-semibold ${STATUS_BADGE[job.status]}`}>
                      {STATUS_ICON[job.status]}
                      <span className="capitalize">{job.status === 'processing' ? 'In Progress' : job.status}</span>
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="w-16 h-2 bg-white/5 rounded-full overflow-hidden">
                        <div className={`h-full rounded-full transition-all ${job.status === 'failed' ? 'bg-red-500' : 'bg-raiya-500'}`} style={{ width: `${job.progress}%` }} />
                      </div>
                      <span className="text-xs font-semibold text-slate-400">{job.progress}%</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-400">{job.step}</td>
                  <td className="px-4 py-3">
                    {job.score ? (
                      <span className="text-sm font-bold" style={{ color: getScoreColor(job.score) }}>{job.score}</span>
                    ) : job.status === 'failed' ? (
                      <span className="text-xs text-red-400">Error</span>
                    ) : (
                      <span className="text-slate-600">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 flex gap-1.5">
                    {job.status === 'completed' && (
                      <Link href={`/results/${job.candidateId || 'candidate-1'}`} className="px-2 py-1 rounded-lg bg-green-500/10 text-green-300 text-xs font-medium hover:bg-green-500/20 transition-colors">
                        Results
                      </Link>
                    )}
                    {(job.status === 'completed' || job.status === 'processing') && (
                      <button onClick={() => setShowModal(job)} className="px-2 py-1 rounded-lg bg-raiya-500/10 text-raiya-300 text-xs font-medium hover:bg-raiya-500/20 transition-colors">
                        <Eye className="w-3 h-3" />
                      </button>
                    )}
                    {job.status === 'failed' && (
                      <button onClick={() => toast.error(`Error: Failed to extract text from ${job.filename}. File may be corrupted.`)} className="px-2 py-1 rounded-lg bg-red-500/10 text-red-300 text-xs font-medium hover:bg-red-500/20 transition-colors">
                        <AlertTriangle className="w-3 h-3" />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Visualizations */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="glass-card p-6">
          <h3 className="text-base font-bold text-white mb-4">📊 Score Distribution</h3>
          <div className="h-64"><ScoreDistChart data={scoreDist} /></div>
        </div>
        <div className="glass-card p-6">
          <h3 className="text-base font-bold text-white mb-4">📈 Processing Status</h3>
          <div className="h-64"><StatusDonutChart data={{ completed, processing, queued, failed }} /></div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="glass-card p-6">
        <h3 className="text-base font-bold text-white mb-4 flex items-center gap-2">🕑 Recent Activity</h3>
        <div className="space-y-0 relative">
          {/* Timeline line */}
          <div className="absolute left-[15px] top-2 bottom-2 w-px bg-white/10" />
          {[
            { time: '10:32 AM', desc: 'Gurjas_Singh_Gandhi_Resume.pdf scored 91.2 — Excellent Match', type: 'success' },
            { time: '10:31 AM', desc: 'Priya_Sharma_Resume.pdf scored 86.5 — Excellent Match', type: 'success' },
            { time: '10:30 AM', desc: 'Arjun_Patel_Resume.pdf — AI Scoring stage started', type: 'info' },
            { time: '10:29 AM', desc: 'Sneha_Reddy_Resume.pdf scored 78.3 — Good Match', type: 'success' },
            { time: '10:28 AM', desc: 'Batch progress: 50% complete (8/15 resumes)', type: 'milestone' },
            { time: '10:27 AM', desc: 'Rahul_Menon_Resume.pdf scored 72.1 — Good Match', type: 'success' },
            { time: '10:26 AM', desc: 'Ananya_Gupta_Resume.pdf — Text extraction completed', type: 'info' },
            { time: '10:24 AM', desc: 'Vikram_Joshi_Resume.pdf — Failed: corrupted PDF file', type: 'error' },
            { time: '10:23 AM', desc: 'Kavitha_Nair_Resume.pdf scored 65.8 — Moderate Match', type: 'success' },
            { time: '10:21 AM', desc: '4 new resumes added to processing queue', type: 'queue' },
            { time: '10:20 AM', desc: 'Batch BATCH-2024-001 processing started', type: 'milestone' },
            { time: '10:18 AM', desc: 'Scoring weights confirmed — 100% total weight validated', type: 'info' },
          ].map((item, i) => {
            const dotColor = item.type === 'success' ? 'bg-green-400' : item.type === 'error' ? 'bg-red-400' : item.type === 'milestone' ? 'bg-amber-400' : item.type === 'queue' ? 'bg-purple-400' : 'bg-blue-400'
            const textColor = item.type === 'success' ? 'text-green-300/80' : item.type === 'error' ? 'text-red-300/80' : item.type === 'milestone' ? 'text-amber-300/80' : item.type === 'queue' ? 'text-purple-300/80' : 'text-blue-300/80'
            return (
              <div key={i} className="flex items-start gap-4 py-2.5 pl-1 group">
                <div className={`w-[10px] h-[10px] rounded-full ${dotColor} mt-1.5 flex-shrink-0 z-10 ring-2 ring-slate-900 group-hover:scale-125 transition-transform`} />
                <div className="flex-1 min-w-0">
                  <p className={`text-sm ${textColor}`}>{item.desc}</p>
                </div>
                <span className="text-[11px] text-slate-500 font-mono flex-shrink-0 mt-0.5">{item.time}</span>
              </div>
            )
          })}
        </div>
      </div>

      {/* Pipeline Details Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={() => setShowModal(null)} />
          <div className="relative rounded-2xl bg-slate-900/95 border border-white/10 shadow-2xl p-6 max-w-lg w-full max-h-[80vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-5">
              <h3 className="text-lg font-bold text-white">Pipeline Details</h3>
              <button onClick={() => setShowModal(null)} className="p-2 rounded-lg hover:bg-white/5 text-slate-400"><X className="w-5 h-5" /></button>
            </div>
            <div className="mb-4 p-3 rounded-xl bg-white/5 border border-white/10">
              <p className="text-xs text-slate-500">File</p>
              <p className="text-sm text-white font-medium">{showModal.filename}</p>
              <p className="text-xs text-slate-500 mt-1">Job ID: {showModal.id}</p>
            </div>
            <div className="space-y-3">
              {PIPELINE_STAGES.map((stage, i) => (
                <div key={i} className={`flex items-center gap-3 p-3 rounded-xl ${stage.status === 'done' ? 'bg-green-500/10' : stage.status === 'active' ? 'bg-blue-500/10' : 'bg-white/5'}`}>
                  <div className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 ${stage.status === 'done' ? 'bg-green-500' : stage.status === 'active' ? 'bg-blue-500' : 'bg-slate-600'}`}>
                    {stage.status === 'done' ? <CheckCircle className="w-4 h-4 text-white" /> : stage.status === 'active' ? <Loader2 className="w-4 h-4 text-white animate-spin" /> : <Clock className="w-4 h-4 text-slate-400" />}
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-semibold text-white">{stage.name}</p>
                    <p className="text-xs text-slate-400">{stage.time}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
