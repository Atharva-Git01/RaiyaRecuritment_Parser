'use client'
import { Scale } from 'lucide-react'

const JD_DATA = [
  { jdId: 'JD-001', title: 'Senior Full Stack Developer', recruiter: 'REC-001', date: '2024-04-29', sections: 8, totalWeight: 100, accuracy: 95.1, resumesScored: 15, avgMatch: 78.4 },
  { jdId: 'JD-002', title: 'ML Engineer', recruiter: 'REC-002', date: '2024-04-28', sections: 7, totalWeight: 100, accuracy: 92.3, resumesScored: 12, avgMatch: 74.8 },
  { jdId: 'JD-003', title: 'DevOps Lead', recruiter: 'REC-001', date: '2024-04-28', sections: 8, totalWeight: 100, accuracy: 96.8, resumesScored: 28, avgMatch: 81.3 },
  { jdId: 'JD-004', title: 'Data Analyst', recruiter: 'REC-003', date: '2024-04-27', sections: 6, totalWeight: 100, accuracy: 88.5, resumesScored: 67, avgMatch: 69.8 },
  { jdId: 'JD-005', title: 'Frontend React Developer', recruiter: 'REC-003', date: '2024-04-27', sections: 7, totalWeight: 100, accuracy: 90.2, resumesScored: 34, avgMatch: 72.1 },
  { jdId: 'JD-006', title: 'Cloud Architect', recruiter: 'REC-002', date: '2024-04-26', sections: 8, totalWeight: 100, accuracy: 97.0, resumesScored: 15, avgMatch: 83.2 },
]

export default function JdAccuracyPage() {
  const avgAcc = (JD_DATA.reduce((s, j) => s + j.accuracy, 0) / JD_DATA.length).toFixed(1)
  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-white flex items-center gap-3"><Scale className="w-6 h-6 text-cyan-400" /> JD Weight Assignment Accuracy</h1>
      <p className="text-slate-400 text-sm">Accuracy of LLM-generated weights per JD against scoring outcomes</p>
      <div className="grid grid-cols-3 gap-3">
        {[{ l: 'Total JDs', v: JD_DATA.length, c: 'text-blue-400' }, { l: 'Avg Accuracy', v: `${avgAcc}%`, c: 'text-green-400' }, { l: 'Resumes Scored', v: JD_DATA.reduce((s, j) => s + j.resumesScored, 0), c: 'text-raiya-400' }].map(s => (
          <div key={s.l} className="glass-card p-4"><p className="text-xs text-slate-500">{s.l}</p><p className={`text-2xl font-bold ${s.c}`}>{s.v}</p></div>
        ))}
      </div>
      <div className="glass-card overflow-hidden overflow-x-auto">
        <table className="w-full text-sm">
          <thead><tr className="border-b border-white/5">{['JD ID', 'Title', 'Recruiter', 'Date', 'Sections', 'Weight', 'Accuracy', 'Resumes', 'Avg Match'].map(h => <th key={h} className="text-left px-3 py-2 text-[10px] text-slate-500 uppercase">{h}</th>)}</tr></thead>
          <tbody>{JD_DATA.map(j => (
            <tr key={j.jdId} className="border-b border-white/5 hover:bg-white/5">
              <td className="px-3 py-3 text-raiya-300 font-mono text-xs font-semibold">{j.jdId}</td>
              <td className="px-3 py-3 text-white text-xs font-medium">{j.title}</td>
              <td className="px-3 py-3 text-slate-400 text-xs">{j.recruiter}</td>
              <td className="px-3 py-3 text-slate-400 font-mono text-xs">{j.date}</td>
              <td className="px-3 py-3 text-white">{j.sections}</td>
              <td className="px-3 py-3 text-green-400 font-semibold">{j.totalWeight}%</td>
              <td className="px-3 py-3"><span className={`font-bold ${j.accuracy >= 95 ? 'text-green-400' : j.accuracy >= 90 ? 'text-blue-400' : 'text-amber-400'}`}>{j.accuracy}%</span></td>
              <td className="px-3 py-3 text-white">{j.resumesScored}</td>
              <td className="px-3 py-3"><span className={`font-semibold ${j.avgMatch >= 80 ? 'text-green-400' : j.avgMatch >= 70 ? 'text-blue-400' : 'text-amber-400'}`}>{j.avgMatch}</span></td>
            </tr>
          ))}</tbody>
        </table>
      </div>
    </div>
  )
}
