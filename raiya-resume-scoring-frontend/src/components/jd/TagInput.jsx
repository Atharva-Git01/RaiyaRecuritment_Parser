'use client'
import { useState } from 'react'
import { X, Plus } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

export default function TagInput({ label, tags = [], onChange, placeholder = 'Add tag...', id }) {
  const [input, setInput] = useState('')

  const addTag = () => {
    const val = input.trim()
    if (val && !tags.includes(val)) {
      onChange([...tags, val])
      setInput('')
    }
  }

  const removeTag = (tag) => {
    onChange(tags.filter(t => t !== tag))
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      addTag()
    }
    if (e.key === 'Backspace' && !input && tags.length) {
      removeTag(tags[tags.length - 1])
    }
  }

  return (
    <div id={id}>
      {label && <label className="text-xs t-faint mb-1.5 block font-medium">{label}</label>}
      <div className="flex flex-wrap items-center gap-2 p-2.5 rounded-xl t-input min-h-[44px]">
        <AnimatePresence mode="popLayout">
          {tags.map(tag => (
            <motion.span
              key={tag}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium bg-raiya-500/20 text-raiya-300 border border-raiya-500/20"
            >
              {tag}
              <button onClick={() => removeTag(tag)} className="hover:text-red-400 transition-colors">
                <X className="w-3 h-3" />
              </button>
            </motion.span>
          ))}
        </AnimatePresence>
        <div className="flex items-center gap-1 flex-1 min-w-[120px]">
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            className="flex-1 bg-transparent text-sm t-heading outline-none placeholder:t-faintest min-w-[80px]"
          />
          {input.trim() && (
            <button onClick={addTag} className="p-1 rounded-lg hover:bg-raiya-500/20 text-raiya-400 transition-colors">
              <Plus className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
