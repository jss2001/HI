import { useEffect, useState } from 'react'
import { getMarket, setMarket } from '../hooks/useMarket'

// ☀︎ → 라이트 테마 + KR 마켓 / ☾ → 다크 테마 + US 마켓 / ⬢ → 그린 테마(마켓 유지)
const THEMES = [
  { key: 'light', icon: '☀︎', market: 'kr', title: '국내장 · 라이트' },
  { key: 'dark',  icon: '☾',  market: 'us', title: '미장 · 다크' },
  { key: 'green', icon: '⬢',  market: null, title: '그린' },
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

function TopActions() {
  const [theme, setTheme] = useState(() =>
    document.documentElement.getAttribute('data-theme') ||
    localStorage.getItem('hi_theme') || 'light'
  )
  const [market, setLocalMarket] = useState(getMarket)

  const apply = (t) => {
    setTheme(t)
    document.documentElement.setAttribute('data-theme', t)
    localStorage.setItem('hi_theme', t)
    const def = THEMES.find((x) => x.key === t)
    if (def?.market) {
      setLocalMarket(def.market)
      setMarket(def.market)
    }
  }

  return (
    <div className="top-actions">
      <div className="theme-pill" role="group" aria-label="테마 · 마켓 전환">
        {THEMES.map((t) => {
          const isThemeOn = theme === t.key
          const isMarketOn = t.market && market === t.market
          return (
            <button
              key={t.key}
              className={`theme-btn ${isThemeOn ? 'on' : ''} ${isMarketOn && !isThemeOn ? 'market-on' : ''}`}
              onClick={() => apply(t.key)}
              title={t.title}
              aria-pressed={isThemeOn}
            >{t.icon}</button>
          )
        })}
      </div>
      <button
        className="exchange-fab"
        onClick={() => window.dispatchEvent(new CustomEvent('hi-nav', { detail: { name: 'exchange' } }))}
      >
        $
      </button>
    </div>
  )
}

export default function PhoneFrame({ children, tabBar, hideTopActions }) {
  return (
    <div className="phone">
      <StatusBar />
      {!hideTopActions && <TopActions />}
      {children}
      {tabBar}
    </div>
  )
}
