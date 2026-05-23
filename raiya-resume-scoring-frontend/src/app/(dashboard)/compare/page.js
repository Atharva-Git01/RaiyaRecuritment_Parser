'use client'
import { useState, useMemo } from 'react'
import { DEMO_CANDIDATES, DEMO_JD_WEIGHTS, getScoreColor, SECTION_LABELS } from '@/data/static-data'
import dynamic from 'next/dynamic'

const CompareRadar = dynamic(() => import('@/components/charts/CompareRadar'), { ssr: false })

/* ── helpers ─────────────────────────────────────── */
function jdExpectation(sectionKey) {
  const s = DEMO_JD_WEIGHTS.scoring[sectionKey]
  if (!s) return 0
  const vals = Object.values(s.criteria)
  if (!vals.length) return 0
  const max = Math.max(...vals)
  const avg = vals.reduce((a, b) => a + b, 0) / vals.length
  // Weighted: 70% max + 30% avg → realistic benchmark
  return Math.round(max * 0.7 + avg * 0.3)
}

function jdAlignPct(raw, sectionKey) {
  const exp = jdExpectation(sectionKey)
  if (!exp) return 100
  return Math.min(Math.round((raw / exp) * 100), 100)
}

function alignColor(pct) {
  if (pct >= 100) return '#10b981'
  if (pct >= 80)  return '#3b82f6'
  if (pct >= 60)  return '#f59e0b'
  return '#ef4444'
}

function alignLabel(pct) {
  if (pct >= 100) return 'Exceeds'
  if (pct >= 80)  return 'Meets'
  if (pct >= 60)  return 'Partial'
  return 'Gap'
}

function overallJdFit(candidate) {
  const sections = Object.keys(candidate.section_breakdown)
  const sum = sections.reduce((acc, key) => {
    const raw = candidate.section_breakdown[key]?.raw_score || 0
    return acc + jdAlignPct(raw, key)
  }, 0)
  return Math.round(sum / sections.length)
}

/* ── JD requirement items (for skills match) ────── */
const JD_REQUIRED_SKILLS = DEMO_JD_WEIGHTS.technologies
const JD_REQUIRED_TOOLS  = DEMO_JD_WEIGHTS.tools
const JD_REQUIRED_CERTS  = DEMO_JD_WEIGHTS.certifications

export default function ComparePage() {
  const [selected, setSelected] = useState([DEMO_CANDIDATES[0]?.id, DEMO_CANDIDATES[3]?.id])
  const [showJdOverlay, setShowJdOverlay] = useState(true)
  const [activeTab, setActiveTab] = useState('scores') // scores | skills | recommendation

  const candidates = selected.map(id => DEMO_CANDIDATES.find(c => c.id === id)).filter(Boolean)
  const sections = Object.keys(DEMO_CANDIDATES[0]?.section_breakdown || {})

  const toggleSelect = (idx, id) => {
    const next = [...selected]
    next[idx] = id
    setSelected(next)
  }

  /* ── build JD expectation "pseudo-candidate" for radar ── */
  const jdBaseline = useMemo(() => {
    const sb = {}
    sections.forEach(key => { sb[key] = { raw_score: jdExpectation(key) } })
    return { id: 'jd-baseline', name: 'JD Requirement', section_breakdown: sb }
  }, [])

  const radarCandidates = showJdOverlay ? [...candidates, jdBaseline] : candidates
  const RADAR_COLORS = ['#6366f1', '#f59e0b', '#10b981']

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* ── Header ──────────────────────────────────────── */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold t-heading flex items-center gap-3">
          <span className="text-3xl">⚖️</span> Compare Candidates
        </h1>
        <p className="t-muted text-sm mt-1">
          Side-by-side comparison against the Job Description: <span className="text-raiya-300 font-medium">{DEMO_JD_WEIGHTS.job_title}</span>
        </p>
      </div>

      {/* ── Selectors + JD toggle ────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[0, 1].map(idx => (
          <div key={idx} className="glass-card p-4">
            <label className="text-xs t-faint mb-2 block">Candidate {idx + 1}</label>
            <select value={selected[idx] || ''} onChange={e => toggleSelect(idx, e.target.value)}
              className="w-full px-3 py-2.5 rounded-xl text-sm focus:ring-2 focus:ring-raiya-500 focus:outline-none appearance-none t-input" style={{ borderRadius: '12px' }}>
              {DEMO_CANDIDATES.map(c => <option key={c.id} value={c.id} disabled={selected[1 - idx] === c.id} className="t-option">{c.name} ({c.final_score})</option>)}
            </select>
          </div>
        ))}
        {/* JD overlay toggle */}
        <div className="glass-card p-4 flex flex-col justify-between">
          <label className="text-xs t-faint mb-2 block">JD Baseline Overlay</label>
          <button onClick={() => setShowJdOverlay(!showJdOverlay)}
            className={`w-full px-3 py-2.5 rounded-xl text-sm font-medium transition-all border ${showJdOverlay
              ? 'bg-raiya-500/20 border-raiya-500/40 text-raiya-300'
              : 'border text-sm t-muted'
            }`}>
            {showJdOverlay ? '✅ JD Overlay ON' : '☐ JD Overlay OFF'}
          </button>
        </div>
      </div>

      {candidates.length === 2 && (
        <>
          {/* ── JD Fit Summary Cards ─────────────────────── */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {candidates.map((c, cidx) => {
              const fit = overallJdFit(c)
              return (
                <div key={`fit-${cidx}`} className="glass-card p-5 relative overflow-hidden">
                  {/* subtle accent bar */}
                  <div className="absolute top-0 left-0 h-1 rounded-b-full" style={{ width: `${fit}%`, background: alignColor(fit) }} />
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <p className="t-heading font-semibold text-base">{c.name}</p>
                      <p className="text-xs t-faint">vs {DEMO_JD_WEIGHTS.job_title}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-2xl font-bold" style={{ color: alignColor(fit) }}>{fit}%</p>
                      <p className="text-[10px] uppercase tracking-wider font-semibold" style={{ color: alignColor(fit) }}>{alignLabel(fit)} JD</p>
                    </div>
                  </div>
                  <div className="w-full h-2 rounded-full bg-white/5 overflow-hidden">
                    <div className="h-full rounded-full transition-all duration-700" style={{ width: `${Math.min(fit, 100)}%`, background: alignColor(fit) }} />
                  </div>
                  <div className="flex justify-between mt-2 text-[10px] t-faint">
                    <span>Score: <span className="font-bold t-heading" style={{ color: getScoreColor(c.final_score) }}>{c.final_score}</span></span>
                    <span>Skills matched: <span className="t-heading font-bold">{c.matched_skills.length}/{c.matched_skills.length + c.missing_skills.length}</span></span>
                  </div>
                </div>
              )
            })}
          </div>

          {/* ── Overlaid Radar ────────────────────────────── */}
          <div className="glass-card p-6">
            <h2 className="text-lg font-semibold t-heading mb-4">📊 Overlaid Radar {showJdOverlay && <span className="text-xs text-raiya-300 font-normal ml-2">— includes JD baseline</span>}</h2>
            <div className="h-[320px] sm:h-[400px]">
              <CompareRadar candidates={radarCandidates} />
            </div>
            <div className="flex flex-wrap justify-center gap-x-6 gap-y-2 mt-3">
              {radarCandidates.map((c, ri) => (
                <div key={`radar-legend-${ri}`} className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full" style={{ background: RADAR_COLORS[ri] }} />
                  <span className="text-xs t-muted">
                    {c.id === 'jd-baseline' ? '🎯 JD Requirement (avg)' : `${c.name} (${c.final_score})`}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* ── Tabs ─────────────────────────────────────── */}
          <div className="flex gap-2">
            {[
              { key: 'scores', label: '📊 Section Scores' },
              { key: 'skills', label: '🛠️ Skills vs JD' },
              { key: 'recommendation', label: '💡 Recommendation' },
            ].map(t => (
              <button key={t.key} onClick={() => setActiveTab(t.key)}
                className={`px-4 py-2 rounded-xl text-xs font-medium transition-all border ${activeTab === t.key
                  ? 'bg-raiya-500/20 border-raiya-500/40 text-raiya-300'
                  : 'border t-muted'
                }`}>
                {t.label}
              </button>
            ))}
          </div>

          {/* ── TAB: Section Scores + JD alignment ───────── */}
          {activeTab === 'scores' && (
            <div className="glass-card overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--divider)' }}>
                      <th className="text-left px-4 py-3 text-xs t-faint font-medium">Section</th>
                      {candidates.map((c, ci) => (
                        <th key={`name-${ci}`} className="text-center px-4 py-3 text-xs text-slate-500 font-medium">{c.name}</th>
                      ))}
                      <th className="text-center px-4 py-3 text-xs t-faint font-medium">Diff</th>
                      <th className="text-center px-4 py-3 text-xs t-faint font-medium">JD Expect</th>
                      {candidates.map((c, ci) => (
                        <th key={`align-${ci}`} className="text-center px-4 py-3 text-xs text-slate-500 font-medium">
                          {c.name.split(' ')[0]} JD%
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {/* Overall */}
                    <tr className="t-row-alt" style={{ borderBottom: '1px solid var(--divider)' }}>
                      <td className="px-4 py-3 font-bold t-heading">Overall Score</td>
                      {candidates.map((c, ci) => (
                        <td key={`score-${ci}`} className="px-4 py-3 text-center">
                          <span className="text-lg font-bold" style={{ color: getScoreColor(c.final_score) }}>{c.final_score}</span>
                        </td>
                      ))}
                      <td className="px-4 py-3 text-center">
                        <span className={`text-sm font-bold ${candidates[0].final_score > candidates[1].final_score ? 'text-green-400' : 'text-red-400'}`}>
                          {(candidates[0].final_score - candidates[1].final_score).toFixed(1)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center text-xs t-faint">—</td>
                      {candidates.map((c, ci) => {
                        const fit = overallJdFit(c)
                        return (
                          <td key={`of-${ci}`} className="px-4 py-3 text-center">
                            <span className="text-xs font-bold px-2 py-0.5 rounded-full" style={{ color: alignColor(fit), background: `${alignColor(fit)}15` }}>
                              {fit}%
                            </span>
                          </td>
                        )
                      })}
                    </tr>
                    {/* Per-section */}
                    {sections.map(key => {
                      const a = candidates[0].section_breakdown[key]?.raw_score || 0
                      const b = candidates[1].section_breakdown[key]?.raw_score || 0
                      const exp = jdExpectation(key)
                      const aAlign = jdAlignPct(a, key)
                      const bAlign = jdAlignPct(b, key)
                      const jdW = DEMO_JD_WEIGHTS.scoring[key]?.weight || 0
                      return (
                        <tr key={key} className="t-row-hover transition-colors" style={{ borderBottom: '1px solid var(--divider)' }}>
                          <td className="px-4 py-2.5 text-xs t-muted">
                            {SECTION_LABELS[key] || key}
                            <span className="ml-1 text-[10px] t-faintest">w:{jdW}</span>
                          </td>
                          <td className="px-4 py-2.5 text-center text-sm font-medium" style={{ color: getScoreColor(a) }}>{a}</td>
                          <td className="px-4 py-2.5 text-center text-sm font-medium" style={{ color: getScoreColor(b) }}>{b}</td>
                          <td className="px-4 py-2.5 text-center">
                            <span className={`text-xs font-bold ${a > b ? 'text-green-400' : a < b ? 'text-red-400' : 'text-slate-500'}`}>{a > b ? '+' : ''}{a - b}</span>
                          </td>
                          <td className="px-4 py-2.5 text-center text-xs t-faint font-mono">{exp}</td>
                          <td className="px-4 py-2.5 text-center">
                            <span className="text-[11px] font-bold" style={{ color: alignColor(aAlign) }}>{aAlign}%</span>
                          </td>
                          <td className="px-4 py-2.5 text-center">
                            <span className="text-[11px] font-bold" style={{ color: alignColor(bAlign) }}>{bAlign}%</span>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
              {/* Legend */}
              <div className="px-4 py-3 flex flex-wrap gap-4 text-[10px]" style={{ borderTop: '1px solid var(--divider)' }}>
                <span className="t-faint">JD% Legend:</span>
                {[
                  { label: '≥100% Exceeds', color: '#10b981' },
                  { label: '≥80% Meets',    color: '#3b82f6' },
                  { label: '≥60% Partial',  color: '#f59e0b' },
                  { label: '<60% Gap',      color: '#ef4444' },
                ].map(l => (
                  <span key={l.label} className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full inline-block" style={{ background: l.color }} />
                    <span style={{ color: l.color }}>{l.label}</span>
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* ── TAB: Skills vs JD ────────────────────────── */}
          {activeTab === 'skills' && (
            <div className="space-y-4">
              {/* Technologies */}
              <SkillsBlock
                title="💻 Technologies Required"
                required={JD_REQUIRED_SKILLS}
                candidates={candidates}
              />
              {/* Tools */}
              <SkillsBlock
                title="🔧 Tools Required"
                required={JD_REQUIRED_TOOLS}
                candidates={candidates}
              />
              {/* Certifications */}
              <SkillsBlock
                title="📜 Certifications Preferred"
                required={JD_REQUIRED_CERTS}
                candidates={candidates}
              />
              {/* Missing Skills Comparison */}
              <div className="glass-card p-5">
                <h3 className="text-sm font-semibold t-heading mb-3">⚠️ Missing Skills Comparison</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {candidates.map((c, ci) => (
                    <div key={`missing-${ci}`}>
                      <p className="text-xs t-faint mb-2">{c.name}</p>
                      {c.missing_skills.length === 0
                        ? <span className="text-xs text-green-400 font-medium">✅ No missing skills!</span>
                        : <div className="flex flex-wrap gap-1.5">
                            {c.missing_skills.map(s => (
                              <span key={s} className="px-2 py-0.5 text-[11px] rounded-full bg-red-500/15 text-red-400 border border-red-500/20">{s}</span>
                            ))}
                          </div>
                      }
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ── TAB: Recommendation ──────────────────────── */}
          {activeTab === 'recommendation' && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {candidates.map((c, ci) => {
                  const fit = overallJdFit(c)
                  return (
                    <div key={`rec-${ci}`} className="glass-card p-5 space-y-4">
                      <div className="flex items-center justify-between">
                        <h3 className="text-base font-semibold t-heading">{c.name}</h3>
                        <span className="px-2.5 py-1 text-xs font-bold rounded-full" style={{ color: alignColor(fit), background: `${alignColor(fit)}15`, border: `1px solid ${alignColor(fit)}30` }}>
                          {c.match_level}
                        </span>
                      </div>
                      {/* Strengths */}
                      <div>
                        <p className="text-xs text-green-400 font-semibold mb-1.5">✅ Strengths</p>
                        <ul className="space-y-1">
                          {c.strengths.map((s, i) => (
                            <li key={i} className="text-xs t-body flex gap-2">
                              <span className="text-green-500 mt-0.5 shrink-0">▸</span>{s}
                            </li>
                          ))}
                        </ul>
                      </div>
                      {/* Weaknesses */}
                      <div>
                        <p className="text-xs text-amber-400 font-semibold mb-1.5">⚠️ Weaknesses</p>
                        <ul className="space-y-1">
                          {c.weaknesses.map((w, i) => (
                            <li key={i} className="text-xs t-body flex gap-2">
                              <span className="text-amber-500 mt-0.5 shrink-0">▸</span>{w}
                            </li>
                          ))}
                        </ul>
                      </div>
                      {/* AI Recommendation */}
                      <div className="p-3 rounded-xl bg-raiya-500/10 border border-raiya-500/20">
                        <p className="text-[10px] uppercase tracking-wider text-raiya-300 font-semibold mb-1">🤖 AI Recommendation</p>
                        <p className="text-xs t-body leading-relaxed">{c.recommendation}</p>
                      </div>
                      {/* JD Fit Summary */}
                      <div className="p-3 rounded-xl bg-white/5 border border-white/10">
                        <p className="text-[10px] uppercase tracking-wider t-faint font-semibold mb-1">📋 JD Fit for {DEMO_JD_WEIGHTS.job_title}</p>
                        <div className="flex items-center gap-3 mt-1">
                          <div className="flex-1 h-2 rounded-full bg-white/5 overflow-hidden">
                            <div className="h-full rounded-full" style={{ width: `${Math.min(fit, 100)}%`, background: alignColor(fit) }} />
                          </div>
                          <span className="text-sm font-bold" style={{ color: alignColor(fit) }}>{fit}%</span>
                        </div>
                        <p className="text-[10px] t-faint mt-1">
                          Matched: {c.matched_skills.length} skills · Missing: {c.missing_skills.length} skills · Top section: {c.top_section}
                        </p>
                      </div>
                    </div>
                  )
                })}
              </div>
              {/* Verdict */}
              <div className="glass-card p-5">
                <h3 className="text-sm font-semibold t-heading mb-3">🏆 Verdict — Who fits the JD better?</h3>
                {(() => {
                  const fitA = overallJdFit(candidates[0])
                  const fitB = overallJdFit(candidates[1])
                  const winner = fitA >= fitB ? candidates[0] : candidates[1]
                  const loser  = fitA >= fitB ? candidates[1] : candidates[0]
                  const wFit   = Math.max(fitA, fitB)
                  const lFit   = Math.min(fitA, fitB)
                  const diff   = wFit - lFit
                  return (
                    <div className="flex items-start gap-4">
                      <div className="w-12 h-12 rounded-xl flex items-center justify-center text-2xl shrink-0" style={{ background: `${alignColor(wFit)}15` }}>🏆</div>
                      <div>
                        <p className="t-heading font-semibold">{winner.name} <span className="text-xs font-normal t-muted">leads by</span> <span className="font-bold" style={{ color: alignColor(wFit) }}>+{diff}%</span> <span className="text-xs font-normal t-muted">JD alignment</span></p>
                        <p className="text-xs t-muted mt-1">
                          {winner.name} ({wFit}% JD fit) vs {loser.name} ({lFit}% JD fit). 
                          {diff <= 5 ? ' Both candidates are very close — consider soft skills and culture fit.' : diff <= 15 ? ` ${winner.name} has a moderate edge in JD alignment.` : ` ${winner.name} significantly outperforms in JD requirements.`}
                        </p>
                      </div>
                    </div>
                  )
                })()}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}

/* ── SkillsBlock sub-component ───────────────────── */
function SkillsBlock({ title, required, candidates }) {
  return (
    <div className="glass-card p-5">
      <h3 className="text-sm font-semibold t-heading mb-3">{title}</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr style={{ borderBottom: '1px solid var(--divider)' }}>
              <th className="text-left py-2 pr-3 t-faint font-medium">Skill / Tool</th>
              {candidates.map((c, ci) => (
                <th key={`sb-h-${ci}`} className="text-center py-2 px-3 t-faint font-medium">{c.name.split(' ')[0]}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {required.map(item => (
              <tr key={item} className="t-row-hover transition-colors" style={{ borderBottom: '1px solid var(--divider)' }}>
                <td className="py-2 pr-3 t-body">{item}</td>
                {candidates.map((c, ci) => {
                  const has = c.matched_skills.some(s => s.toLowerCase() === item.toLowerCase())
                  return (
                    <td key={`sb-${ci}`} className="py-2 px-3 text-center">
                      {has
                        ? <span className="text-green-400 font-bold">✓</span>
                        : <span className="text-red-400 font-bold">✗</span>
                      }
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
