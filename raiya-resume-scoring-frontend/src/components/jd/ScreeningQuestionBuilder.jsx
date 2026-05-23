'use client'
import { Plus, Trash2, HelpCircle } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

const QUESTION_TYPES = [
  { value: 'yes_no', label: 'Yes / No' },
  { value: 'mcq', label: 'Multiple Choice' },
  { value: 'text', label: 'Text Answer' },
]

export default function ScreeningQuestionBuilder({ questions = [], onChange }) {
  const addQuestion = () => {
    onChange([...questions, { type: 'yes_no', question: '', options: [] }])
  }

  const updateQuestion = (index, field, value) => {
    const updated = [...questions]
    updated[index] = { ...updated[index], [field]: value }
    onChange(updated)
  }

  const removeQuestion = (index) => {
    onChange(questions.filter((_, i) => i !== index))
  }

  const addOption = (index) => {
    const updated = [...questions]
    updated[index].options = [...(updated[index].options || []), '']
    onChange(updated)
  }

  const updateOption = (qIndex, oIndex, value) => {
    const updated = [...questions]
    updated[qIndex].options[oIndex] = value
    onChange(updated)
  }

  const removeOption = (qIndex, oIndex) => {
    const updated = [...questions]
    updated[qIndex].options = updated[qIndex].options.filter((_, i) => i !== oIndex)
    onChange(updated)
  }

  return (
    <div>
      <label className="text-xs t-faint mb-2 block font-medium">Screening Questions</label>
      <div className="space-y-3">
        <AnimatePresence mode="popLayout">
          {questions.map((q, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="p-4 rounded-xl border border-white/5 hover:border-raiya-500/20 transition-colors"
              style={{ background: 'var(--row-alt)' }}
            >
              <div className="flex items-start justify-between gap-3 mb-3">
                <div className="flex items-center gap-2">
                  <HelpCircle className="w-4 h-4 text-raiya-400 flex-shrink-0" />
                  <span className="text-xs font-semibold t-muted">Q{i + 1}</span>
                </div>
                <div className="flex items-center gap-2">
                  <select
                    value={q.type}
                    onChange={e => updateQuestion(i, 'type', e.target.value)}
                    className="text-xs px-2 py-1 rounded-lg t-input focus:ring-2 focus:ring-raiya-500 focus:outline-none"
                  >
                    {QUESTION_TYPES.map(t => (
                      <option key={t.value} value={t.value} className="t-option">{t.label}</option>
                    ))}
                  </select>
                  <button onClick={() => removeQuestion(i)} className="p-1 rounded-lg text-red-400/50 hover:text-red-400 hover:bg-red-500/10 transition-all">
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              <input
                value={q.question}
                onChange={e => updateQuestion(i, 'question', e.target.value)}
                placeholder="Enter your question..."
                className="w-full px-3 py-2 rounded-xl t-input text-sm focus:ring-2 focus:ring-raiya-500 focus:outline-none mb-2"
              />

              {q.type === 'mcq' && (
                <div className="ml-4 space-y-2 mt-2">
                  {(q.options || []).map((opt, oi) => (
                    <div key={oi} className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full border border-raiya-500/30 flex-shrink-0" />
                      <input
                        value={opt}
                        onChange={e => updateOption(i, oi, e.target.value)}
                        placeholder={`Option ${oi + 1}`}
                        className="flex-1 px-2.5 py-1.5 rounded-lg t-input text-xs focus:ring-2 focus:ring-raiya-500 focus:outline-none"
                      />
                      <button onClick={() => removeOption(i, oi)} className="text-red-400/50 hover:text-red-400 transition-colors">
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  ))}
                  <button
                    onClick={() => addOption(i)}
                    className="text-xs text-raiya-400 hover:text-raiya-300 mt-1 flex items-center gap-1"
                  >
                    <Plus className="w-3 h-3" /> Add Option
                  </button>
                </div>
              )}

              {q.type === 'yes_no' && (
                <div className="flex items-center gap-3 ml-4 mt-2">
                  <span className="text-xs px-3 py-1 rounded-lg bg-green-500/10 text-green-400 border border-green-500/20">Yes</span>
                  <span className="text-xs px-3 py-1 rounded-lg bg-red-500/10 text-red-400 border border-red-500/20">No</span>
                </div>
              )}

              {q.type === 'text' && (
                <div className="ml-4 mt-2">
                  <div className="w-full h-8 rounded-lg border border-dashed border-white/10 flex items-center justify-center">
                    <span className="text-[10px] t-faintest">Free text response area</span>
                  </div>
                </div>
              )}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
      <button
        onClick={addQuestion}
        className="mt-3 flex items-center gap-2 px-4 py-2 rounded-xl border border-dashed border-raiya-500/30 text-raiya-400 text-sm hover:bg-raiya-500/10 hover:border-raiya-500/50 transition-all"
      >
        <Plus className="w-4 h-4" /> Add Screening Question
      </button>
    </div>
  )
}
