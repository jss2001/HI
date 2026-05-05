import { useEffect, useMemo, useState } from 'react'
import PhoneFrame from '../components/PhoneFrame'

function MiniChart({ data, color }) {
  const path = useMemo(() => {
    if (!data?.length) return ''
    const w = 320
    const h = 100
    const min = Math.min(...data)
    const max = Math.max(...data)
    const range = max - min || 1
    return data
      .map((v, i) => {
        const x = (i / (data.length - 1)) * w
        const y = h - ((v - min) / range) * (h - 8) - 4
        return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`
      })
      .join(' ')
  }, [data])

  return (
    <svg className="chart" viewBox="0 0 320 100" preserveAspectRatio="none">
      <defs>
        <linearGradient id="g1" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.3" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={`${path} L320,100 L0,100 Z`} fill="url(#g1)" />
      <path d={path} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

const TABS = [
  { key: 'daily', label: '일간' },
  { key: 'weekly', label: '주간' },
  { key: 'monthly', label: '월간' },
  { key: 'yearly', label: '연간' },
]

const FAV_KEY = 'hi_fav_sectors'

function getFavs() {
  try { return JSON.parse(localStorage.getItem(FAV_KEY) || '[]') } catch { return [] }
}

export default function SectorDetail({ sectorId, onBack, onOpenNews, tabBar }) {
  const [data, setData] = useState(null)
  const [period, setPeriod] = useState('daily')
  const [fav, setFav] = useState(() => getFavs().includes(sectorId))
  const [toast, setToast] = useState(null)

  useEffect(() => {
    setData(null)
    fetch(`/api/sectors/${sectorId}?period=${period}`).then((r) => r.json()).then(setData)
  }, [sectorId, period])

  useEffect(() => { setFav(getFavs().includes(sectorId)) }, [sectorId])

  const toggleFav = () => {
    const cur = getFavs()
    const next = fav ? cur.filter((x) => x !== sectorId) : [...cur, sectorId]
    localStorage.setItem(FAV_KEY, JSON.stringify(next))
    setFav(!fav)
    setToast(!fav ? '관심 섹터에 추가됨' : '관심 섹터에서 제거됨')
    setTimeout(() => setToast(null), 1400)
  }

  const share = async () => {
    const url = window.location.origin + window.location.pathname + '#sector/' + sectorId
    try {
      await navigator.clipboard.writeText(url)
      setToast('링크 복사됨')
    } catch {
      setToast('복사 실패')
    }
    setTimeout(() => setToast(null), 1400)
  }

  if (!data) {
    return (
      <PhoneFrame tabBar={tabBar}>
        <div className="loading">불러오는 중…</div>
      </PhoneFrame>
    )
  }

  const up = data.change >= 0
  const color = up ? 'var(--up)' : 'var(--down)'

  return (
    <PhoneFrame tabBar={tabBar}>
      <div className="detail-header">
        <button className="icon-btn" onClick={onBack} aria-label="뒤로">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M15 18l-6-6 6-6"/></svg>
        </button>
        <div className="detail-title">
          {data.name}
          <button
            className="star-btn"
            onClick={toggleFav}
            aria-label={fav ? '관심 해제' : '관심 추가'}
            style={{ color: fav ? '#f59e0b' : 'var(--muted2)' }}
          >★</button>
        </div>
        <button className="icon-btn" onClick={share} aria-label="공유">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="M8.6 13.5l6.8 4M15.4 6.5l-6.8 4"/></svg>
        </button>
      </div>
      {toast && <div className="toast">{toast}</div>}

      <div className="scroll">
        <div className="detail-hero">
          <div className="hero-pct" style={{ color }}>
            <span>{up ? '▲' : '▼'}</span>
            {up ? '+' : ''}{data.change.toFixed(2)}%
          </div>
          <div className="hero-price">
            {data.price?.toLocaleString()} {data.currency === 'USD' ? '$' : '원'}
            {data.high_3mo && data.low_3mo && (
              <span style={{ marginLeft: 8, fontSize: 11, color: 'var(--muted)', fontWeight: 500 }}>
                3M {data.low_3mo.toLocaleString()}~{data.high_3mo.toLocaleString()}
              </span>
            )}
          </div>
          <MiniChart data={data.chart} color={color} />
          <div className="hero-summary">{data.summary}</div>
        </div>

        <div className="tabs-pill">
          {TABS.map((t) => (
            <button key={t.key} className={`pill ${period === t.key ? 'active' : ''}`} onClick={() => setPeriod(t.key)}>{t.label}</button>
          ))}
        </div>
        {data.period_label && (
          <div style={{ fontSize: 10, color: 'var(--muted)', textAlign: 'center', marginBottom: 10, fontWeight: 600 }}>
            {data.period_label}
          </div>
        )}

        <div className="section-title">
          <span>
            관련 최신 뉴스
            {data.comments?.length > 0 && data.news_period && (
              <span style={{ fontSize: 10, color: 'var(--muted)', fontWeight: 600, marginLeft: 6 }}>
                · {data.news_period}
              </span>
            )}
          </span>
          {onOpenNews && data.comments?.length > 0 && (
            <button
              className="more"
              style={{ border: 0, background: 'transparent', cursor: 'pointer', color: 'var(--accent)' }}
              onClick={() => onOpenNews(data.name)}
            >전체 보기 ›</button>
          )}
        </div>
        {(!data.comments || data.comments.length === 0) && (
          <div className="empty" style={{ padding: '20px 0' }}>
            관련 뉴스를 찾지 못했어요
            {onOpenNews && (
              <div style={{ marginTop: 8 }}>
                <button
                  onClick={() => onOpenNews(data.name)}
                  style={{
                    border: '1px solid var(--line)',
                    background: 'var(--card)',
                    color: 'var(--text)',
                    padding: '6px 12px',
                    borderRadius: 8,
                    fontSize: 11,
                    fontWeight: 700,
                    cursor: 'pointer',
                  }}
                >뉴스탭에서 검색 ›</button>
              </div>
            )}
          </div>
        )}
        {data.comments.map((c) => {
          const isNews = c.kind === 'news'
          const Wrapper = isNews && c.link ? 'a' : 'div'
          const props = isNews && c.link ? { href: c.link, target: '_blank', rel: 'noreferrer' } : {}
          return (
            <Wrapper key={c.id} className="comment" {...props}>
              <div className="row1">
                <span className="user">{c.user}</span>
                <span>{c.time}</span>
              </div>
              <div className="text">{c.text}</div>
              {!isNews && (
                <div className="row2">
                  <span>♡ {c.likes}</span>
                  <span>💬 답글</span>
                </div>
              )}
            </Wrapper>
          )
        })}
      </div>
    </PhoneFrame>
  )
}
