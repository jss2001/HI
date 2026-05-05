import { useEffect, useMemo, useState } from 'react'
import PhoneFrame from '../components/PhoneFrame'

function MiniChart({ data, color }) {
  const path = useMemo(() => {
    if (!data?.length) return ''
    const w = 320, h = 100
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
        <linearGradient id="tgd" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.25" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={`${path} L320,100 L0,100 Z`} fill="url(#tgd)" />
      <path d={path} fill="none" stroke={color} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

export default function ThemeDetail({ keyword, onBack, onOpenNews, tabBar }) {
  const [data, setData] = useState(null)

  useEffect(() => {
    setData(null)
    fetch(`/api/themes?keyword=${encodeURIComponent(keyword)}`).then((r) => r.json()).then(setData)
  }, [keyword])

  if (!data) {
    return (
      <PhoneFrame tabBar={tabBar}>
        <div className="loading">불러오는 중…</div>
      </PhoneFrame>
    )
  }

  const m = data.market
  const b = data.buzz
  const up = (m?.change || 0) >= 0
  const color = up ? 'var(--up)' : 'var(--down)'

  return (
    <PhoneFrame tabBar={tabBar}>
      <div className="detail-header">
        <button className="icon-btn" onClick={onBack} aria-label="뒤로">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M15 18l-6-6 6-6"/></svg>
        </button>
        <div className="detail-title">
          {data.keyword}
          <span style={{ fontSize: 10, color: 'var(--muted)', marginLeft: 6, fontWeight: 600 }}>테마</span>
        </div>
        <div style={{ width: 32 }} />
      </div>

      <div className="scroll">
        <div className="detail-hero">
          {m ? (
            <>
              <div className="hero-pct" style={{ color }}>
                <span>{up ? '▲' : '▼'}</span>
                {up ? '+' : ''}{m.change.toFixed(2)}%
              </div>
              <div className="hero-price">
                {m.price?.toLocaleString()}원
                <span style={{ marginLeft: 8, fontSize: 11, color: 'var(--muted)', fontWeight: 500 }}>
                  {m.etf_name} · {m.ticker}
                </span>
              </div>
              <MiniChart data={m.chart} color={up ? '#d92e2e' : '#2563eb'} />
            </>
          ) : (
            <div style={{ padding: '8px 0 4px' }}>
              <div style={{ fontSize: 11, color: 'var(--muted)', fontWeight: 700, marginBottom: 4, letterSpacing: '0.04em' }}>
                ETF 미매핑 · 뉴스/커뮤니티 기반
              </div>
              <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text)' }}>
                {data.keyword}
              </div>
            </div>
          )}
        </div>

        {b && (
          <div className="vibe-grid" style={{ marginTop: 12 }}>
            <div className="buzz-card">
              <div className="vibe-label">화제성 <span className="vibe-emoji">{b.buzz_emoji}</span></div>
              <div className="vibe-value">{b.buzz_label}</div>
              <div className="vibe-sub">
                {b.api_saturated
                  ? `최근 3일 50+건 (조회 한도)`
                  : b.buzz_ratio !== null
                    ? `최근 평균 대비 ${b.buzz_ratio}배`
                    : `최근 3일 ${b.counts.recent_3d}건`}
              </div>
            </div>
            {b.posts?.length > 0 && (
              <div className="sentiment-card">
                <div className="vibe-label">필터된 글</div>
                <div className="vibe-value" style={{ fontSize: 14 }}>{b.posts.length}건</div>
                <div className="vibe-sub">블로그 + 카페</div>
              </div>
            )}
          </div>
        )}

        <div className="section-title">
          <span>
            관련 최신 뉴스
            {data.news_period && (
              <span style={{ fontSize: 10, color: 'var(--muted)', fontWeight: 600, marginLeft: 6 }}>
                · {data.news_period}
              </span>
            )}
          </span>
          {onOpenNews && (
            <button
              className="more"
              style={{ border: 0, background: 'transparent', cursor: 'pointer', color: 'var(--accent)' }}
              onClick={() => onOpenNews(keyword)}
            >전체 보기 ›</button>
          )}
        </div>
        {(!data.news || data.news.length === 0) && (
          <div className="empty">관련 기사 없음</div>
        )}
        {data.news?.map((n) => (
          <a key={n.id} href={n.link} target="_blank" rel="noreferrer" className="comment">
            <div className="row1">
              <span className="user">{n.source}</span>
              <span>{n.time}</span>
            </div>
            <div className="text">{n.title}</div>
          </a>
        ))}
      </div>
    </PhoneFrame>
  )
}
