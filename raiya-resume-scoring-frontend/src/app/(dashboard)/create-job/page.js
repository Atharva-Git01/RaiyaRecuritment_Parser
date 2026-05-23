'use client'
import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { PenLine, Upload, Save, Send, X, CheckCircle2, AlertTriangle, Briefcase } from 'lucide-react'
import { useRouter } from 'next/navigation'
import toast from 'react-hot-toast'
import { DEMO_RECRUITER_PROFILE, DEMO_WEIGHT_PRESETS } from '@/data/static-data'
import JobForm from '@/components/jd/JobForm'
import WeightAssignment from '@/components/jd/WeightAssignment'
import UploadJD from '@/components/jd/UploadJD'
import JDPreview from '@/components/jd/JDPreview'

const TABS = [
  { id: 'manual', label: 'Manual Creation', icon: PenLine },
  { id: 'upload', label: 'Upload JD Document', icon: Upload },
]

const DEFAULT_WEIGHTS = {
  relevant_experience: { weight: 0, criteria: {} },
  experience: { weight: 0, criteria: {} },
  qualification: { weight: 0, criteria: {} },
  technologies: { weight: 0, criteria: {} },
  skills: { weight: 0, criteria: {} },
  position: { weight: 0, criteria: {} },
  tools: { weight: 0, criteria: {} },
  certifications: { weight: 0, criteria: {} },
  responsibilities: { weight: 0, criteria: {} },
  salary: { weight: 0, criteria: {} },
}

const STORAGE_KEYS = {
  draft: 'raiya_jd_draft',
  weights: 'raiya_jd_weights',
  confirmed: 'raiya_confirmed_job',
  weightsConfirmed: 'raiya_weights_confirmed',
}

export default function CreateJobPage() {
  const router = useRouter()
  const [activeTab, setActiveTab] = useState('manual')
  const [currentStep, setCurrentStep] = useState('basic')
  const [showPublishModal, setShowPublishModal] = useState(false)
  const [weightsConfirmed, setWeightsConfirmed] = useState(false)

  // Load recruiter profile
  const [profile, setProfile] = useState(DEMO_RECRUITER_PROFILE)
  useEffect(() => {
    try {
      const saved = localStorage.getItem('raiya_recruiter_profile')
      if (saved) setProfile(JSON.parse(saved))
    } catch {}
  }, [])

  // Form data — load from draft or auto-fill from recruiter profile
  const [formData, setFormData] = useState(() => {
    const defaults = {
      jobRole: DEMO_RECRUITER_PROFILE.preferredJobRole || '',
      department: DEMO_RECRUITER_PROFILE.department || '',
      workMode: DEMO_RECRUITER_PROFILE.defaultWorkMode || '',
      location: DEMO_RECRUITER_PROFILE.defaultLocation || '',
      employmentType: 'Full-time',
      salaryRange: '',
      openPositions: '',
      deadline: '',
      minExperience: '',
      maxExperience: '',
      qualification: '',
      preferredQualification: '',
      domainExpertise: '',
      requiredSkills: [],
      preferredSkills: [],
      softSkills: [],
      technologies: [],
      frameworks: [],
      databases: [],
      tools: [],
      cloud: [],
      responsibilities: [''],
      screeningQuestions: [],
    }
    return defaults
  })

  // Load saved draft on mount
  useEffect(() => {
    try {
      const savedDraft = localStorage.getItem(STORAGE_KEYS.draft)
      if (savedDraft) {
        setFormData(JSON.parse(savedDraft))
        toast('📝 Draft restored from your last session', { duration: 2000 })
      } else {
        // Auto-fill from profile
        setFormData(prev => ({
          ...prev,
          jobRole: profile.preferredJobRole || prev.jobRole,
          department: profile.department || prev.department,
          workMode: profile.defaultWorkMode || prev.workMode,
          location: profile.defaultLocation || prev.location,
        }))
      }
    } catch {}
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Weights
  const [weights, setWeights] = useState(DEFAULT_WEIGHTS)

  // Load saved weights on mount
  useEffect(() => {
    try {
      const savedWeights = localStorage.getItem(STORAGE_KEYS.weights)
      if (savedWeights) setWeights(JSON.parse(savedWeights))
      const wc = localStorage.getItem(STORAGE_KEYS.weightsConfirmed)
      if (wc === 'true') setWeightsConfirmed(true)
    } catch {}
  }, [])

  const presetWeights = DEMO_WEIGHT_PRESETS[formData.jobRole] || DEMO_WEIGHT_PRESETS['Python Backend Developer']
  const totalWeight = Object.values(weights).reduce((sum, s) => sum + (s.weight || 0), 0)

  // Auto-save draft to localStorage whenever form data or weights change
  const saveDraft = useCallback(() => {
    try {
      localStorage.setItem(STORAGE_KEYS.draft, JSON.stringify(formData))
      localStorage.setItem(STORAGE_KEYS.weights, JSON.stringify(weights))
    } catch {}
  }, [formData, weights])

  useEffect(() => {
    const timer = setTimeout(saveDraft, 1000) // debounced auto-save
    return () => clearTimeout(timer)
  }, [saveDraft])

  // Handle explicit save draft button
  const handleSaveDraft = () => {
    saveDraft()
    toast.success('Draft saved! Your changes will be here when you return.', { icon: '💾', duration: 3000 })
  }

  // Handle weight confirmation from WeightAssignment
  const handleWeightsConfirmed = () => {
    setWeightsConfirmed(true)
    try { localStorage.setItem(STORAGE_KEYS.weightsConfirmed, 'true') } catch {}
    toast.success('Weights confirmed and locked! ✓')
  }

  // Handle publish click — validate first
  const handlePublish = () => {
    if (!formData.jobRole?.trim()) {
      toast.error('Please fill in the Job Role before publishing')
      return
    }
    if (totalWeight !== 100) {
      toast.error('Total weight must equal 100 before publishing')
      return
    }
    if (!weightsConfirmed) {
      toast.error('Please confirm your weights first')
      return
    }
    setShowPublishModal(true)
  }

  // Confirm publish → save to confirmed job, route to platform
  const confirmPublish = () => {
    setShowPublishModal(false)
    const confirmedJob = {
      formData,
      weights,
      confirmedAt: new Date().toISOString(),
      status: 'confirmed',
    }
    try {
      localStorage.setItem(STORAGE_KEYS.confirmed, JSON.stringify(confirmedJob))
      // Clear draft since it's now confirmed
      localStorage.removeItem(STORAGE_KEYS.draft)
      localStorage.removeItem(STORAGE_KEYS.weights)
      localStorage.removeItem(STORAGE_KEYS.weightsConfirmed)
    } catch {}
    toast.success('Job Description created successfully! Redirecting to Platform...', { icon: '🎉', duration: 3000 })
    setTimeout(() => router.push('/platform'), 1500)
  }

  // Cancel publish → keep editing
  const cancelPublish = () => {
    setShowPublishModal(false)
    saveDraft()
    toast('Keep editing! Your data is auto-saved. 📝', { duration: 3000 })
  }

  return (
    <div className="space-y-6 max-w-[1400px] mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold t-heading flex items-center gap-3">
          <span className="text-3xl">💼</span> Create New Job Description
        </h1>
        <p className="text-sm t-faint mt-1">
          Build a structured JD manually or upload one for automatic extraction.
        </p>
        {/* Auto-save indicator */}
        <p className="text-[10px] t-faintest mt-2 flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
          Auto-saving enabled — your progress is saved automatically
        </p>
      </div>

      {/* Tabs */}
      <div className="glass-card p-1.5 inline-flex gap-1 rounded-xl">
        {TABS.map(tab => {
          const Icon = tab.icon
          const isActive = activeTab === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`relative flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                isActive ? 'text-white' : 't-faint hover:t-muted'
              }`}
            >
              {isActive && (
                <motion.div
                  layoutId="activeTab"
                  className="absolute inset-0 bg-gradient-to-r from-raiya-600 to-raiya-500 rounded-lg"
                  transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                />
              )}
              <span className="relative z-10 flex items-center gap-2">
                <Icon className="w-4 h-4" />
                {tab.label}
              </span>
            </button>
          )
        })}
      </div>

      {/* Tab Content */}
      <AnimatePresence mode="wait">
        {activeTab === 'manual' ? (
          <motion.div key="manual" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} transition={{ duration: 0.25 }}>
            {/* 2-column layout */}
            <div className="grid grid-cols-1 lg:grid-cols-[1fr,380px] gap-6">
              <div>
                <JobForm formData={formData} setFormData={setFormData} currentStep={currentStep} setCurrentStep={setCurrentStep} />
              </div>
              <div className="lg:self-start lg:sticky lg:top-20">
                <WeightAssignment
                  weights={weights}
                  setWeights={setWeights}
                  presetWeights={presetWeights}
                  onConfirm={handleWeightsConfirmed}
                />
                {/* Weight status badge */}
                {weightsConfirmed && (
                  <motion.div initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }} className="mt-3 flex items-center gap-2 px-4 py-2 rounded-xl bg-green-500/10 border border-green-500/20">
                    <CheckCircle2 className="w-4 h-4 text-green-400" />
                    <span className="text-xs text-green-400 font-medium">Weights confirmed and ready</span>
                  </motion.div>
                )}
              </div>
            </div>

            {/* Preview */}
            <div className="mt-8">
              <h3 className="text-base font-semibold t-heading mb-4 flex items-center gap-2">
                📄 Generated JD Preview
              </h3>
              <JDPreview formData={formData} />
            </div>

            {/* Action Buttons */}
            <div className="mt-6 flex flex-col sm:flex-row gap-3">
              <button onClick={handleSaveDraft} className="flex-1 py-3 rounded-xl border border-white/10 t-muted hover:border-white/20 hover:bg-white/5 hover:text-white font-semibold text-sm transition-all flex items-center justify-center gap-2">
                <Save className="w-4 h-4" /> Save Draft
              </button>
              <button
                onClick={handlePublish}
                className={`flex-1 py-3 rounded-xl font-semibold text-sm transition-all flex items-center justify-center gap-2 ${
                  weightsConfirmed && totalWeight === 100
                    ? 'bg-gradient-to-r from-green-600 to-emerald-500 hover:from-green-500 hover:to-emerald-400 text-white shadow-lg shadow-green-500/20'
                    : 'bg-white/5 t-faintest border border-white/10 cursor-not-allowed'
                }`}
                disabled={!weightsConfirmed || totalWeight !== 100}
              >
                <Send className="w-4 h-4" /> Create Job & Go to Platform
              </button>
            </div>
          </motion.div>
        ) : (
          <motion.div key="upload" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} transition={{ duration: 0.25 }}>
            <UploadJD />
          </motion.div>
        )}
      </AnimatePresence>

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
                  <span className="t-heading font-semibold">{formData.jobRole}</span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs t-muted">
                  <span>📍 {formData.location || 'N/A'}</span>
                  <span>🏢 {formData.department || 'N/A'}</span>
                  <span>💼 {formData.employmentType || 'N/A'}</span>
                  <span>🏠 {formData.workMode || 'N/A'}</span>
                </div>
                <div className="text-xs t-faint mt-1 flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3 text-green-400" />
                  Weights: {totalWeight}/100 confirmed
                </div>
              </div>

              <p className="text-sm t-faint">
                Once confirmed, you&apos;ll be redirected to the <strong className="t-heading">Platform</strong> to start resume scoring.
              </p>

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
