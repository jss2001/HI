import { useEffect, useState } from 'react'
import PhoneFrame from '../components/PhoneFrame'

const THEMES_KEY = 'hi_themes'

function getThemes() {
  try { return JSON.parse(localStorage.getItem(THEMES_KEY) || '[]') } catch { return [] }
}
function saveThemes(arr) {
  localStorage.setItem(THEMES_KEY, JSON.stringify(arr))
}

function ChangeText({ value }) {
  const cls = value >= 0 ? 'change up' : 'change down'
  const sign = value >= 0 ? '+' : ''
  return <span className={cls}>{sign}{value.toFixed(2)}%</span>
}

function ThemeCard({ keyword, onRemove, onOpen }) {
  const [data, setData] = useState(null)
  useEffect(() => {
    fetch(`/api/themes?keyword=${encodeURIComponent(keyword)}`).then((r) => r.json()).then(setData)
  }, [keyword])
  if (!data) {
    return <div className="theme-card loading-card">{keyword}…</div>
  }
  const m = data.market
  const b = data.buzz
  const buzzText = b ? (
    b.api_saturated
      ? `${b.buzz_emoji} ${b.buzz_label}`
      : `${b.buzz_emoji} ${b.buzz_label}${b.buzz_ratio ? ` · ${b.buzz_ratio}배` : ''}`
  ) : null
  const handleRemove = (e) => { e.stopPropagation(); onRemove() }
  return (
    <div className="theme-card clickable" onClick={onOpen} role="button" tabIndex={0}>
      <div className="theme-head">
        <span className="theme-name">{keyword}</span>
        <button className="theme-x" onClick={handleRemove} aria-label="제거">×</button>
      </div>
      {m ? (
        <>
          <div className="theme-mkt">
            <span className={`change ${m.change >= 0 ? 'up' : 'down'}`}>
              {m.change >= 0 ? '+' : ''}{m.change.toFixed(2)}%
            </span>
            <span className="theme-price">{m.price?.toLocaleString()}</span>
          </div>
          {buzzText && <div className="theme-buzz">{buzzText}</div>}
        </>
      ) : (
        // ETF 없으면 buzz를 메인으로
        buzzText && <div className="theme-buzz-big">{buzzText}</div>
      )}
      <div className="theme-news-cnt">관련 기사 {data.news?.length || 0}건 ›</div>
    </div>
  )
}

export default function SectorCheck({ onOpenSector, onOpenTheme, tabBar }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [themes, setThemes] = useState(getThemes)
  const [newTheme, setNewTheme] = useState('')

  useEffect(() => {
    fetch('/api/sectors')
      .then((r) => r.json())
      .then(setData)
      .catch((e) => setError(e.message))
  }, [])

  const addTheme = (e) => {
    e.preventDefault()
    const kw = newTheme.trim()
    if (!kw || themes.includes(kw)) { setNewTheme(''); return }
    const next = [...themes, kw]
    setThemes(next); saveThemes(next); setNewTheme('')
  }
  const removeTheme = (kw) => {
    const next = themes.filter((x) => x !== kw)
    setThemes(next); saveThemes(next)
  }

  return (
    <PhoneFrame tabBar={tabBar}>
      <div className="app-bar">
        <div>
          <h1>섹터체크</h1>
          <div className="sub">오늘의 시장 흐름</div>
        </div>
      </div>

      <div className="scroll">
        {!data && !error && <div className="loading">불러오는 중…</div>}
        {error && <div className="empty">데이터를 불러오지 못했습니다.</div>}
        {data && (
          <>
            <div className="section-title">
              <span>오늘 가장 뜨거운 섹터</span>
            </div>
            <div className="hot-grid">
              {data.hot.map((s) => (
                <div key={s.id} className="hot-card" onClick={() => onOpenSector(s.id)}>
                  <div className="hot-icon" style={{ background: s.color }}>{s.icon}</div>
                  <div className="hot-name">{s.name}</div>
                  <ChangeText value={s.change} />
                </div>
              ))}
            </div>

            <div className="section-title">
              <span>섹터 등락률</span>
            </div>
            <div className="sector-list">
              {data.all.map((s) => (
                <div key={s.id} className="sector-row" onClick={() => onOpenSector(s.id)}>
                  <div className="hot-icon" style={{ background: s.color, width: 40, height: 40 }}>{s.icon}</div>
                  <div className="meta">
                    <div className="name">{s.name}</div>
                    <div className="summary">{s.summary}</div>
                  </div>
                  <div className="right">
                    <div className="price">{s.price.toLocaleString()}</div>
                    <ChangeText value={s.change} />
                  </div>
                </div>
              ))}
            </div>

            <div className="section-title">
              <span>내 테마</span>
              <span className="more">키워드로 직접 만들기</span>
            </div>
            <form onSubmit={addTheme} className="theme-add-form">
              <input
                className="theme-input"
                placeholder="예: 로봇, 방산, 우주, 메타버스…"
                value={newTheme}
                onChange={(e) => setNewTheme(e.target.value)}
              />
              <button className="theme-add-btn" type="submit">추가</button>
            </form>
            <div className="theme-grid">
              {themes.length === 0 && (
                <div className="theme-empty">관심 키워드를 추가해보세요. ETF·뉴스·커뮤니티 글이 자동 매칭됩니다.</div>
              )}
              {themes.map((kw) => (
                <ThemeCard
                  key={kw}
                  keyword={kw}
                  onOpen={() => onOpenTheme && onOpenTheme(kw)}
                  onRemove={() => removeTheme(kw)}
                />
              ))}
            </div>
          </>
        )}
      </div>
    </PhoneFrame>
  )
}
