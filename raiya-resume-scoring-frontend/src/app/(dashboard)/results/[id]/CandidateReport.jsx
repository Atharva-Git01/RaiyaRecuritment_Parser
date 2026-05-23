'use client'
import { DEMO_CANDIDATES, getScoreColor, SECTION_LABELS } from '@/data/static-data'
import { ArrowLeft, Download, CheckCircle, XCircle, Star, TrendingUp, FileText } from 'lucide-react'
import Link from 'next/link'
import dynamic from 'next/dynamic'
import toast from 'react-hot-toast'

const RadarChartComponent = dynamic(() => import('@/components/charts/RadarChart'), { ssr: false })

export default function CandidateReport({ id }) {
  const candidate = DEMO_CANDIDATES.find(c => c.id === id)
  if (!candidate) return <div className="text-center py-20 text-slate-400">Candidate not found</div>

  const sections = Object.entries(candidate.section_breakdown)
  const scoreColor = getScoreColor(candidate.final_score)
  const circumference = 2 * Math.PI * 54
  const offset = circumference - (candidate.final_score / 100) * circumference

  const handleDownloadReport = () => {
    const content = [
      '════════════════════════════════════════════════════',
      '   RAIYA: Recruiting Resume Scoring System',
      '   Candidate Screening Report',
      '   Powered by SpeedTech.ai',
      '════════════════════════════════════════════════════',
      '', `Report Generated: ${new Date().toLocaleString()}`, '',
      '── CANDIDATE INFORMATION ──────────────────────────',
      `Name:    ${candidate.name}`, `Email:   ${candidate.email}`, `Resume:  ${candidate.resume_file}`, '',
      '── OVERALL SCORE ─────────────────────────────────',
      `Final Score:  ${candidate.final_score} / 100`, `Status:       ${candidate.score_status}`,
      `Match Level:  ${candidate.match_level}`, `Top Section:  ${candidate.top_section}`, '',
      '── SECTION BREAKDOWN ─────────────────────────────',
      ...sections.map(([key, d]) => `  ${(SECTION_LABELS[key]||key).padEnd(28)} Raw:${String(d.raw_score).padStart(3)}  W:${String(d.jd_weight).padStart(4)}  Wtd:${d.weighted_contribution.toFixed(1).padStart(5)}`),
      '', '── MATCHED SKILLS ────────────────────────────────',
      candidate.matched_skills.join(', ') || 'None',
      '', '── MISSING SKILLS ────────────────────────────────',
      candidate.missing_skills.join(', ') || 'None',
      '', '── STRENGTHS ─────────────────────────────────────',
      ...candidate.strengths.map(s => `  ✓ ${s}`),
      '', '── WEAKNESSES ────────────────────────────────────',
      ...candidate.weaknesses.map(w => `  ✗ ${w}`),
      '', '── AI RECOMMENDATION ─────────────────────────────',
      candidate.recommendation, '',
      '════════════════════════════════════════════════════',
    ].join('\n')
    const blob = new Blob([content], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a'); a.href = url; a.download = `${candidate.name.replace(/\s/g,'_')}_Report.txt`; a.click()
    URL.revokeObjectURL(url)
    toast.success('Report downloaded!')
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <Link href="/results" className="p-2 rounded-lg hover:bg-white/5 text-slate-400 hover:text-white transition-colors"><ArrowLeft className="w-5 h-5" /></Link>
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-white">{candidate.name}</h1>
            <p className="text-sm text-slate-400">{candidate.email} · {candidate.resume_file}</p>
          </div>
        </div>
        <button onClick={handleDownloadReport} className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-raiya-600/20 border border-raiya-500/30 text-raiya-300 text-sm hover:bg-raiya-600/30 transition-colors">
          <FileText className="w-4 h-4" /> Download Report
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="glass-card p-6 flex flex-col items-center justify-center sm:col-span-2 lg:col-span-1">
          <div className="score-circle mb-3">
            <svg width="130" height="130">
              <circle cx="65" cy="65" r="54" fill="none" strokeWidth="8" className="score-circle-bg" />
              <circle cx="65" cy="65" r="54" fill="none" strokeWidth="8" stroke={scoreColor} strokeDasharray={circumference} strokeDashoffset={offset} strokeLinecap="round" className="score-circle-fill" />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-3xl font-black" style={{ color: scoreColor }}>{candidate.final_score}</span>
              <span className="text-xs text-slate-500">/100</span>
            </div>
          </div>
          <span className="px-3 py-1 rounded-full text-xs font-medium" style={{ background: `${scoreColor}22`, color: scoreColor }}>{candidate.score_status}</span>
        </div>
        {[
          { label: 'Match Level', value: candidate.match_level, icon: TrendingUp },
          { label: 'Top Section', value: candidate.top_section, icon: Star },
          { label: 'Skills Matched', value: `${candidate.matched_skills.length}/${candidate.matched_skills.length + candidate.missing_skills.length}`, icon: CheckCircle },
        ].map(s => (
          <div key={s.label} className="glass-card p-4 flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-raiya-500/10 flex items-center justify-center flex-shrink-0"><s.icon className="w-5 h-5 text-raiya-400" /></div>
            <div><p className="text-xs text-slate-500">{s.label}</p><p className="text-sm font-semibold text-white">{s.value}</p></div>
          </div>
        ))}
      </div>

      <div className="glass-card p-6">
        <h2 className="text-lg font-semibold text-white mb-4">📊 Section Score Radar</h2>
        <div className="h-[300px] sm:h-[350px]"><RadarChartComponent sections={sections} /></div>
      </div>

      <div className="glass-card p-6">
        <h2 className="text-lg font-semibold text-white mb-4">📈 Section Breakdown</h2>
        <div className="space-y-3">
          {sections.map(([key, data]) => (
            <div key={key} className="flex items-center gap-3">
              <span className="text-xs text-slate-400 w-36 truncate">{SECTION_LABELS[key] || key}</span>
              <div className="flex-1 h-3 bg-white/5 rounded-full overflow-hidden">
                <div className="h-full rounded-full transition-all duration-1000" style={{ width: `${data.raw_score}%`, background: getScoreColor(data.raw_score) }} />
              </div>
              <span className="text-xs font-mono text-white w-8 text-right">{data.raw_score}</span>
              <span className="text-[10px] text-slate-500 w-12 text-right">w:{data.jd_weight}</span>
              <span className="text-xs font-bold w-12 text-right" style={{ color: getScoreColor(data.raw_score) }}>{data.weighted_contribution.toFixed(1)}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="glass-card p-5">
          <h3 className="text-sm font-semibold text-green-400 mb-3 flex items-center gap-2"><CheckCircle className="w-4 h-4" /> Matched Skills ({candidate.matched_skills.length})</h3>
          <div className="flex flex-wrap gap-2">{candidate.matched_skills.map(s => <span key={s} className="px-2.5 py-1 rounded-lg bg-green-500/10 text-green-300 text-xs border border-green-500/20">{s}</span>)}</div>
        </div>
        <div className="glass-card p-5">
          <h3 className="text-sm font-semibold text-red-400 mb-3 flex items-center gap-2"><XCircle className="w-4 h-4" /> Missing Skills ({candidate.missing_skills.length})</h3>
          <div className="flex flex-wrap gap-2">{candidate.missing_skills.length > 0 ? candidate.missing_skills.map(s => <span key={s} className="px-2.5 py-1 rounded-lg bg-red-500/10 text-red-300 text-xs border border-red-500/20">{s}</span>) : <span className="text-xs text-slate-500">No gaps — all skills matched!</span>}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="glass-card p-5">
          <h3 className="text-sm font-semibold text-green-400 mb-3">✅ Strengths</h3>
          <ul className="space-y-2">{candidate.strengths.map((s, i) => <li key={i} className="text-xs text-slate-300 flex items-start gap-2"><span className="text-green-500 mt-0.5">•</span>{s}</li>)}</ul>
        </div>
        <div className="glass-card p-5">
          <h3 className="text-sm font-semibold text-amber-400 mb-3">⚠️ Weaknesses</h3>
          <ul className="space-y-2">{candidate.weaknesses.map((w, i) => <li key={i} className="text-xs text-slate-300 flex items-start gap-2"><span className="text-amber-500 mt-0.5">•</span>{w}</li>)}</ul>
        </div>
      </div>

      <div className="glass-card p-5">
        <h3 className="text-sm font-semibold text-raiya-400 mb-3">💡 AI Recommendation</h3>
        <p className="text-sm text-slate-300 leading-relaxed">{candidate.recommendation}</p>
      </div>
    </div>
  )
}
