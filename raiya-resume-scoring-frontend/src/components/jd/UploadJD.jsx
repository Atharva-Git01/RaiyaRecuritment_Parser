'use client'
import { useState } from 'react'
import { Upload, FileText, CheckCircle2, Loader2, Sparkles, X, AlertTriangle, Briefcase, Send } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import toast from 'react-hot-toast'
import { DEMO_EXTRACTED_JD, DEMO_WEIGHT_PRESETS } from '@/data/static-data'
import WeightAssignment from './WeightAssignment'

const STAGES = [
  { label: 'Uploading document...', duration: 1200 },
  { label: 'Extracting content with AI...', duration: 1800 },
  { label: 'Generating weight suggestions...', duration: 1500 },
]

export default function UploadJD() {
  const router = useRouter()
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [stage, setStage] = useState(-1)
  const [extracted, setExtracted] = useState(null)
  const [weights, setWeights] = useState(null)
  const [weightsConfirmed, setWeightsConfirmed] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const [showPublishModal, setShowPublishModal] = useState(false)

  const totalWeight = weights ? Object.values(weights).reduce((s, v) => s + (v.weight || 0), 0) : 0

  const simulate = (f) => {
    setFile(f); setUploading(true); setStage(0); setExtracted(null); setWeights(null); setWeightsConfirmed(false)
    let s = 0
    const next = () => {
      if (s < STAGES.length - 1) { s++; setStage(s); setTimeout(next, STAGES[s].duration) }
      else setTimeout(() => {
        setUploading(false); setStage(-1)
        setExtracted(DEMO_EXTRACTED_JD)
        setWeights(DEMO_WEIGHT_PRESETS['Python Backend Developer'] || {})
        toast.success('JD extracted successfully!')
      }, 800)
    }
    setTimeout(next, STAGES[0].duration)
  }

  const onDrop = e => { e.preventDefault(); setDragOver(false); e.dataTransfer?.files?.[0] && simulate(e.dataTransfer.files[0]) }
  const onFile = e => e.target.files?.[0] && simulate(e.target.files[0])
  const clear = () => { setFile(null); setExtracted(null); setWeights(null); setStage(-1); setUploading(false); setWeightsConfirmed(false) }

  const handleWeightsConfirmed = () => {
    setWeightsConfirmed(true)
    toast.success('Weights confirmed! ✓')
  }

  const handlePublishClick = () => {
    if (!weightsConfirmed || totalWeight !== 100) {
      toast.error('Please confirm weights at 100 first')
      return
    }
    setShowPublishModal(true)
  }

  const confirmPublish = () => {
    setShowPublishModal(false)
    // Build formData from extracted JD
    const formData = {
      jobRole: extracted.jobRole,
      department: extracted.department,
      employmentType: extracted.employmentType,
      workMode: extracted.workMode,
      location: extracted.location,
      salaryRange: extracted.salaryRange,
      openPositions: extracted.openPositions || '',
      deadline: '',
      minExperience: extracted.experience?.min || '',
      maxExperience: extracted.experience?.max || '',
      qualification: extracted.qualification,
      preferredQualification: extracted.preferredQualification || '',
      domainExpertise: extracted.domainExpertise || '',
      requiredSkills: extracted.requiredSkills || [],
      preferredSkills: extracted.preferredSkills || [],
      softSkills: extracted.softSkills || [],
      technologies: extracted.technologies || [],
      frameworks: extracted.frameworks || [],
      databases: extracted.databases || [],
      tools: extracted.tools || [],
      cloud: extracted.cloud || [],
      responsibilities: extracted.responsibilities || [],
      screeningQuestions: extracted.screeningQuestions || [],
    }
    const confirmedJob = { formData, weights, confirmedAt: new Date().toISOString(), status: 'confirmed' }
    try {
      localStorage.setItem('raiya_confirmed_job', JSON.stringify(confirmedJob))
      localStorage.removeItem('raiya_jd_draft')
      localStorage.removeItem('raiya_jd_weights')
      localStorage.removeItem('raiya_weights_confirmed')
    } catch {}
    toast.success('Job Description created! Redirecting to Platform...', { icon: '🎉', duration: 3000 })
    setTimeout(() => router.push('/platform'), 1500)
  }

  const cancelPublish = () => {
    setShowPublishModal(false)
    toast('Keep editing! Your changes are saved. 📝', { duration: 3000 })
  }

  return (
    <div className="space-y-6">
      {/* Dropzone */}
      {!extracted && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
          className={`glass-card p-10 border-2 border-dashed transition-all cursor-pointer text-center ${dragOver ? 'border-raiya-400 bg-raiya-500/10' : uploading ? 'border-raiya-500/30' : 'border-white/10 hover:border-raiya-500/30'}`}
          onDragOver={e => { e.preventDefault(); setDragOver(true) }} onDragLeave={() => setDragOver(false)} onDrop={onDrop}
          onClick={() => !uploading && document.getElementById('jd-upload')?.click()}
        >
          <input id="jd-upload" type="file" accept=".pdf,.docx" onChange={onFile} className="hidden" />
          {uploading ? (
            <div className="space-y-4">
              <Loader2 className="w-12 h-12 text-raiya-400 animate-spin mx-auto" />
              {STAGES.map((st, i) => (
                <div key={i} className={`flex items-center justify-center gap-2 text-sm ${i < stage ? 'text-green-400' : i === stage ? 'text-raiya-400' : 't-faintest'}`}>
                  {i < stage ? <CheckCircle2 className="w-4 h-4" /> : i === stage ? <Loader2 className="w-4 h-4 animate-spin" /> : <div className="w-4 h-4 rounded-full border border-white/10" />}
                  <span>{st.label}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="space-y-3">
              <div className="w-16 h-16 rounded-2xl bg-raiya-500/10 border border-raiya-500/20 flex items-center justify-center mx-auto">
                <Upload className="w-8 h-8 text-raiya-400" />
              </div>
              <p className="text-sm font-semibold t-heading">Drop your JD document here</p>
              <p className="text-xs t-faint">PDF, DOCX • Max 10MB</p>
              <button className="px-5 py-2 rounded-xl bg-raiya-600/20 text-raiya-400 text-sm font-medium border border-raiya-500/20 hover:bg-raiya-600/30 transition-all">Browse Files</button>
            </div>
          )}
        </motion.div>
      )}

      {/* Extracted JD */}
      {extracted && (
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
          {/* File info */}
          <div className="glass-card p-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-green-500/10 border border-green-500/20 flex items-center justify-center"><FileText className="w-5 h-5 text-green-400" /></div>
              <div>
                <p className="text-sm font-medium t-heading">{file?.name || 'JD_Document.pdf'}</p>
                <p className="text-xs text-green-400 flex items-center gap-1"><CheckCircle2 className="w-3 h-3" /> Extracted</p>
              </div>
            </div>
            <button onClick={clear} className="p-2 rounded-lg t-faint hover:text-red-400 transition-all"><X className="w-4 h-4" /></button>
          </div>

          {/* Extracted Details */}
          <div className="glass-card p-6 space-y-5">
            <h3 className="text-base font-semibold t-heading flex items-center gap-2"><Sparkles className="w-4 h-4 text-raiya-400" /> Extracted JD Preview</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {[['Role', extracted.jobRole],['Dept', extracted.department],['Type', extracted.employmentType],['Mode', extracted.workMode],['Location', extracted.location],['Salary', extracted.salaryRange],['Exp', `${extracted.experience.min}-${extracted.experience.max}y`],['Qual', extracted.qualification],['Domain', extracted.domainExpertise]].map(([l,v]) => (
                <div key={l} className="p-3 rounded-xl border border-white/5" style={{ background: 'var(--row-alt)' }}>
                  <span className="text-[10px] uppercase tracking-wider t-faintest font-semibold">{l}</span>
                  <p className="text-sm t-heading font-medium mt-0.5">{v}</p>
                </div>
              ))}
            </div>
            {[['Required Skills', extracted.requiredSkills, 'raiya'],['Technologies', extracted.technologies, 'purple'],['Tools', extracted.tools, 'green']].map(([label, tags, c]) => (
              <div key={label}>
                <span className="text-xs t-faint font-medium block mb-1.5">{label}</span>
                <div className="flex flex-wrap gap-1.5">
                  {tags.map(t => <span key={t} className={`px-2.5 py-1 rounded-lg text-xs font-medium border ${c === 'raiya' ? 'bg-raiya-500/15 text-raiya-300 border-raiya-500/20' : c === 'purple' ? 'bg-purple-500/15 text-purple-300 border-purple-500/20' : 'bg-green-500/15 text-green-300 border-green-500/20'}`}>{t}</span>)}
                </div>
              </div>
            ))}
            <div>
              <span className="text-xs t-faint font-medium block mb-2">Responsibilities</span>
              <ul className="space-y-1.5">{extracted.responsibilities.map((r,i) => <li key={i} className="flex items-start gap-2 text-xs t-muted"><span className="text-raiya-400 mt-0.5">▸</span>{r}</li>)}</ul>
            </div>
          </div>

          {/* Weight Assignment */}
          {weights && (
            <WeightAssignment
              weights={weights}
              setWeights={setWeights}
              presetWeights={DEMO_WEIGHT_PRESETS['Python Backend Developer']}
              onConfirm={handleWeightsConfirmed}
            />
          )}

          {weightsConfirmed && (
            <motion.div initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-2 px-4 py-2 rounded-xl bg-green-500/10 border border-green-500/20">
              <CheckCircle2 className="w-4 h-4 text-green-400" />
              <span className="text-xs text-green-400 font-medium">Weights confirmed and ready</span>
            </motion.div>
          )}

          {/* Publish */}
          <button
            onClick={handlePublishClick}
            disabled={!weightsConfirmed || totalWeight !== 100}
            className={`w-full py-3.5 rounded-xl font-semibold text-sm transition-all flex items-center justify-center gap-2 ${
              weightsConfirmed && totalWeight === 100
                ? 'bg-gradient-to-r from-green-600 to-emerald-500 hover:from-green-500 hover:to-emerald-400 text-white shadow-lg shadow-green-500/20'
                : 'bg-white/5 t-faintest border border-white/10 cursor-not-allowed'
            }`}
          >
            <Send className="w-5 h-5" /> Create Job & Go to Platform
          </button>
        </motion.div>
      )}

      {/* ═══ Publish Confirmation Modal ═══ */}
      <AnimatePresence>
        {showPublishModal && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={cancelPublish} />
            <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.9, opacity: 0 }}
              className="relative rounded-2xl shadow-2xl shadow-black/50 p-8 max-w-lg w-full text-center space-y-5"
              style={{ background: 'var(--dropdown-bg)', border: '1px solid var(--glass-hover-border)' }}
            >
              <button onClick={cancelPublish} className="absolute top-4 right-4 p-1 rounded-lg t-faint hover:text-white transition-colors">
                <X className="w-5 h-5" />
              </button>
              <div className="w-16 h-16 rounded-2xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center mx-auto">
                <AlertTriangle className="w-8 h-8 text-amber-400" />
              </div>
              <h3 className="text-xl font-bold t-heading">Are you sure you want to create this job?</h3>
              <div className="text-left rounded-xl p-4 space-y-2" style={{ background: 'var(--row-alt)', border: '1px solid var(--divider)' }}>
                <div className="flex items-center gap-2 text-sm">
                  <Briefcase className="w-4 h-4 text-raiya-400" />
                  <span className="t-heading font-semibold">{extracted?.jobRole}</span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs t-muted">
                  <span>📍 {extracted?.location}</span>
                  <span>🏢 {extracted?.department}</span>
                  <span>💼 {extracted?.employmentType}</span>
                  <span>🏠 {extracted?.workMode}</span>
                </div>
                <div className="text-xs t-faint mt-1 flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3 text-green-400" /> Weights: {totalWeight}/100 confirmed
                </div>
              </div>
              <p className="text-sm t-faint">Once confirmed, you&apos;ll be redirected to the <strong className="t-heading">Platform</strong> to start resume scoring.</p>
              <div className="flex gap-3 pt-1">
                <button onClick={cancelPublish} className="flex-1 py-3 rounded-xl text-sm font-medium transition-all t-muted hover:text-white" style={{ background: 'var(--input-bg)', border: '1px solid var(--input-border)' }}>
                  No, Keep Editing
                </button>
                <button onClick={confirmPublish} className="flex-1 py-3 rounded-xl bg-gradient-to-r from-green-600 to-emerald-500 hover:from-green-500 hover:to-emerald-400 text-white text-sm font-semibold transition-all shadow-lg shadow-green-500/20 flex items-center justify-center gap-2">
                  <CheckCircle2 className="w-4 h-4" /> Yes, Create Job
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
