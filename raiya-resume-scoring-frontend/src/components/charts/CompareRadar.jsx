'use client'
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip, Legend } from 'recharts'
import { SECTION_LABELS } from '@/data/static-data'
import { useTheme } from '@/components/ThemeProvider'

const COLORS = ['#6366f1', '#f59e0b', '#10b981']

export default function CompareRadar({ candidates }) {
  const { dark } = useTheme()
  const sections = Object.keys(candidates[0]?.section_breakdown || {})
  const data = sections.map(key => {
    const entry = { section: (SECTION_LABELS[key] || key).replace(/^.\s/, '') }
    candidates.forEach((c, i) => { entry[`c${i}`] = c.section_breakdown[key]?.raw_score || 0 })
    return entry
  })

  return (
    <ResponsiveContainer width="100%" height="100%">
      <RadarChart cx="50%" cy="50%" outerRadius="75%" data={data}>
        <PolarGrid stroke={dark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)'} />
        <PolarAngleAxis dataKey="section" tick={{ fill: dark ? '#94a3b8' : '#475569', fontSize: 10 }} />
        <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: dark ? '#475569' : '#94a3b8', fontSize: 9 }} />
        <Tooltip contentStyle={{
          background: dark ? 'rgba(15,23,42,0.95)' : 'rgba(255,255,255,0.95)',
          border: `1px solid ${dark ? 'rgba(99,102,241,0.3)' : 'rgba(99,102,241,0.25)'}`,
          borderRadius: '12px', fontSize: '12px',
          color: dark ? '#e2e8f0' : '#1e293b'
        }} />
        {candidates.map((c, i) => (
          <Radar key={`radar-${i}`} name={c.name} dataKey={`c${i}`} stroke={COLORS[i]} fill={COLORS[i]} fillOpacity={0.1} strokeWidth={2} />
        ))}
      </RadarChart>
    </ResponsiveContainer>
  )
}
