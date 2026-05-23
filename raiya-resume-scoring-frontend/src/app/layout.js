import './globals.css'
import { Toaster } from 'react-hot-toast'
import { ThemeProvider } from '@/components/ThemeProvider'

export const metadata = {
  title: 'RAIYA: Recruiting Resume Scoring System',
  description: 'AI-Powered Resume Screening Platform — Evidence-Based Scoring by SpeedTech.ai',
  keywords: ['recruiting', 'resume scoring', 'AI', 'HR tech', 'candidate screening'],
  openGraph: {
    title: 'RAIYA: Recruiting Resume Scoring System',
    description: 'AI-Powered Resume Screening Platform',
    images: ['/company_logo.jpeg'],
  },
  icons: {
    icon: '/company_logo.jpeg',
  },
}

function ToasterWithTheme() {
  return (
    <Toaster
      position="top-right"
      toastOptions={{
        duration: 3000,
        style: {
          background: 'var(--dropdown-bg)',
          color: 'var(--heading-color)',
          border: '1px solid var(--glass-hover-border)',
          backdropFilter: 'blur(10px)',
          borderRadius: '12px',
        },
      }}
    />
  )
}

export default function RootLayout({ children }) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet" />
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=5" />
        <meta name="theme-color" content="#0f0c29" />
      </head>
      <body className="antialiased">
        <ThemeProvider>
          {children}
          <ToasterWithTheme />
        </ThemeProvider>
      </body>
    </html>
  )
}
