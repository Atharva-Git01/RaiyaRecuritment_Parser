'use client'
import { Brain, TrendingUp, Clock, AlertTriangle, CheckCircle } from 'lucide-react'

const DAILY = [
  { date: '2024-04-29', calls: 156, avgLatency: '3.1s', accuracy: 94.8, bufferTime: '1.0s', scoreGenTime: '3.2s', failures: 2, confidence: 88.4 },
  { date: '2024-04-28', calls: 132, avgLatency: '3.4s', accuracy: 93.2, bufferTime: '1.2s', scoreGenTime: '3.5s', failures: 4, confidence: 86.1 },
  { date: '2024-04-27', calls: 189, avgLatency: '2.9s', accuracy: 95.1, bufferTime: '0.9s', scoreGenTime: '2.8s', failures: 1, confidence: 89.7 },
  { date: '2024-04-26', calls: 98, avgLatency: '3.6s', accuracy: 91.4, bufferTime: '1.4s', scoreGenTime: '3.8s', failures: 5, confidence: 84.2 },
  { date: '2024-04-25', calls: 145, avgLatency: '3.0s', accuracy: 94.5, bufferTime: '1.1s', scoreGenTime: '3.1s', failures: 3, confidence: 87.9 },
  { date: '2024-04-24', calls: 167, avgLatency: '2.8s', accuracy: 96.0, bufferTime: '0.8s', scoreGenTime: '2.6s', failures: 0, confidence: 91.2 },
  { date: '2024-04-23', calls: 121, avgLatency: '3.3s', accuracy: 92.8, bufferTime: '1.3s', scoreGenTime: '3.4s', failures: 3, confidence: 85.5 },
]

export default function LlmMetricsPage() {
  const avg = (arr) => (arr.reduce((s, v) => s + v, 0) / arr.length).toFixed(1)
  const avgAcc = avg(DAILY.map(d => d.accuracy))
  const avgConf = avg(DAILY.map(d => d.confidence))
  const totalFails = DAILY.reduce((s, d) => s + d.failures, 0)

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div><h1 className="text-2xl font-bold text-white flex items-center gap-3"><Brain className="w-6 h-6 text-emerald-400" /> LLM Performance Metrics</h1><p className="text-slate-400 text-sm mt-1">Daily model performance tracking</p></div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: '7-Day Avg Accuracy', value: `${avgAcc}%`, color: 'text-green-400', bg: 'bg-green-500/10' },
          { label: '7-Day Avg Confidence', value: `${avgConf}%`, color: 'text-blue-400', bg: 'bg-blue-500/10' },
          { label: 'Total Failures', value: totalFails, color: 'text-red-400', bg: 'bg-red-500/10' },
          { label: 'Total LLM Calls', value: DAILY.reduce((s, d) => s + d.calls, 0), color: 'text-purple-400', bg: 'bg-purple-500/10' },
        ].map(s => (
          <div key={s.label} className={`glass-card p-4 ${s.bg} border-none`}>
            <p className="text-xs text-slate-500 mb-1">{s.label}</p>
            <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
          </div>
        ))}
      </div>

      <div className="glass-card overflow-hidden">
        <div className="p-4 border-b border-white/5"><h2 className="text-base font-bold text-white">Daily LLM Performance Log</h2></div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="border-b border-white/5">
              {['Date', 'Calls', 'Avg Latency', 'Score Gen Time', 'Buffer Time', 'Accuracy', 'Confidence', 'Failures'].map(h => (
                <th key={h} className="text-left px-4 py-2 text-xs text-slate-500 font-medium">{h}</th>
              ))}
            </tr></thead>
            <tbody>{DAILY.map(d => (
              <tr key={d.date} className="border-b border-white/5 hover:bg-white/5">
                <td className="px-4 py-3 text-slate-400 font-mono text-xs">{d.date}</td>
                <td className="px-4 py-3 text-white">{d.calls}</td>
                <td className="px-4 py-3 text-slate-300 font-mono text-xs">{d.avgLatency}</td>
                <td className="px-4 py-3 text-amber-300 font-mono text-xs">{d.scoreGenTime}</td>
                <td className="px-4 py-3 text-cyan-300 font-mono text-xs">{d.bufferTime}</td>
                <td className="px-4 py-3"><span className={`font-semibold ${d.accuracy >= 95 ? 'text-green-400' : d.accuracy >= 90 ? 'text-blue-400' : 'text-amber-400'}`}>{d.accuracy}%</span></td>
                <td className="px-4 py-3"><span className={`font-semibold ${d.confidence >= 88 ? 'text-green-400' : 'text-amber-400'}`}>{d.confidence}%</span></td>
                <td className="px-4 py-3">{d.failures === 0 ? <CheckCircle className="w-4 h-4 text-green-400" /> : <span className="text-red-400 font-semibold">{d.failures}</span>}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
