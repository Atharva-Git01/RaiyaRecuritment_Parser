'use client'
import { Bot, CheckCircle, XCircle } from 'lucide-react'

const AGENTS = [
  { name: 'Text Extraction Agent', version: 'v2.4.1', successRate: 97.8, avgTime: '4.2s', p95: '8.1s', processed: 220, failed: 5, lastRun: '2024-04-29 10:32 AM', status: 'running' },
  { name: 'Text Normalization Agent', version: 'v1.8.3', successRate: 99.2, avgTime: '1.4s', p95: '2.6s', processed: 218, failed: 2, lastRun: '2024-04-29 10:31 AM', status: 'running' },
  { name: 'Section Mapping Agent', version: 'v3.1.0', successRate: 95.4, avgTime: '2.1s', p95: '4.2s', processed: 215, failed: 10, lastRun: '2024-04-29 10:30 AM', status: 'running' },
  { name: 'AI Scoring Agent', version: 'v4.0.2', successRate: 99.1, avgTime: '3.2s', p95: '6.1s', processed: 212, failed: 2, lastRun: '2024-04-29 10:32 AM', status: 'running' },
  { name: 'Score Aggregation Agent', version: 'v1.2.0', successRate: 100, avgTime: '0.6s', p95: '1.1s', processed: 210, failed: 0, lastRun: '2024-04-29 10:32 AM', status: 'idle' },
  { name: 'Report Generation Agent', version: 'v2.0.5', successRate: 98.5, avgTime: '1.8s', p95: '3.4s', processed: 210, failed: 3, lastRun: '2024-04-29 10:31 AM', status: 'idle' },
  { name: 'Email Dispatch Agent', version: 'v1.5.1', successRate: 100, avgTime: '0.6s', p95: '1.0s', processed: 70, failed: 0, lastRun: '2024-04-29 10:28 AM', status: 'idle' },
]

export default function AgentMetricsPage() {
  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div><h1 className="text-2xl font-bold text-white flex items-center gap-3"><Bot className="w-6 h-6 text-purple-400" /> Agent Performance Metrics</h1><p className="text-slate-400 text-sm mt-1">Individual pipeline agent health and throughput</p></div>
      <div className="grid gap-4">
        {AGENTS.map(a => (
          <div key={a.name} className="glass-card p-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
              <div className="flex items-center gap-3">
                <div className={`w-3 h-3 rounded-full ${a.status === 'running' ? 'bg-green-400 animate-pulse' : 'bg-slate-500'}`} />
                <div><p className="text-white font-semibold">{a.name}</p><p className="text-[10px] text-slate-500">{a.version} · Last run: {a.lastRun}</p></div>
              </div>
              <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold capitalize ${a.status === 'running' ? 'bg-green-500/15 text-green-400' : 'bg-slate-500/15 text-slate-400'}`}>{a.status}</span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
              <div className="p-2 rounded-xl bg-white/5 text-center"><p className="text-[10px] text-slate-500">Success</p><p className="text-sm font-bold text-green-400">{a.successRate}%</p></div>
              <div className="p-2 rounded-xl bg-white/5 text-center"><p className="text-[10px] text-slate-500">Avg Time</p><p className="text-sm font-bold text-white">{a.avgTime}</p></div>
              <div className="p-2 rounded-xl bg-white/5 text-center"><p className="text-[10px] text-slate-500">P95</p><p className="text-sm font-bold text-amber-400">{a.p95}</p></div>
              <div className="p-2 rounded-xl bg-white/5 text-center"><p className="text-[10px] text-slate-500">Processed</p><p className="text-sm font-bold text-raiya-300">{a.processed}</p></div>
              <div className="p-2 rounded-xl bg-white/5 text-center"><p className="text-[10px] text-slate-500">Failed</p><p className={`text-sm font-bold ${a.failed > 0 ? 'text-red-400' : 'text-green-400'}`}>{a.failed}</p></div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
