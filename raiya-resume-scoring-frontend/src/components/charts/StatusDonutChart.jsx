'use client'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts'
import { useTheme } from '@/components/ThemeProvider'

const COLORS = ['#22c55e', '#3b82f6', '#9ca3af', '#ef4444']

export default function StatusDonutChart({ data }) {
  const { dark } = useTheme()
  const chartData = [
    { name: 'Completed', value: data.completed },
    { name: 'In Progress', value: data.processing },
    { name: 'Queued', value: data.queued },
    { name: 'Failed', value: data.failed },
  ].filter(d => d.value > 0)

  return (
    <ResponsiveContainer width="100%" height="100%">
      <PieChart>
        <Pie data={chartData} cx="50%" cy="50%" innerRadius={55} outerRadius={85} paddingAngle={3} dataKey="value" stroke={dark ? 'rgba(15,23,42,0.8)' : 'rgba(255,255,255,0.8)'} strokeWidth={2}>
          {chartData.map((_, i) => <Cell key={i} fill={COLORS[i]} />)}
        </Pie>
        <Tooltip contentStyle={{ background: dark ? 'rgba(15,23,42,0.95)' : 'rgba(255,255,255,0.95)', border: `1px solid ${dark ? 'rgba(99,102,241,0.3)' : 'rgba(99,102,241,0.25)'}`, borderRadius: '12px', fontSize: '12px', color: dark ? '#e2e8f0' : '#1e293b' }} />
        <Legend wrapperStyle={{ fontSize: '12px', color: dark ? '#94a3b8' : '#475569' }} />
      </PieChart>
    </ResponsiveContainer>
  )
}
