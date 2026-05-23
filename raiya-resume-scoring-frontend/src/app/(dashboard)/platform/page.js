'use client'
import { useState, useEffect } from 'react'
import { Upload, CheckCircle, Sparkles, ArrowRight, X, File, Lock, Briefcase, Eye, AlertTriangle, ChevronDown, ChevronUp, Send } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import toast from 'react-hot-toast'

export default function PlatformPage() {
  const router = useRouter()
  const [confirmedJob, setConfirmedJob] = useState(null)
  const [hydrated, setHydrated] = useState(false)
  const [showJdModal, setShowJdModal] = useState(false)
  const [showScoringAlert, setShowScoringAlert] = useState(false)
  const [scoringReady, setScoringReady] = useState(false)
  const [resumes, setResumes] = useState([])

  // Hydrate from localStorage after client mount
  useEffect(() => {
    let job = null
    try {
      const saved = localStorage.getItem('raiya_confirmed_job')
      if (saved) {
        const parsed = JSON.parse(saved)
        if (parsed && parsed.formData) job = parsed
      }
    } catch (e) { /* ignore */ }
    setConfirmedJob(job)
    setHydrated(true)
  }, [])

  const hasJob = hydrated && !!confirmedJob
  const fd = confirmedJob?.formData || {}
  const wt = confirmedJob?.weights || {}
  const totalWeight = Object.values(wt).reduce((s, v) => s + (v.weight || 0), 0)

  const handleViewJd = () => setShowJdModal(true)

  const handleReadyForScoring = () => {
    setShowJdModal(false)
    setShowScoringAlert(true)
  }

  const confirmScoring = () => {
    setShowScoringAlert(false)
    setScoringReady(true)
    toast.success('Resume upload unlocked! Upload resumes to start scoring.', { icon: '🚀', duration: 3000 })
  }

  const handleResumeClick = () => {
    if (!scoringReady) {
      toast.error('⚠️ View your JD and confirm scoring readiness first!')
      return
    }
    const demoFiles = [
      { name: 'Gurjas_Singh_Gandhi_Resume.pdf', size: '245 KB' },
      { name: 'Priya_Sharma_Resume.pdf', size: '189 KB' },
      { name: 'Arjun_Patel_Resume.pdf', size: '312 KB' },
      { name: 'Sneha_Reddy_Resume.pdf', size: '267 KB' },
      { name: 'Rahul_Menon_Resume.pdf', size: '198 KB' },
      { name: 'Ananya_Gupta_Resume.pdf', size: '223 KB' },
      { name: 'Vikram_Joshi_Resume.pdf', size: '156 KB' },
      { name: 'Kavitha_Nair_Resume.pdf', size: '278 KB' },
    ]
    setResumes(demoFiles)
    toast.success(`${demoFiles.length} resumes loaded!`)
  }

  const handleStartScoring = () => {
    if (!scoringReady) { toast.error('Complete the JD review first!'); return }
    toast.loading('Starting scoring pipeline...', { duration: 800 })
    setTimeout(() => router.push('/processing'), 800)
  }

  // Before hydration, show a simple non-blocking placeholder
  if (!hydrated) {
    return (
      <div className="max-w-5xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold t-heading flex items-center gap-3">
            <span className="text-3xl">📤</span> Recruiter Platform
          </h1>
          <p className="text-sm t-faint mt-1">Loading your workspace...</p>
        </div>
        <div className="glass-card p-12 flex items-center justify-center">
          <div className="w-8 h-8 border-2 border-raiya-400/30 border-t-raiya-400 rounded-full animate-spin" />
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold t-heading flex items-center gap-3">
          <span className="text-3xl">📤</span> Recruiter Platform
        </h1>
        <p className="text-sm t-faint mt-1">
          {hasJob ? 'Your job description is ready — upload resumes to start AI-powered scoring' : 'Create a Job Description first to unlock resume scoring'}
        </p>
      </div>

      {/* Step Indicator */}
      <div className="glass-card p-4">
        <div className="flex items-center justify-between text-xs sm:text-sm">
          {[
            { step: 1, label: 'Create JD', done: hasJob },
            { step: 2, label: 'Review & Confirm', done: scoringReady },
            { step: 3, label: 'Upload Resumes', done: resumes.length > 0 },
            { step: 4, label: 'Start Scoring', done: false },
          ].map((s, i) => (
            <div key={s.step} className="flex items-center gap-1.5 sm:gap-2">
              <div className={`w-7 h-7 sm:w-8 sm:h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all ${s.done ? 'bg-green-500 text-white' : 'text-slate-400'}`}
                style={!s.done ? { background: 'var(--input-bg)' } : undefined}>
                {s.done ? '✓' : s.step}
              </div>
              <span className={`hidden sm:inline ${s.done ? 'text-green-400' : 't-faintest'}`}>{s.label}</span>
              {i < 3 && <ArrowRight className="w-3 h-3 t-faintest mx-1" />}
            </div>
          ))}
        </div>
      </div>

      {/* ═══ No Job Created — Locked State ═══ */}
      {!hasJob && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="glass-card p-10 text-center space-y-5">
          <div className="w-20 h-20 rounded-2xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center mx-auto">
            <Lock className="w-10 h-10 text-amber-400" />
          </div>
          <div>
            <h2 className="text-xl font-bold t-heading mb-2">No Job Description Found</h2>
            <p className="text-sm t-faint max-w-md mx-auto">
              You need to create a Job Description with weight assignment before you can upload resumes and start scoring.
            </p>
          </div>
          <button
            onClick={() => router.push('/create-job')}
            className="px-8 py-3 rounded-xl bg-gradient-to-r from-raiya-600 to-raiya-500 hover:from-raiya-500 hover:to-raiya-400 text-white font-semibold text-sm transition-all shadow-lg shadow-raiya-500/20 inline-flex items-center gap-2"
          >
            <Briefcase className="w-5 h-5" /> Create Job Description <ArrowRight className="w-4 h-4" />
          </button>
        </motion.div>
      )}

      {/* ═══ Job Created — Show JD Card ═══ */}
      {hasJob && (
        <>
          {/* JD Summary Card */}
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="glass-card p-6">
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 rounded-xl bg-green-500/10 border border-green-500/20 flex items-center justify-center flex-shrink-0">
                  <CheckCircle className="w-6 h-6 text-green-400" />
                </div>
                <div>
                  <h2 className="text-lg font-bold t-heading">{fd.jobRole || 'Untitled Position'}</h2>
                  <div className="flex flex-wrap items-center gap-2 mt-1">
                    {fd.department && <span className="text-xs t-faint">🏢 {fd.department}</span>}
                    {fd.location && <span className="text-xs t-faint">📍 {fd.location}</span>}
                    {fd.workMode && <span className="text-xs t-faint">🏠 {fd.workMode}</span>}
                    {fd.employmentType && <span className="text-xs t-faint">💼 {fd.employmentType}</span>}
                  </div>
                  <div className="flex items-center gap-2 mt-2">
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-green-500/15 text-green-400 border border-green-500/20 font-semibold">
                      ✓ Confirmed
                    </span>
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-raiya-500/15 text-raiya-400 border border-raiya-500/20 font-semibold">
                      Weights: {totalWeight}/100
                    </span>
                    {confirmedJob?.confirmedAt && (
                      <span className="text-[10px] t-faintest">
                        Created {new Date(confirmedJob.confirmedAt).toLocaleDateString()}
                      </span>
                    )}
                  </div>
                </div>
              </div>

              <button
                onClick={handleViewJd}
                className="px-4 py-2 rounded-xl bg-raiya-600/20 text-raiya-400 text-sm font-medium border border-raiya-500/20 hover:bg-raiya-600/30 transition-all flex items-center gap-2 flex-shrink-0"
              >
                <Eye className="w-4 h-4" /> View Details
              </button>
            </div>
          </motion.div>

          {/* Ready for scoring prompt — shown if not yet confirmed */}
          {!scoringReady && (
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
              className="glass-card p-6 text-center space-y-4 border-2 border-dashed border-raiya-500/20"
            >
              <Sparkles className="w-8 h-8 text-raiya-400 mx-auto" />
              <h3 className="text-base font-semibold t-heading">Ready to start resume scoring?</h3>
              <p className="text-sm t-faint max-w-lg mx-auto">
                Review your Job Description details and weights by clicking &quot;View Details&quot; above, then confirm you&apos;re ready to begin scoring.
              </p>
              <button
                onClick={handleViewJd}
                className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-raiya-600 to-raiya-500 hover:from-raiya-500 hover:to-raiya-400 text-white text-sm font-semibold transition-all shadow-lg shadow-raiya-500/15 inline-flex items-center gap-2"
              >
                <Eye className="w-4 h-4" /> Review JD & Start Scoring
              </button>
            </motion.div>
          )}

          {/* Resume Upload Section — locked until scoring is confirmed */}
          <div className={`glass-card p-6 relative ${!scoringReady ? 'opacity-40' : ''}`}>
            {!scoringReady && (
              <div className="absolute inset-0 backdrop-blur-[1px] rounded-2xl z-10 flex items-center justify-center cursor-not-allowed"
                style={{ background: 'rgba(0,0,0,0.2)' }}
                onClick={() => toast.error('⚠️ Review your JD and confirm scoring readiness first!')}
              >
                <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-red-500/20 border border-red-500/30">
                  <Lock className="w-4 h-4 text-red-400" />
                  <span className="text-sm text-red-300 font-medium">Review JD First</span>
                </div>
              </div>
            )}
            <h2 className="text-lg font-semibold t-heading mb-4 flex items-center gap-2">
              <Upload className="w-5 h-5 text-raiya-400" /> Batch Resume Upload
              {resumes.length > 0 && <span className="text-xs bg-raiya-500/20 text-raiya-300 px-2 py-0.5 rounded-full">{resumes.length} files</span>}
            </h2>
            {resumes.length === 0 ? (
              <div onClick={handleResumeClick} className="border-2 border-dashed border-white/10 hover:border-raiya-500/40 rounded-2xl p-8 sm:p-12 text-center cursor-pointer transition-all hover:bg-raiya-500/5 group">
                <Upload className="w-12 h-12 t-faintest group-hover:text-raiya-400 mx-auto mb-4 transition-colors" />
                <p className="t-heading font-medium mb-1">Drop resumes here or click to upload</p>
                <p className="text-xs t-faintest">PDF, DOCX — up to 200 files</p>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="grid gap-2 max-h-64 overflow-y-auto pr-2">
                  {resumes.map((f, i) => (
                    <div key={i} className="flex items-center gap-3 p-2.5 rounded-xl border border-white/5 group hover:border-raiya-500/20 transition-all" style={{ background: 'var(--row-alt)' }}>
                      <File className="w-4 h-4 text-raiya-400 flex-shrink-0" />
                      <span className="text-sm t-muted truncate flex-1">{f.name}</span>
                      <span className="text-xs t-faintest">{f.size}</span>
                      <button onClick={() => setResumes(resumes.filter((_, j) => j !== i))} className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-500/20 rounded t-faintest hover:text-red-400 transition-all">
                        <X className="w-3 h-3" />
                      </button>
                    </div>
                  ))}
                </div>
                <button onClick={handleStartScoring} className="w-full py-3 rounded-xl bg-gradient-to-r from-raiya-600 to-raiya-500 hover:from-raiya-500 hover:to-raiya-400 text-white font-semibold flex items-center justify-center gap-2 transition-all shadow-lg shadow-raiya-500/20">
                  <Sparkles className="w-5 h-5" /> Start Scoring with {resumes.length} Resumes <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>
        </>
      )}

      {/* ═══ JD Details View Modal ═══ */}
      <AnimatePresence>
        {showJdModal && confirmedJob && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={() => setShowJdModal(false)} />
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.9, opacity: 0 }}
              className="relative w-full max-w-3xl max-h-[85vh] overflow-y-auto rounded-2xl shadow-2xl shadow-black/50 p-6 sm:p-8"
              style={{ background: 'var(--dropdown-bg)', border: '1px solid var(--glass-hover-border)' }}
            >
              <button onClick={() => setShowJdModal(false)} className="absolute top-4 right-4 p-2 rounded-lg t-faint hover:text-white transition-colors z-10">
                <X className="w-5 h-5" />
              </button>

              {/* JD Header */}
              <div className="mb-6">
                <h2 className="text-xl font-bold t-heading flex items-center gap-2">
                  <Briefcase className="w-5 h-5 text-raiya-400" /> {fd.jobRole}
                </h2>
                <p className="text-sm t-faint mt-1">{fd.department} Department</p>
              </div>

              {/* Details Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-6">
                {[
                  ['Employment', fd.employmentType], ['Work Mode', fd.workMode], ['Location', fd.location],
                  ['Salary', fd.salaryRange || 'N/A'], ['Positions', fd.openPositions || 'N/A'], ['Deadline', fd.deadline || 'N/A'],
                  ['Min Exp', fd.minExperience ? `${fd.minExperience}y` : 'N/A'], ['Max Exp', fd.maxExperience ? `${fd.maxExperience}y` : 'N/A'],
                  ['Qualification', fd.qualification || 'N/A'],
                ].map(([label, value]) => (
                  <div key={label} className="p-3 rounded-xl border border-white/5" style={{ background: 'var(--row-alt)' }}>
                    <span className="text-[10px] uppercase tracking-wider t-faintest font-semibold">{label}</span>
                    <p className="text-sm t-heading font-medium mt-0.5">{value}</p>
                  </div>
                ))}
              </div>

              {/* Skills */}
              {fd.requiredSkills?.length > 0 && (
                <div className="mb-4">
                  <span className="text-xs t-faint font-medium block mb-1.5">Required Skills</span>
                  <div className="flex flex-wrap gap-1.5">
                    {fd.requiredSkills.map(s => <span key={s} className="px-2.5 py-1 rounded-lg text-xs font-medium bg-raiya-500/15 text-raiya-300 border border-raiya-500/20">{s}</span>)}
                  </div>
                </div>
              )}

              {fd.technologies?.length > 0 && (
                <div className="mb-4">
                  <span className="text-xs t-faint font-medium block mb-1.5">Technologies</span>
                  <div className="flex flex-wrap gap-1.5">
                    {fd.technologies.map(t => <span key={t} className="px-2.5 py-1 rounded-lg text-xs font-medium bg-purple-500/15 text-purple-300 border border-purple-500/20">{t}</span>)}
                  </div>
                </div>
              )}

              {/* Responsibilities */}
              {fd.responsibilities?.length > 0 && fd.responsibilities.some(r => r?.trim()) && (
                <div className="mb-4">
                  <span className="text-xs t-faint font-medium block mb-2">Responsibilities</span>
                  <ul className="space-y-1.5">
                    {fd.responsibilities.filter(r => r?.trim()).map((r, i) => (
                      <li key={i} className="flex items-start gap-2 text-xs t-muted"><span className="text-raiya-400 mt-0.5">▸</span>{r}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Weight Breakdown */}
              <div className="mt-6 p-4 rounded-xl border border-white/5" style={{ background: 'var(--row-alt)' }}>
                <h4 className="text-sm font-semibold t-heading mb-3 flex items-center gap-2">
                  ⚖️ Weight Assignment
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-green-500/15 text-green-400 border border-green-500/20 font-mono">{totalWeight}/100</span>
                </h4>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  {Object.entries(wt).map(([key, sec]) => (
                    <div key={key} className="flex items-center justify-between text-xs p-2 rounded-lg" style={{ background: 'var(--input-bg)' }}>
                      <span className="t-muted capitalize">{key.replace(/_/g, ' ')}</span>
                      <span className={`font-mono font-bold ${sec.weight > 0 ? 'text-raiya-400' : 't-faintest'}`}>{sec.weight}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Action: Ready for Scoring */}
              {!scoringReady && (
                <button onClick={handleReadyForScoring}
                  className="w-full mt-6 py-3.5 rounded-xl bg-gradient-to-r from-green-600 to-emerald-500 hover:from-green-500 hover:to-emerald-400 text-white font-semibold text-sm transition-all shadow-lg shadow-green-500/20 flex items-center justify-center gap-2"
                >
                  <CheckCircle className="w-5 h-5" /> Looks Good — Start Resume Scoring
                </button>
              )}
              {scoringReady && (
                <div className="mt-6 flex items-center gap-2 justify-center text-sm text-green-400">
                  <CheckCircle className="w-4 h-4" /> Scoring is active — close to upload resumes
                </div>
              )}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ═══ Scoring Readiness Alert Modal ═══ */}
      <AnimatePresence>
        {showScoringAlert && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" />
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.9, opacity: 0 }}
              className="relative rounded-2xl shadow-2xl shadow-black/50 p-8 max-w-md w-full text-center space-y-5"
              style={{ background: 'var(--dropdown-bg)', border: '1px solid var(--glass-hover-border)' }}
            >
              <div className="w-16 h-16 rounded-2xl bg-raiya-500/10 border border-raiya-500/20 flex items-center justify-center mx-auto">
                <Sparkles className="w-8 h-8 text-raiya-400" />
              </div>
              <h3 className="text-xl font-bold t-heading">Are you ready for resume scoring?</h3>
              <p className="text-sm t-faint">
                Your Job Description for <strong className="t-heading">{fd.jobRole}</strong> has been reviewed. Click OK to unlock resume uploads and begin the AI-powered scoring pipeline.
              </p>
              <div className="flex gap-3 pt-1">
                <button onClick={() => { setShowScoringAlert(false); setShowJdModal(true) }}
                  className="flex-1 py-3 rounded-xl text-sm font-medium transition-all t-muted hover:text-white"
                  style={{ background: 'var(--input-bg)', border: '1px solid var(--input-border)' }}
                >
                  Review Again
                </button>
                <button onClick={confirmScoring}
                  className="flex-1 py-3 rounded-xl bg-gradient-to-r from-raiya-600 to-raiya-500 hover:from-raiya-500 hover:to-raiya-400 text-white text-sm font-semibold transition-all shadow-lg shadow-raiya-500/20 flex items-center justify-center gap-2"
                >
                  <CheckCircle className="w-4 h-4" /> Yes, Let&apos;s Go!
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
