'use client'
import { DEMO_BATCHES } from '@/data/static-data'
import { Clock, CheckCircle, Loader2, XCircle } from 'lucide-react'

export default function HistoryPage() {
  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold text-white flex items-center gap-3"><span className="text-3xl">📜</span> Batch History</h1>
        <p className="text-slate-400 text-sm mt-1">Past scoring sessions</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: 'Total Batches', value: DEMO_BATCHES.length, color: 'text-white' },
          { label: 'Total Resumes', value: DEMO_BATCHES.reduce((s, b) => s + b.resume_count, 0), color: 'text-raiya-400' },
          { label: 'Completed', value: DEMO_BATCHES.filter(b => b.status === 'completed').length, color: 'text-green-400' },
          { label: 'Active', value: DEMO_BATCHES.filter(b => b.status === 'processing').length, color: 'text-blue-400' },
        ].map(s => (
          <div key={s.label} className="glass-card p-4">
            <p className="text-xs text-slate-500 mb-1">{s.label}</p>
            <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
          </div>
        ))}
      </div>

      {/* Batch Cards */}
      <div className="space-y-3">
        {DEMO_BATCHES.map(batch => (
          <div key={batch.id} className="glass-card p-4 sm:p-5 hover:border-raiya-500/20 transition-all">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-white">{batch.name}</h3>
                <p className="text-xs text-slate-500 mt-0.5">{batch.jd_title} · {new Date(batch.created_at).toLocaleDateString()}</p>
              </div>
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-1.5">
                  {batch.status === 'completed' ? <CheckCircle className="w-4 h-4 text-green-400" /> : <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />}
                  <span className={`text-xs font-medium capitalize ${batch.status === 'completed' ? 'text-green-400' : 'text-blue-400'}`}>{batch.status}</span>
                </div>
              </div>
            </div>
            <div className="mt-3 flex flex-wrap gap-4 text-xs text-slate-400">
              <span>📄 {batch.resume_count} resumes</span>
              <span className="text-green-400">✓ {batch.completed} done</span>
              {batch.failed > 0 && <span className="text-red-400">✗ {batch.failed} failed</span>}
              {batch.processing > 0 && <span className="text-blue-400">⟳ {batch.processing} running</span>}
              {batch.queued > 0 && <span className="text-slate-500">◷ {batch.queued} queued</span>}
            </div>
            <div className="mt-2 w-full h-1.5 bg-white/5 rounded-full overflow-hidden">
              <div className="h-full bg-gradient-to-r from-green-500 to-green-400 rounded-full" style={{ width: `${(batch.completed / batch.resume_count) * 100}%` }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
