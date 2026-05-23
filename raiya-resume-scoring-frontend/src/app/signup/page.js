'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Eye, EyeOff, UserPlus, ArrowRight, AlertCircle, CheckCircle } from 'lucide-react'
import Link from 'next/link'
import toast from 'react-hot-toast'

export default function SignupPage() {
  const router = useRouter()
  const [form, setForm] = useState({ name: '', email: '', password: '', confirmPassword: '' })
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [errors, setErrors] = useState({})

  const update = (key, val) => { setForm(p => ({ ...p, [key]: val })); setErrors(p => ({ ...p, [key]: '' })) }

  const passStrength = (p) => {
    if (!p) return { label: '', color: '', width: '0%' }
    let s = 0
    if (p.length >= 6) s++; if (p.length >= 10) s++; if (/[A-Z]/.test(p)) s++; if (/[0-9]/.test(p)) s++; if (/[^A-Za-z0-9]/.test(p)) s++
    if (s <= 1) return { label: 'Weak', color: 'bg-red-500', width: '20%' }
    if (s <= 2) return { label: 'Fair', color: 'bg-amber-500', width: '40%' }
    if (s <= 3) return { label: 'Good', color: 'bg-blue-500', width: '60%' }
    if (s <= 4) return { label: 'Strong', color: 'bg-green-500', width: '80%' }
    return { label: 'Very Strong', color: 'bg-emerald-400', width: '100%' }
  }

  const validate = () => {
    const e = {}
    if (!form.name.trim()) e.name = 'Full name is required'
    else if (form.name.trim().length < 2) e.name = 'Name must be at least 2 characters'
    if (!form.email.trim()) e.email = 'Email is required'
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) e.email = 'Enter a valid email'
    if (!form.password) e.password = 'Password is required'
    else if (form.password.length < 6) e.password = 'Password must be at least 6 characters'
    if (!form.confirmPassword) e.confirmPassword = 'Please confirm your password'
    else if (form.password !== form.confirmPassword) e.confirmPassword = 'Passwords do not match'
    setErrors(e); return Object.keys(e).length === 0
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!validate()) return
    setLoading(true)
    setTimeout(() => { toast.success('Account created! Redirecting...'); router.push('/login') }, 1500)
  }

  const ps = passStrength(form.password)

  return (
    <div className="min-h-screen flex flex-col lg:flex-row">
      <div className="relative lg:w-1/2 flex flex-col items-center justify-center p-8 lg:p-16 overflow-hidden bg-gradient-to-br from-raiya-950 via-raiya-900 to-sidebar min-h-[250px] lg:min-h-screen">
        <div className="absolute top-20 left-10 w-72 h-72 bg-raiya-600/20 rounded-full blur-[100px] animate-pulse" />
        <div className="absolute bottom-20 right-10 w-96 h-96 bg-purple-600/10 rounded-full blur-[120px] animate-pulse" style={{ animationDelay: '1s' }} />
        <div className="relative z-10 text-center max-w-md">
          <div className="mb-6 float">
            <div className="w-36 h-36 sm:w-44 sm:h-44 mx-auto rounded-2xl overflow-hidden ring-4 ring-raiya-500/30 shadow-2xl shadow-raiya-500/20 bg-white p-2">
              <img src="/company_logo.jpeg" alt="SpeedTech.ai" className="w-full h-full object-contain rounded-xl" />
            </div>
          </div>
          <h1 className="text-3xl sm:text-4xl font-black gradient-text mb-3 tracking-tight">Join RAIYA</h1>
          <p className="text-sm text-slate-400">Create your recruiter account and start AI-powered screening</p>
        </div>
        <p className="absolute bottom-6 text-xs text-slate-600">Powered by SpeedTech.ai</p>
      </div>

      <div className="lg:w-1/2 flex items-center justify-center p-6 sm:p-8 lg:p-16 bg-sidebar/50">
        <div className="w-full max-w-md">
          <div className="mb-6">
            <h2 className="text-2xl sm:text-3xl font-bold text-white mb-2">Create Account</h2>
            <p className="text-slate-400">Fill in details to get started</p>
          </div>
          <form onSubmit={handleSubmit} className="space-y-4">
            {[
              { key: 'name', label: 'Full Name', type: 'text', placeholder: 'Gurjas Singh Gandhi' },
              { key: 'email', label: 'Email Address', type: 'email', placeholder: 'recruiter@speedtech.ai' },
            ].map(f => (
              <div key={f.key}>
                <label className="block text-sm font-medium text-slate-300 mb-1.5">{f.label}</label>
                <input type={f.type} value={form[f.key]} onChange={e => update(f.key, e.target.value)} placeholder={f.placeholder}
                  className={`w-full px-4 py-3 rounded-xl bg-white/5 border ${errors[f.key] ? 'border-red-500/50 ring-1 ring-red-500/30' : 'border-white/10'} text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-raiya-500 text-sm`} />
                {errors[f.key] && <p className="mt-1 text-xs text-red-400 flex items-center gap-1"><AlertCircle className="w-3 h-3" />{errors[f.key]}</p>}
              </div>
            ))}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1.5">Password</label>
              <div className="relative">
                <input type={showPassword ? 'text' : 'password'} value={form.password} onChange={e => update('password', e.target.value)} placeholder="Min. 6 characters"
                  className={`w-full px-4 py-3 rounded-xl bg-white/5 border ${errors.password ? 'border-red-500/50 ring-1 ring-red-500/30' : 'border-white/10'} text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-raiya-500 text-sm pr-12`} />
                <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white"><EyeOff className="w-5 h-5" /></button>
              </div>
              {form.password && (
                <div className="mt-2 flex items-center gap-2">
                  <div className="flex-1 h-1.5 bg-white/10 rounded-full overflow-hidden"><div className={`h-full rounded-full ${ps.color} transition-all`} style={{ width: ps.width }} /></div>
                  <span className="text-[10px] text-slate-400">{ps.label}</span>
                </div>
              )}
              {errors.password && <p className="mt-1 text-xs text-red-400 flex items-center gap-1"><AlertCircle className="w-3 h-3" />{errors.password}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1.5">Confirm Password</label>
              <input type="password" value={form.confirmPassword} onChange={e => update('confirmPassword', e.target.value)} placeholder="Re-enter password"
                className={`w-full px-4 py-3 rounded-xl bg-white/5 border ${errors.confirmPassword ? 'border-red-500/50 ring-1 ring-red-500/30' : form.confirmPassword && form.password === form.confirmPassword ? 'border-green-500/50 ring-1 ring-green-500/30' : 'border-white/10'} text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-raiya-500 text-sm`} />
              {form.confirmPassword && form.password === form.confirmPassword && <p className="mt-1 text-xs text-green-400 flex items-center gap-1"><CheckCircle className="w-3 h-3" />Passwords match</p>}
              {errors.confirmPassword && <p className="mt-1 text-xs text-red-400 flex items-center gap-1"><AlertCircle className="w-3 h-3" />{errors.confirmPassword}</p>}
            </div>
            <button type="submit" disabled={loading}
              className="w-full py-3 rounded-xl bg-gradient-to-r from-raiya-600 to-raiya-500 hover:from-raiya-500 hover:to-raiya-400 text-white font-semibold flex items-center justify-center gap-2 transition-all shadow-lg shadow-raiya-500/20 disabled:opacity-50">
              {loading ? <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <><UserPlus className="w-5 h-5" />Create Account<ArrowRight className="w-4 h-4" /></>}
            </button>
          </form>
          <p className="mt-5 text-center text-sm text-slate-400">Already have an account? <Link href="/login" className="text-raiya-400 hover:text-raiya-300 font-medium">Sign In</Link></p>
        </div>
      </div>
    </div>
  )
}
