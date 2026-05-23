'use client'
import { Clock, TrendingDown } from 'lucide-react'

const BATCHES = [
  { id: 'BATCH-029', date: '2024-04-29', recruiter: 'REC-001', resumes: 15, uploadTime: '2.1s', extractionTime: '58.4s', normTime: '18.2s', scoringTime: '42.6s', aggTime: '8.4s', reportTime: '24.1s', totalTime: '2m 34s', bufferTime: '12.8s' },
  { id: 'BATCH-028', date: '2024-04-28', recruiter: 'REC-002', resumes: 12, uploadTime: '1.8s', extractionTime: '45.2s', normTime: '14.6s', scoringTime: '35.8s', aggTime: '6.2s', reportTime: '18.4s', totalTime: '2m 02s', bufferTime: '10.2s' },
  { id: 'BATCH-027', date: '2024-04-28', recruiter: 'REC-001', resumes: 28, uploadTime: '3.4s', extractionTime: '112.8s', normTime: '35.6s', scoringTime: '82.4s', aggTime: '14.8s', reportTime: '46.2s', totalTime: '4m 55s', bufferTime: '24.6s' },
  { id: 'BATCH-026', date: '2024-04-27', recruiter: 'REC-003', resumes: 67, uploadTime: '8.2s', extractionTime: '268.4s', normTime: '84.2s', scoringTime: '198.6s', aggTime: '32.4s', reportTime: '108.6s', totalTime: '11m 40s', bufferTime: '58.2s' },
]

export default function ProcessingTimePage() {
  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div><h1 className="text-2xl font-bold text-white flex items-center gap-3"><Clock className="w-6 h-6 text-amber-400" /> Processing Timeframes</h1><p className="text-slate-400 text-sm mt-1">Per-batch document processing time breakdown</p></div>
      <div className="glass-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="border-b border-white/5">
              {['Batch', 'Date', 'Recruiter', 'Resumes', 'Upload', 'Extraction', 'Normalize', 'Scoring', 'Aggregate', 'Report', 'Buffer', 'Total'].map(h => (
                <th key={h} className="text-left px-3 py-2 text-[10px] text-slate-500 font-medium uppercase whitespace-nowrap">{h}</th>
              ))}
            </tr></thead>
            <tbody>{BATCHES.map(b => (
              <tr key={b.id} className="border-b border-white/5 hover:bg-white/5">
                <td className="px-3 py-3 text-raiya-300 font-mono text-xs font-semibold">{b.id}</td>
                <td className="px-3 py-3 text-slate-400 font-mono text-xs">{b.date}</td>
                <td className="px-3 py-3 text-white text-xs">{b.recruiter}</td>
                <td className="px-3 py-3 text-white font-semibold">{b.resumes}</td>
                <td className="px-3 py-3 text-green-300 font-mono text-xs">{b.uploadTime}</td>
                <td className="px-3 py-3 text-amber-300 font-mono text-xs">{b.extractionTime}</td>
                <td className="px-3 py-3 text-cyan-300 font-mono text-xs">{b.normTime}</td>
                <td className="px-3 py-3 text-purple-300 font-mono text-xs">{b.scoringTime}</td>
                <td className="px-3 py-3 text-blue-300 font-mono text-xs">{b.aggTime}</td>
                <td className="px-3 py-3 text-pink-300 font-mono text-xs">{b.reportTime}</td>
                <td className="px-3 py-3 text-slate-400 font-mono text-xs">{b.bufferTime}</td>
                <td className="px-3 py-3 text-white font-bold font-mono text-xs">{b.totalTime}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
