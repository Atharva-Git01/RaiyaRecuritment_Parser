'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { KeyRound, ArrowRight } from 'lucide-react'
import Link from 'next/link'
import toast from 'react-hot-toast'

export default function ResetPasswordPage() {
  const router = useRouter()

  const handleReset = (e) => {
    e.preventDefault()
    toast.success('Password reset successfully!')
    setTimeout(() => router.push('/login'), 1000)
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-md text-center">
        <img src="/company_logo.jpeg" alt="SpeedTech.ai" className="w-16 h-16 mx-auto rounded-xl object-cover ring-2 ring-raiya-500/30 mb-6" />
        <h1 className="text-2xl font-bold text-white mb-2">Reset Password</h1>
        <p className="text-slate-400 text-sm mb-8">Enter OTP and your new password</p>
        <form onSubmit={handleReset} className="glass-card p-6 space-y-4">
          <div className="flex gap-2 justify-center">
            {[1,2,3,4,5,6].map(i => (
              <input key={i} maxLength={1} className="w-11 h-12 text-center rounded-xl bg-white/5 border border-white/10 text-white text-lg font-bold focus:outline-none focus:ring-2 focus:ring-raiya-500" />
            ))}
          </div>
          <input type="password" placeholder="New Password" className="w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-raiya-500" />
          <input type="password" placeholder="Confirm Password" className="w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-raiya-500" />
          <button type="submit" className="w-full py-3 rounded-xl bg-gradient-to-r from-raiya-600 to-raiya-500 text-white font-semibold flex items-center justify-center gap-2 transition-all shadow-lg shadow-raiya-500/20">
            <KeyRound className="w-5 h-5" />Reset Password<ArrowRight className="w-4 h-4" />
          </button>
        </form>
        <Link href="/login" className="inline-block mt-4 text-sm text-raiya-400 hover:text-raiya-300">← Back to Login</Link>
      </div>
    </div>
  )
}
