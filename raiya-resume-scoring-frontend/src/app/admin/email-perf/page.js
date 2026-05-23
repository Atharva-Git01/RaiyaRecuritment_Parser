'use client'
import { Mail, CheckCircle, XCircle, Clock } from 'lucide-react'

const EMAIL_LOG = [
  { date: '2024-04-29 10:32 AM', recruiter: 'REC-001', candidate: 'Gurjas Singh Gandhi', email: 'gurjas@email.com', score: 91.2, status: 'delivered', time: '1.2s', type: 'Interview' },
  { date: '2024-04-29 10:31 AM', recruiter: 'REC-001', candidate: 'Priya Sharma', email: 'priya@email.com', score: 86.5, status: 'delivered', time: '0.8s', type: 'Interview' },
  { date: '2024-04-28 04:15 PM', recruiter: 'REC-002', candidate: 'Rahul Menon', email: 'rahul@email.com', score: 72.1, status: 'delivered', time: '0.9s', type: 'Interview' },
  { date: '2024-04-28 04:14 PM', recruiter: 'REC-002', candidate: 'Arjun Patel', email: 'arjun@email.com', score: 82.4, status: 'bounced', time: '—', type: 'Interview' },
  { date: '2024-04-27 02:45 PM', recruiter: 'REC-003', candidate: 'Kavitha Nair', email: 'kavitha@email.com', score: 65.8, status: 'delivered', time: '1.1s', type: 'Update' },
]

const SB = { delivered: 'bg-green-500/15 text-green-400', bounced: 'bg-red-500/15 text-red-400' }

export default function EmailPerfPage() {
  const d = EMAIL_LOG.filter(e => e.status === 'delivered').length
  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-white flex items-center gap-3"><Mail className="w-6 h-6 text-pink-400" /> Email Performance</h1>
      <div className="grid grid-cols-3 gap-3">
        {[{ l: 'Total', v: EMAIL_LOG.length, c: 'text-blue-400' }, { l: 'Delivered', v: d, c: 'text-green-400' }, { l: 'Rate', v: `${((d / EMAIL_LOG.length) * 100).toFixed(0)}%`, c: 'text-emerald-400' }].map(s => (
          <div key={s.l} className="glass-card p-4"><p className="text-xs text-slate-500">{s.l}</p><p className={`text-2xl font-bold ${s.c}`}>{s.v}</p></div>
        ))}
      </div>
      <div className="glass-card overflow-hidden overflow-x-auto">
        <table className="w-full text-sm">
          <thead><tr className="border-b border-white/5">{['Date', 'Recruiter', 'Candidate', 'Score', 'Type', 'Status', 'Time'].map(h => <th key={h} className="text-left px-3 py-2 text-[10px] text-slate-500">{h}</th>)}</tr></thead>
          <tbody>{EMAIL_LOG.map((e, i) => (
            <tr key={i} className="border-b border-white/5 hover:bg-white/5">
              <td className="px-3 py-3 text-slate-400 text-[11px] font-mono">{e.date}</td>
              <td className="px-3 py-3 text-white text-xs">{e.recruiter}</td>
              <td className="px-3 py-3 text-white text-xs">{e.candidate}</td>
              <td className="px-3 py-3 text-green-400 font-bold text-xs">{e.score}</td>
              <td className="px-3 py-3 text-slate-400 text-xs">{e.type}</td>
              <td className="px-3 py-3"><span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${SB[e.status]}`}>{e.status}</span></td>
              <td className="px-3 py-3 text-slate-400 font-mono text-xs">{e.time}</td>
            </tr>
          ))}</tbody>
        </table>
      </div>
    </div>
  )
}
