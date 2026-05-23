'use client'

export default function WeightSlider({ label, value, onChange, max = 30, showValue = true }) {
  return (
    <div className="flex items-center gap-3 group">
      <span className="text-xs t-muted w-32 truncate flex-shrink-0">{label}</span>
      <input
        type="range"
        min={0}
        max={max}
        value={value}
        onChange={e => onChange(Number(e.target.value))}
        className="flex-1 h-1.5 rounded-full appearance-none cursor-pointer transition-all"
        style={{
          background: `linear-gradient(to right, #6366f1 0%, #6366f1 ${(value / max) * 100}%, rgba(255,255,255,0.08) ${(value / max) * 100}%, rgba(255,255,255,0.08) 100%)`,
          accentColor: '#6366f1',
        }}
      />
      {showValue && (
        <span className={`text-xs font-mono font-bold w-8 text-right ${value > 0 ? 'text-raiya-400' : 't-faintest'}`}>
          {value}
        </span>
      )}
    </div>
  )
}
