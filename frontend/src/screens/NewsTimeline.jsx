import { useEffect, useState } from 'react'
import PhoneFrame from '../components/PhoneFrame'
import { useMarket } from '../hooks/useMarket'

const THEMES_KEY = 'hi_themes'
function getCustomThemes() {
  try { return JSON.parse(localStorage.getItem(THEMES_KEY) || '[]') } catch { return [] }
}

export default function NewsTimeline({ tabBar, initialTag }) {
  const market = useMarket()
  const [data, setData] = useState(null)
  const [tag, setTag] = useState(initialTag || '전체')
  const [customTags] = useState(getCustomThemes)

  useEffect(() => {
    if (initialTag) setTag(initialTag)
  }, [initialTag])

  // 마켓 모드 전환 시 태그를 '전체'로 리셋 (KR/US 태그 셋이 다름)
  useEffect(() => {
    setTag('전체')
  }, [market])

  useEffect(() => {
    const params = new URLSearchParams()
    params.set('market', market)
    if (tag !== '전체') params.set('tag', tag)
    const url = `/api/news?${params.toString()}`
    fetch(url).then((r) => r.json()).then(setData)
  }, [tag, market])

  const marketLabel = market === 'us' ? '미국장' : '국내장'
  return (
    <PhoneFrame tabBar={tabBar}>
      <div className="app-bar">
        <div>
          <h1>뉴스 · 타임라인 <span className={`market-tag ${market === 'us' ? 'us' : 'kr'}`}>{marketLabel}</span></h1>
          <div className="sub">{marketLabel} 관련 기사</div>
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
