'use client'
import { Plus, Trash2, GripVertical } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

export default function ResponsibilityBuilder({ responsibilities = [], onChange }) {
  const addItem = () => {
    onChange([...responsibilities, ''])
  }

  const updateItem = (index, value) => {
    const updated = [...responsibilities]
    updated[index] = value
    onChange(updated)
  }

  const removeItem = (index) => {
    onChange(responsibilities.filter((_, i) => i !== index))
  }

  return (
    <div>
      <label className="text-xs t-faint mb-2 block font-medium">Responsibilities</label>
      <div className="space-y-2">
        <AnimatePresence mode="popLayout">
          {responsibilities.map((item, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              className="flex items-center gap-2 group"
            >
              <GripVertical className="w-4 h-4 t-faintest flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity cursor-grab" />
              <span className="text-xs t-faintest font-mono w-6 text-right flex-shrink-0">{i + 1}.</span>
              <input
                value={item}
                onChange={e => updateItem(i, e.target.value)}
                placeholder={`Responsibility ${i + 1}...`}
                className="flex-1 px-3 py-2 rounded-xl t-input text-sm focus:ring-2 focus:ring-raiya-500 focus:outline-none"
              />
              <button
                onClick={() => removeItem(i)}
                className="p-1.5 rounded-lg text-red-400/50 hover:text-red-400 hover:bg-red-500/10 transition-all opacity-0 group-hover:opacity-100"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
      <button
        onClick={addItem}
        className="mt-3 flex items-center gap-2 px-4 py-2 rounded-xl border border-dashed border-raiya-500/30 text-raiya-400 text-sm hover:bg-raiya-500/10 hover:border-raiya-500/50 transition-all"
      >
        <Plus className="w-4 h-4" /> Add Responsibility
      </button>
    </div>
  )
}
