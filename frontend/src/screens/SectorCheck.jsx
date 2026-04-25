import { useEffect, useState } from 'react'
import PhoneFrame from '../components/PhoneFrame'

function ChangeText({ value }) {
  const cls = value >= 0 ? 'change up' : 'change down'
  const sign = value >= 0 ? '+' : ''
  return <span className={cls}>{sign}{value.toFixed(2)}%</span>
}

export default function SectorCheck({ onOpenSector, tabBar }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetch('/api/sectors')
      .then((r) => r.json())
      .then(setData)
      .catch((e) => setError(e.message))
  }, [])

  return (
    <PhoneFrame tabBar={tabBar}>
      <div className="app-bar">
        <div>
          <h1>섹터체크</h1>
          <div className="sub">오늘의 시장 흐름</div>
        </div>
        <button className="icon-btn" aria-label="알림">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.7 21a2 2 0 0 1-3.4 0"/></svg>
        </button>
      </div>

      <div className="scroll">
        {!data && !error && <div className="loading">불러오는 중…</div>}
        {error && <div className="empty">데이터를 불러오지 못했습니다.</div>}
        {data && (
          <>
            <div className="section-title">
              <span>오늘 가장 뜨거운 섹터</span>
              <span className="more">전체보기 ›</span>
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
              <span className="more">정렬 ↕</span>
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
          </>
        )}
      </div>
    </PhoneFrame>
  )
}
