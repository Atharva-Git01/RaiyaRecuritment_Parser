import Link from 'next/link'

export default function NotFound() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-8 text-center">
      <div className="text-8xl mb-6">🔍</div>
      <h1 className="text-4xl sm:text-5xl font-black gradient-text mb-4">404</h1>
      <p className="text-lg text-slate-400 mb-8 max-w-md">The page you&apos;re looking for doesn&apos;t exist or has been moved.</p>
      <Link href="/platform" className="px-6 py-3 rounded-xl bg-gradient-to-r from-raiya-600 to-raiya-500 text-white font-semibold hover:shadow-lg hover:shadow-raiya-500/20 transition-all">
        Back to Platform
      </Link>
    </div>
  )
}
