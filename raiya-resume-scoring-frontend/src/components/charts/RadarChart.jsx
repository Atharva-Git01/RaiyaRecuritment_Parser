'use client'
import { Radar, RadarChart as ReRadar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip } from 'recharts'
import { SECTION_LABELS } from '@/data/static-data'
import { useTheme } from '@/components/ThemeProvider'

export default function RadarChart({ sections }) {
  const { dark } = useTheme()
  const data = sections.map(([key, val]) => ({
    section: (SECTION_LABELS[key] || key).replace(/^.\s/, ''),
    score: val.raw_score,
    fullMark: 100,
  }))

  return (
    <ResponsiveContainer width="100%" height="100%">
      <ReRadar cx="50%" cy="50%" outerRadius="75%" data={data}>
        <PolarGrid stroke={dark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)'} />
        <PolarAngleAxis dataKey="section" tick={{ fill: dark ? '#94a3b8' : '#475569', fontSize: 10 }} />
        <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: dark ? '#475569' : '#94a3b8', fontSize: 9 }} />
        <Tooltip contentStyle={{ background: dark ? 'rgba(15,23,42,0.95)' : 'rgba(255,255,255,0.95)', border: `1px solid ${dark ? 'rgba(99,102,241,0.3)' : 'rgba(99,102,241,0.25)'}`, borderRadius: '12px', fontSize: '12px', color: dark ? '#e2e8f0' : '#1e293b' }} />
        <Radar name="Score" dataKey="score" stroke="#6366f1" fill="#6366f1" fillOpacity={0.15} strokeWidth={2} />
      </ReRadar>
    </ResponsiveContainer>
  )
}
