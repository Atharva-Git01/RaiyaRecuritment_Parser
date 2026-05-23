'use client'
import { useState } from 'react'
import { ChevronDown } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import WeightSlider from './WeightSlider'

export default function CriteriaAccordion({ title, weight, onWeightChange, criteria = {}, onCriteriaChange, maxWeight = 30 }) {
  const [open, setOpen] = useState(false)
  const criteriaEntries = Object.entries(criteria)

  return (
    <div className="rounded-xl border border-white/5 overflow-hidden transition-colors hover:border-raiya-500/15"
      style={{ background: 'var(--row-alt)' }}
    >
      {/* Header */}
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-3 transition-colors hover:bg-raiya-500/5"
      >
        <div className="flex items-center gap-3">
          <ChevronDown className={`w-4 h-4 t-faint transition-transform duration-300 ${open ? 'rotate-180' : ''}`} />
          <span className="text-sm font-medium t-heading">{title}</span>
        </div>
        <div className="flex items-center gap-2">
          <div
            className="h-1.5 w-16 rounded-full overflow-hidden"
            style={{ background: 'rgba(255,255,255,0.08)' }}
          >
            <motion.div
              className="h-full rounded-full bg-gradient-to-r from-raiya-600 to-raiya-400"
              initial={false}
              animate={{ width: `${Math.min((weight / maxWeight) * 100, 100)}%` }}
              transition={{ duration: 0.3 }}
            />
          </div>
          <span className={`text-xs font-mono font-bold w-6 text-right ${weight > 0 ? 'text-raiya-400' : 't-faintest'}`}>
            {weight}
          </span>
        </div>
      </button>

      {/* Content */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: 'easeInOut' }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4 space-y-3" style={{ borderTop: '1px solid var(--divider)' }}>
              {/* Section Weight */}
              <div className="pt-3">
                <WeightSlider
                  label="Section Weight"
                  value={weight}
                  onChange={onWeightChange}
                  max={maxWeight}
                />
              </div>

              {/* Criteria */}
              {criteriaEntries.length > 0 && (
                <div className="space-y-2 pt-2">
                  <span className="text-[10px] uppercase tracking-wider t-faintest font-semibold">Criteria Breakdown</span>
                  {criteriaEntries.map(([key, val]) => (
                    <WeightSlider
                      key={key}
                      label={key}
                      value={val}
                      onChange={(v) => onCriteriaChange(key, v)}
                      max={15}
                    />
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
