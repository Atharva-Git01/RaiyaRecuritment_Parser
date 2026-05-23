'use client'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { useTheme } from '@/components/ThemeProvider'

const COLORS = ['#ef4444', '#f59e0b', '#3b82f6', '#22c55e']

export default function ScoreDistChart({ data }) {
  const { dark } = useTheme()
  const chartData = [
    { name: 'Poor (0-29)', value: data.poor },
    { name: 'Average (30-49)', value: data.average },
    { name: 'Good (50-79)', value: data.good },
    { name: 'Excellent (80+)', value: data.excellent },
  ]

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" stroke={dark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.06)'} />
        <XAxis dataKey="name" tick={{ fill: dark ? '#94a3b8' : '#475569', fontSize: 11 }} axisLine={{ stroke: dark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)' }} />
        <YAxis tick={{ fill: dark ? '#94a3b8' : '#475569', fontSize: 11 }} axisLine={{ stroke: dark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)' }} allowDecimals={false} />
        <Tooltip contentStyle={{ background: dark ? 'rgba(15,23,42,0.95)' : 'rgba(255,255,255,0.95)', border: `1px solid ${dark ? 'rgba(99,102,241,0.3)' : 'rgba(99,102,241,0.25)'}`, borderRadius: '12px', fontSize: '12px', color: dark ? '#e2e8f0' : '#1e293b' }} />
        <Bar dataKey="value" radius={[6, 6, 0, 0]}>
          {chartData.map((_, i) => <Cell key={i} fill={COLORS[i]} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
