import { useEffect, useState } from 'react'

const THEMES = [
  { key: 'light', icon: '☀︎' },
  { key: 'dark', icon: '☾' },
  { key: 'green', icon: '⬢' },
]

function StatusBar() {
  const [time, setTime] = useState('9:41')
  useEffect(() => {
    const tick = () => {
      const d = new Date()
      setTime(`${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`)
    }
    tick()
    const id = setInterval(tick, 30000)
    return () => clearInterval(id)
  }, [])
  return (
    <div className="status-bar">
      <span>{time}</span>
      <span className="status-icons">
        <svg width="16" height="12" viewBox="0 0 16 12" fill="currentColor"><path d="M2 8h2v3H2zM6 5h2v6H6zM10 2h2v9h-2zM14 0h-1v11h1z"/></svg>
        <svg width="16" height="12" viewBox="0 0 16 12" fill="none" stroke="currentColor" strokeWidth="1.4"><path d="M1 5c4-4 10-4 14 0M3.5 7.5c2.5-2.5 7-2.5 9 0M6 10l2 1 2-1"/></svg>
        <svg width="22" height="12" viewBox="0 0 22 12" fill="none" stroke="currentColor" strokeWidth="1"><rect x="0.5" y="0.5" width="18" height="11" rx="2"/><rect x="2" y="2" width="14" height="8" fill="currentColor"/><rect x="20" y="4" width="1.5" height="4" fill="currentColor"/></svg>
      </span>
    </div>
  )
}

function ThemeToggle() {
  const [theme, setTheme] = useState(() =>
    document.documentElement.getAttribute('data-theme') ||
    localStorage.getItem('hi_theme') || 'light'
  )
  const apply = (t) => {
    setTheme(t)
    document.documentElement.setAttribute('data-theme', t)
    localStorage.setItem('hi_theme', t)
  }
  return (
    <div className="theme-inphone">
      {THEMES.map((t) => (
        <button
          key={t.key}
          className={`theme-btn ${theme === t.key ? 'on' : ''}`}
          onClick={() => apply(t.key)}
        >{t.icon}</button>
      ))}
    </div>
  )
}

export default function PhoneFrame({ children, tabBar }) {
  return (
    <div className="phone">
      <StatusBar />
      <ThemeToggle />
      {children}
      {tabBar}
    </div>
  )
}
