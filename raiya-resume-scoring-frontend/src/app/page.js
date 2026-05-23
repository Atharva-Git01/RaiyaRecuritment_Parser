'use client'
import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function Home() {
  const router = useRouter()
  useEffect(() => { router.replace('/login') }, [router])
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="animate-pulse text-raiya-400 text-xl font-semibold">Loading RAIYA...</div>
    </div>
  )
}
