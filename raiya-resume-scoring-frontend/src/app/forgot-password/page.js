'use client'
import { useState } from 'react'
import { Mail, ArrowLeft, ArrowRight, AlertCircle, CheckCircle } from 'lucide-react'
import Link from 'next/link'
import toast from 'react-hot-toast'

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [sent, setSent] = useState(false)
  const [error, setError] = useState('')

  const validate = () => {
    if (!email.trim()) { setError('Email is required'); return false }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { setError('Enter a valid email address'); return false }
    setError(''); return true
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!validate()) return
    setLoading(true)
    setTimeout(() => { setLoading(false); setSent(true); toast.success('OTP sent to your email!') }, 1500)
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-raiya-950 via-raiya-900 to-sidebar p-6">
      <div className="absolute top-20 left-10 w-72 h-72 bg-raiya-600/20 rounded-full blur-[100px] animate-pulse" />
      <div className="absolute bottom-20 right-10 w-96 h-96 bg-purple-600/10 rounded-full blur-[120px] animate-pulse" />
      <div className="relative z-10 w-full max-w-md">
        <div className="text-center mb-8">
          <div className="w-20 h-20 mx-auto rounded-2xl overflow-hidden bg-white p-1.5 ring-4 ring-raiya-500/30 shadow-2xl shadow-raiya-500/20 mb-4">
            <img src="/company_logo.jpeg" alt="SpeedTech.ai" className="w-full h-full object-contain rounded-xl" />
          </div>
          <h1 className="text-2xl font-bold text-white mb-1">Forgot Password</h1>
          <p className="text-sm text-slate-400">Enter your email to receive a reset OTP</p>
        </div>
        <div className="glass-card p-6 sm:p-8">
          {!sent ? (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Email Address</label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                  <input type="email" value={email} onChange={e => { setEmail(e.target.value); setError('') }} placeholder="recruiter@speedtech.ai"
                    className={`w-full pl-10 pr-4 py-3 rounded-xl bg-white/5 border ${error ? 'border-red-500/50 ring-1 ring-red-500/30' : 'border-white/10'} text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-raiya-500 text-sm`} />
                </div>
                {error && <p className="mt-1 text-xs text-red-400 flex items-center gap-1"><AlertCircle className="w-3 h-3" />{error}</p>}
              </div>
              <button type="submit" disabled={loading}
                className="w-full py-3 rounded-xl bg-gradient-to-r from-raiya-600 to-raiya-500 text-white font-semibold flex items-center justify-center gap-2 transition-all shadow-lg shadow-raiya-500/20 disabled:opacity-50">
                {loading ? <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <>Send Reset OTP<ArrowRight className="w-4 h-4" /></>}
              </button>
            </form>
          ) : (
            <div className="text-center space-y-4">
              <div className="w-14 h-14 rounded-full bg-green-500/20 flex items-center justify-center mx-auto"><CheckCircle className="w-7 h-7 text-green-400" /></div>
              <h3 className="text-lg font-semibold text-white">OTP Sent!</h3>
              <p className="text-sm text-slate-400">We&apos;ve sent a 6-digit OTP to <span className="text-raiya-300 font-medium">{email}</span>. Check your inbox.</p>
              <Link href="/reset-password" className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-raiya-600 to-raiya-500 text-white font-semibold transition-all shadow-lg shadow-raiya-500/20">
                Enter OTP <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          )}
        </div>
        <p className="mt-6 text-center text-sm text-slate-500"><Link href="/login" className="text-raiya-400 hover:text-raiya-300 inline-flex items-center gap-1"><ArrowLeft className="w-3.5 h-3.5" />Back to Login</Link></p>
      </div>
    </div>
  )
}
