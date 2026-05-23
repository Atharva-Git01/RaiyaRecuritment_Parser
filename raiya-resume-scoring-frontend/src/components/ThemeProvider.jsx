'use client'
import { createContext, useContext, useState, useEffect, useCallback } from 'react'

const ThemeContext = createContext({ dark: true, toggle: () => {} })

export function useTheme() {
  return useContext(ThemeContext)
}

export function ThemeProvider({ children }) {
  const [dark, setDark] = useState(true)
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    // Read persisted theme
    const stored = localStorage.getItem('raiya-theme')
    if (stored === 'light') setDark(false)
    setMounted(true)
  }, [])

  useEffect(() => {
    if (!mounted) return
    const html = document.documentElement
    html.classList.remove('dark', 'light')
    html.classList.add(dark ? 'dark' : 'light')
    localStorage.setItem('raiya-theme', dark ? 'dark' : 'light')
    // Update meta theme-color
    const meta = document.querySelector('meta[name="theme-color"]')
    if (meta) meta.setAttribute('content', dark ? '#0f0c29' : '#f0f4ff')
  }, [dark, mounted])

  const toggle = useCallback(() => setDark(prev => !prev), [])

  return (
    <ThemeContext.Provider value={{ dark, toggle }}>
      {children}
    </ThemeContext.Provider>
  )
}
