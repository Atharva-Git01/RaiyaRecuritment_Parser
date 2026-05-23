'use client'
import { useState } from 'react'
import { Sparkles, RotateCcw, CheckCircle2, AlertTriangle, XCircle, Loader2 } from 'lucide-react'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import CriteriaAccordion from './CriteriaAccordion'

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

const SECTION_LABELS = {
  relevant_experience: '🎯 Relevant Experience',
  experience: '📅 Experience',
  qualification: '🎓 Qualification',
  technologies: '💻 Technologies',
  skills: '🛠️ Skills',
  position: '📊 Position',
  tools: '🔧 Tools',
  certifications: '📜 Certifications',
  responsibilities: '📋 Responsibilities',
  salary: '💰 Salary',
}

export default function WeightAssignment({ weights, setWeights, presetWeights, onConfirm }) {
  const [suggesting, setSuggesting] = useState(false)

  const total = Object.values(weights).reduce((sum, s) => sum + (s.weight || 0), 0)
  const statusColor = total === 100 ? '#10b981' : total > 100 ? '#ef4444' : '#f59e0b'
  const statusIcon = total === 100 ? <CheckCircle2 className="w-4 h-4" /> : total > 100 ? <XCircle className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />
  const statusText = total === 100 ? 'Weights Balanced ✓' : total > 100 ? `Over by ${total - 100}` : `${100 - total} remaining`

  const handleAutoSuggest = () => {
    if (!presetWeights) {
      toast.error('No preset available for this role')
      return
    }
    setSuggesting(true)
    toast.loading('AI generating weight suggestions...', { id: 'ai-suggest' })

    setTimeout(() => {
      setWeights(presetWeights)
      setSuggesting(false)
      toast.success('AI weights applied! Review & adjust as needed.', { id: 'ai-suggest' })
    }, 2000)
  }

  const handleReset = () => {
    setWeights(DEFAULT_WEIGHTS)
    toast('Weights reset to zero', { icon: '🔄' })
  }

  const handleConfirm = () => {
    if (total !== 100) {
      toast.error('Total weight must equal 100')
      return
    }
    onConfirm?.(weights)
    toast.success('Weights confirmed and locked! ✓')
  }

  const updateSectionWeight = (section, value) => {
    setWeights(prev => ({
      ...prev,
      [section]: { ...prev[section], weight: value },
    }))
  }

  const updateCriteria = (section, key, value) => {
    setWeights(prev => ({
      ...prev,
      [section]: {
        ...prev[section],
        criteria: { ...prev[section].criteria, [key]: value },
      },
    }))
  }

  return (
    <div className="glass-card p-5 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-bold t-heading flex items-center gap-2">
          ⚖️ Weight Assignment
        </h3>
        <span className="text-[10px] px-2 py-0.5 rounded-full font-mono font-bold" style={{ color: statusColor, background: `${statusColor}15`, border: `1px solid ${statusColor}30` }}>
          {total}/100
        </span>
      </div>

      {/* Progress Bar */}
      <div>
        <div className="h-2.5 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.06)' }}>
          <motion.div
            className="h-full rounded-full"
            initial={false}
            animate={{
              width: `${Math.min(total, 105)}%`,
              backgroundColor: statusColor,
            }}
            transition={{ duration: 0.4, ease: 'easeOut' }}
          />
        </div>
        <div className="flex items-center justify-between mt-1.5">
          <div className="flex items-center gap-1" style={{ color: statusColor }}>
            {statusIcon}
            <span className="text-[11px] font-medium">{statusText}</span>
          </div>
        </div>
      </div>

      {/* Accordions */}
      <div className="space-y-2 max-h-[460px] overflow-y-auto pr-1">
        {Object.entries(weights).map(([key, section]) => (
          <CriteriaAccordion
            key={key}
            title={SECTION_LABELS[key] || key}
            weight={section.weight}
            onWeightChange={(v) => updateSectionWeight(key, v)}
            criteria={section.criteria}
            onCriteriaChange={(cKey, v) => updateCriteria(key, cKey, v)}
          />
        ))}
      </div>

      {/* Buttons */}
      <div className="grid grid-cols-3 gap-2 pt-2">
        <button
          onClick={handleAutoSuggest}
          disabled={suggesting}
          className="flex items-center justify-center gap-1.5 px-3 py-2.5 rounded-xl bg-gradient-to-r from-purple-600/80 to-raiya-600/80 hover:from-purple-500 hover:to-raiya-500 text-white text-xs font-semibold transition-all disabled:opacity-50 disabled:cursor-wait shadow-lg shadow-purple-500/10"
        >
          {suggesting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
          {suggesting ? 'Thinking...' : 'Auto Suggest'}
        </button>
        <button
          onClick={handleReset}
          className="flex items-center justify-center gap-1.5 px-3 py-2.5 rounded-xl text-xs font-semibold transition-all t-muted hover:text-white border border-white/10 hover:border-white/20 hover:bg-white/5"
        >
          <RotateCcw className="w-3.5 h-3.5" /> Reset
        </button>
        <button
          onClick={handleConfirm}
          className={`flex items-center justify-center gap-1.5 px-3 py-2.5 rounded-xl text-xs font-semibold transition-all shadow-lg ${
            total === 100
              ? 'bg-gradient-to-r from-green-600 to-emerald-500 hover:from-green-500 hover:to-emerald-400 text-white shadow-green-500/15'
              : 'bg-white/5 t-faintest cursor-not-allowed border border-white/5'
          }`}
          disabled={total !== 100}
        >
          <CheckCircle2 className="w-3.5 h-3.5" /> Confirm
        </button>
      </div>
    </div>
  )
}
