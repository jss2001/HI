import { useEffect, useState } from 'react'
import PhoneFrame from '../components/PhoneFrame'

export default function NewsTimeline({ tabBar }) {
  const [data, setData] = useState(null)
  const [tag, setTag] = useState('전체')

  useEffect(() => {
    const url = tag === '전체' ? '/api/news' : `/api/news?tag=${encodeURIComponent(tag)}`
    fetch(url).then((r) => r.json()).then(setData)
  }, [tag])

  return (
    <PhoneFrame tabBar={tabBar}>
      <div className="app-bar">
        <div>
          <h1>뉴스 · 타임라인</h1>
          <div className="sub">테마별 시장 뉴스</div>
        </div>
        <button className="icon-btn" aria-label="검색">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>
        </button>
      </div>

      <div className="scroll">
        <div className="tabs-pill">
          {['전체', ...(data?.tags || [])].map((t) => (
            <button key={t} className={`pill ${tag === t ? 'active' : ''}`} onClick={() => setTag(t)}>{t}</button>
          ))}
        </div>

        {!data && <div className="loading">불러오는 중…</div>}
        {data?.groups?.length === 0 && <div className="empty">표시할 뉴스가 없습니다.</div>}

        {data?.groups?.map((group) => (
          <div key={group.date}>
            <div className="news-date">{group.date}</div>
            {group.items.map((n) => (
              <div key={n.id} className="news-item">
                <span className="news-tag">{n.tag}</span>
                <div className="news-body">
                  <div className="news-title">{n.title}</div>
                  <div className="news-summary">{n.summary}</div>
                  <div className="news-meta">{n.source} · {n.time}</div>
                </div>
              </div>
            ))}
          </div>
        ))}
      </div>
    </PhoneFrame>
  )
}
