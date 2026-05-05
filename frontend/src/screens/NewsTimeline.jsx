import { useEffect, useState } from 'react'
import PhoneFrame from '../components/PhoneFrame'

const THEMES_KEY = 'hi_themes'
function getCustomThemes() {
  try { return JSON.parse(localStorage.getItem(THEMES_KEY) || '[]') } catch { return [] }
}

export default function NewsTimeline({ tabBar, initialTag }) {
  const [data, setData] = useState(null)
  const [tag, setTag] = useState(initialTag || '전체')
  const [customTags] = useState(getCustomThemes)

  useEffect(() => {
    if (initialTag) setTag(initialTag)
  }, [initialTag])

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
      </div>

      <div className="scroll">
        <div className="tabs-pill">
          {['전체', ...(data?.tags || []), ...customTags].map((t) => (
            <button key={t} className={`pill ${tag === t ? 'active' : ''}`} onClick={() => setTag(t)}>
              {customTags.includes(t) && '#'}{t}
            </button>
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
                  <div className="news-title">
                    {n.is_hot && <span className="hot-badge">🔥 HOT</span>}
                    {n.title}
                  </div>
                  <div className="news-summary">{n.summary}</div>
                  <div className="news-meta">
                    {n.source} · {n.time}
                    {n.cluster_size > 1 && <span className="cluster-meta"> · 외 {n.cluster_size - 1}개 매체 보도</span>}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ))}
      </div>
    </PhoneFrame>
  )
}
