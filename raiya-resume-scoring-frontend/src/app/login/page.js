'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Eye, EyeOff, LogIn, ArrowRight, AlertCircle } from 'lucide-react'
import Link from 'next/link'
import toast from 'react-hot-toast'

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [errors, setErrors] = useState({})

  const validate = () => {
    const errs = {}
    if (!email.trim()) errs.email = 'Email is required'
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) errs.email = 'Enter a valid email'
    if (!password.trim()) errs.password = 'Password is required'
    else if (password.length < 4) errs.password = 'Password must be at least 4 characters'
    setErrors(errs)
    return Object.keys(errs).length === 0
  }

  const handleLogin = (e) => {
    e.preventDefault()
    if (!validate()) return
    setLoading(true)
    // Admin login check
    if (email === 'admin@speedtech.ai' && password === 'admin123') {
      toast.success('Welcome, Admin!')
      setTimeout(() => router.push('/admin'), 1000)
      return
    }
    setTimeout(() => { toast.success('Welcome to RAIYA!'); router.push('/platform') }, 1200)
  }

  return (
    <div className="min-h-screen flex flex-col lg:flex-row">
      <div className="relative lg:w-1/2 flex flex-col items-center justify-center p-8 lg:p-16 overflow-hidden bg-gradient-to-br from-raiya-950 via-raiya-900 to-sidebar min-h-[300px] lg:min-h-screen">
        <div className="absolute top-20 left-10 w-72 h-72 bg-raiya-600/20 rounded-full blur-[100px] animate-pulse" />
        <div className="absolute bottom-20 right-10 w-96 h-96 bg-purple-600/10 rounded-full blur-[120px] animate-pulse" style={{ animationDelay: '1s' }} />
        <div className="relative z-10 text-center max-w-md">
          <div className="mb-8 float">
            <div className="w-40 h-40 sm:w-52 sm:h-52 mx-auto rounded-2xl overflow-hidden ring-4 ring-raiya-500/30 shadow-2xl shadow-raiya-500/20 bg-white p-2">
              <img src="/company_logo.jpeg" alt="SpeedTech.ai" className="w-full h-full object-contain rounded-xl" />
            </div>
          </div>
          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-black gradient-text mb-4 tracking-tight">RAIYA</h1>
          <p className="text-lg sm:text-xl text-raiya-300 font-medium mb-2">Recruiting Resume Scoring System</p>
          <p className="text-sm text-slate-400 leading-relaxed">AI-powered evidence-based resume screening. Score, rank, and compare candidates with precision.</p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            {['AI Scoring', 'Batch Processing', 'Smart Ranking'].map((tag) => (
              <span key={tag} className="px-3 py-1.5 rounded-full text-xs font-medium bg-raiya-500/10 text-raiya-300 border border-raiya-500/20">{tag}</span>
            ))}
          </div>
        </div>
        <p className="absolute bottom-6 text-xs text-slate-600">Powered by SpeedTech.ai</p>
      </div>

      <div className="lg:w-1/2 flex items-center justify-center p-6 sm:p-8 lg:p-16 bg-sidebar/50">
        <div className="w-full max-w-md">
          <div className="mb-8">
            <h2 className="text-2xl sm:text-3xl font-bold text-white mb-2">Welcome back</h2>
            <p className="text-slate-400">Sign in to your recruiter account</p>
          </div>
          <form onSubmit={handleLogin} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Email Address</label>
              <input type="email" value={email} onChange={(e) => { setEmail(e.target.value); setErrors(p => ({ ...p, email: '' })) }}
                placeholder="recruiter@speedtech.ai"
                className={`w-full px-4 py-3 rounded-xl bg-white/5 border ${errors.email ? 'border-red-500/50 ring-1 ring-red-500/30' : 'border-white/10'} text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-raiya-500 transition-all text-sm`} />
              {errors.email && <p className="mt-1 text-xs text-red-400 flex items-center gap-1"><AlertCircle className="w-3 h-3" />{errors.email}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Password</label>
              <div className="relative">
                <input type={showPassword ? 'text' : 'password'} value={password} onChange={(e) => { setPassword(e.target.value); setErrors(p => ({ ...p, password: '' })) }}
                  placeholder="••••••••"
                  className={`w-full px-4 py-3 rounded-xl bg-white/5 border ${errors.password ? 'border-red-500/50 ring-1 ring-red-500/30' : 'border-white/10'} text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-raiya-500 transition-all text-sm pr-12`} />
                <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white transition-colors">
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
              {errors.password && <p className="mt-1 text-xs text-red-400 flex items-center gap-1"><AlertCircle className="w-3 h-3" />{errors.password}</p>}
            </div>
            <div className="flex items-center justify-between text-sm">
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" className="w-4 h-4 rounded border-white/20 bg-white/5 text-raiya-500 focus:ring-raiya-500" />
                <span className="text-slate-400">Remember me</span>
              </label>
              <Link href="/forgot-password" className="text-raiya-400 hover:text-raiya-300 transition-colors">Forgot password?</Link>
            </div>
            <button type="submit" disabled={loading}
              className="w-full py-3 px-6 rounded-xl bg-gradient-to-r from-raiya-600 to-raiya-500 hover:from-raiya-500 hover:to-raiya-400 text-white font-semibold flex items-center justify-center gap-2 transition-all duration-300 shadow-lg shadow-raiya-500/20 hover:shadow-raiya-500/40 disabled:opacity-50 disabled:cursor-not-allowed">
              {loading ? <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <><LogIn className="w-5 h-5" />Sign In<ArrowRight className="w-4 h-4" /></>}
            </button>
          </form>
          <p className="mt-6 text-center text-sm text-slate-400">
            Don&apos;t have an account?{' '}<Link href="/signup" className="text-raiya-400 hover:text-raiya-300 font-medium transition-colors">Sign Up</Link>
          </p>
          <div className="mt-6 p-4 rounded-xl bg-raiya-500/5 border border-raiya-500/10 space-y-1">
            <p className="text-xs text-raiya-300/70 text-center">🔒 Demo Mode</p>
            <p className="text-[11px] text-slate-500 text-center">Recruiter: any email/password</p>
            <p className="text-[11px] text-slate-500 text-center">Admin: admin@speedtech.ai / admin123</p>
          </div>
        </div>
      </div>
    </div>
  )
}
