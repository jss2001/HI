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

const TABS = ['일간', '주간', '월간', '연간']

export default function SectorDetail({ sectorId, onBack, tabBar }) {
  const [data, setData] = useState(null)
  const [tab, setTab] = useState('일간')

  useEffect(() => {
    setData(null)
    fetch(`/api/sectors/${sectorId}`).then((r) => r.json()).then(setData)
  }, [sectorId])

  if (!data) {
    return (
      <PhoneFrame tabBar={tabBar}>
        <div className="loading">불러오는 중…</div>
      </PhoneFrame>
    )
  }

  const up = data.change >= 0
  const color = up ? '#ef4444' : '#2563eb'

  return (
    <PhoneFrame tabBar={tabBar}>
      <div className="detail-header">
        <button className="icon-btn" onClick={onBack} aria-label="뒤로">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M15 18l-6-6 6-6"/></svg>
        </button>
        <div className="detail-title">
          {data.name}
          <span style={{ color: data.starred ? '#f59e0b' : '#cbd5e1' }}>★</span>
        </div>
        <button className="icon-btn" aria-label="공유">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="M8.6 13.5l6.8 4M15.4 6.5l-6.8 4"/></svg>
        </button>
      </div>

      <div className="scroll">
        <div className="detail-hero">
          <div className="hero-pct" style={{ color }}>
            <span>{up ? '▲' : '▼'}</span>
            {up ? '+' : ''}{data.change.toFixed(2)}%
          </div>
          <div className="hero-price">{data.price.toLocaleString()} pt</div>
          <MiniChart data={data.chart} color={color} />
          <div className="hero-summary">{data.summary}</div>
        </div>

        <div className="tabs-pill">
          {TABS.map((t) => (
            <button key={t} className={`pill ${tab === t ? 'active' : ''}`} onClick={() => setTab(t)}>{t}</button>
          ))}
        </div>

        <div className="section-title"><span>실시간 코멘트</span><span className="more">정렬 ›</span></div>
        {data.comments.map((c) => (
          <div key={c.id} className="comment">
            <div className="row1">
              <span className="user">{c.user}</span>
              <span>{c.time}</span>
            </div>
            <div className="text">{c.text}</div>
            <div className="row2">
              <span>♡ {c.likes}</span>
              <span>💬 답글</span>
            </div>
          </div>
        ))}
      </div>
    </PhoneFrame>
  )
}
