import { useEffect, useRef, useState } from 'react'
import PhoneFrame from '../components/PhoneFrame'

const PF_KEY = 'hi_portfolio'
const HIST_KEY = 'hi_brief_history'

function loadPF() {
  try { return JSON.parse(localStorage.getItem(PF_KEY) || '[]') } catch { return [] }
}
function savePF(arr) { localStorage.setItem(PF_KEY, JSON.stringify(arr)) }

function loadHistory() {
  try { return JSON.parse(localStorage.getItem(HIST_KEY) || '{}') } catch { return {} }
}
function saveHistory(obj) { localStorage.setItem(HIST_KEY, JSON.stringify(obj)) }

function todayKey() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`
}
function yesterdayKey() {
  const d = new Date(); d.setDate(d.getDate()-1)
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`
}

function formatComma(v) {
  const digits = String(v ?? '').replace(/[^0-9]/g, '')
  if (!digits) return ''
  return parseInt(digits, 10).toLocaleString()
}
function parseComma(v) {
  const digits = String(v ?? '').replace(/[^0-9]/g, '')
  return digits ? parseInt(digits, 10) : 0
}

function computeWeights(portfolio) {
  const explicit = portfolio.reduce((s, p) => s + (p.weight || 0), 0)
  const missing = portfolio.filter((p) => !p.weight)
  const remaining = Math.max(0, 100 - explicit)
  const auto = missing.length > 0 ? remaining / missing.length : 0
  return portfolio.map((p) => ({ ...p, _weight: p.weight || auto }))
}

function PortfolioRow({ item, withWeight, onUpdate, onRemove }) {
  const [editing, setEditing] = useState(false)
  const [avg, setAvg] = useState(item.avg_price ? item.avg_price.toLocaleString() : '')
  const [qty, setQty] = useState(item.quantity?.toString() || '')
  const [weight, setWeight] = useState(item.weight?.toString() || '')

  const cancel = () => {
    setAvg(item.avg_price ? item.avg_price.toLocaleString() : '')
    setQty(item.quantity?.toString() || '')
    setWeight(item.weight?.toString() || '')
    setEditing(false)
  }
  const save = () => {
    const avgNum = parseComma(avg)
    const next = {
      ...item,
      avg_price: avgNum || item.avg_price,
      quantity: parseInt(qty || '0', 10),
      weight: weight ? parseFloat(weight) : null,
    }
    onUpdate(next)
    setEditing(false)
  }

  if (!editing) {
    return (
      <div className="pf-item" onClick={() => setEditing(true)} role="button" tabIndex={0}>
        <div className="pf-info">
          <div className="pf-name">{item.name} <span className="pf-code">{item.stock_code}</span></div>
          <div className="pf-meta">
            평단 {item.avg_price?.toLocaleString()}
            {item.quantity > 0 && ` · ${item.quantity}주`}
            {withWeight > 0 && ` · ${withWeight.toFixed(1)}%`}
            {!item.weight && withWeight > 0 && <span className="pf-auto"> (자동)</span>}
            <span className="pf-edit-hint"> · 클릭 수정</span>
          </div>
        </div>
        <button className="pf-x" onClick={(e) => { e.stopPropagation(); onRemove() }}>×</button>
      </div>
    )
  }

  return (
    <div className="pf-item editing">
      <div className="pf-edit-head">
        <span className="pf-name">{item.name} <span className="pf-code">{item.stock_code}</span></span>
      </div>
      <div className="pf-edit-row">
        <label className="pf-edit-label">평단</label>
        <input className="pf-input" type="text" inputMode="numeric" value={avg} onChange={(e) => setAvg(formatComma(e.target.value))} />
      </div>
      <div className="pf-edit-row">
        <label className="pf-edit-label">수량</label>
        <input className="pf-input" type="number" value={qty} onChange={(e) => setQty(e.target.value)} />
      </div>
      <div className="pf-edit-row">
        <label className="pf-edit-label">비중 %</label>
        <input className="pf-input" type="number" placeholder="비워두면 자동" value={weight} onChange={(e) => setWeight(e.target.value)} />
      </div>
      <div className="pf-edit-actions">
        <button className="pf-edit-cancel" onClick={cancel}>취소</button>
        <button className="pf-edit-save" onClick={save}>저장</button>
      </div>
    </div>
  )
}


function PortfolioInput({ portfolio, setPortfolio }) {
  const [query, setQuery] = useState('')
  const [picked, setPicked] = useState(null)
  const [results, setResults] = useState([])
  const [avg, setAvg] = useState('')
  const [qty, setQty] = useState('')
  const [weight, setWeight] = useState('')
  const [searching, setSearching] = useState(false)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const withWeights = computeWeights(portfolio)

  const updateItem = (idx, next) => {
    const arr = portfolio.map((p, i) => i === idx ? next : p)
    setPortfolio(arr); savePF(arr)
  }

  // debounced search
  useEffect(() => {
    if (!query.trim() || picked) {
      setResults([])
      return
    }
    setSearching(true)
    const handle = setTimeout(async () => {
      try {
        const r = await fetch(`/api/search?q=${encodeURIComponent(query)}`)
        const j = await r.json()
        setResults(j.results || [])
      } catch {} finally { setSearching(false) }
    }, 200)
    return () => clearTimeout(handle)
  }, [query, picked])

  const select = (item) => {
    setPicked(item)
    setQuery(item.corp_name)
    setResults([])
  }

  const add = (e) => {
    e.preventDefault()
    const avgNum = parseComma(avg)
    if (!picked || !avgNum) return
    const w = weight ? parseFloat(weight) : null
    const next = [...portfolio, {
      stock_code: picked.stock_code,
      name: picked.corp_name,
      avg_price: avgNum,
      quantity: parseInt(qty || '0', 10),
      weight: w && w > 0 ? w : null,
    }]
    setPortfolio(next); savePF(next)
    setQuery(''); setPicked(null); setAvg(''); setQty(''); setWeight('')
  }
  const remove = (i) => {
    const next = portfolio.filter((_, idx) => idx !== i)
    setPortfolio(next); savePF(next)
  }

  return (
    <div className="pf-section">
      <div className="pf-list">
        {portfolio.length === 0 && (
          <div className="pf-empty">종목 이름을 검색해서 추가하세요</div>
        )}
        {withWeights.map((p, i) => (
          <PortfolioRow
            key={i}
            item={p}
            withWeight={p._weight || 0}
            onUpdate={(next) => updateItem(i, next)}
            onRemove={() => remove(i)}
          />
        ))}
      </div>

      {portfolio.length > 0 && <div className="pf-divider"><span>새 종목 추가</span></div>}

      <form onSubmit={add} className="pf-form-v2">
        <div className="pf-search-wrap">
          <input
            className="pf-input pf-input-lg"
            placeholder="종목 검색 (이름 또는 코드)"
            value={query}
            onChange={(e) => { setQuery(e.target.value); setPicked(null) }}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !picked && results[0]) {
                e.preventDefault()
                select(results[0])
              }
            }}
          />
          {results.length > 0 && !picked && (
            <div className="pf-suggest">
              {results.map((r) => (
                <div
                  key={r.stock_code}
                  className="pf-suggest-row"
                  onMouseDown={(e) => { e.preventDefault(); select(r) }}
                >
                  <span className="pf-suggest-name">{r.corp_name}</span>
                  <span className="pf-suggest-code">{r.stock_code}</span>
                </div>
              ))}
            </div>
          )}
          {searching && results.length === 0 && query && !picked && (
            <div className="pf-suggest-loading">검색 중…</div>
          )}
        </div>
        <input
          className="pf-input pf-input-lg"
          placeholder="평단가"
          type="text"
          inputMode="numeric"
          value={avg}
          onChange={(e) => setAvg(formatComma(e.target.value))}
          onKeyDown={(e) => { if (e.key === 'Enter') add(e) }}
        />
        <input
          className="pf-input pf-input-lg"
          placeholder="수량 (선택)"
          type="number"
          value={qty}
          onChange={(e) => setQty(e.target.value)}
        />
        <input
          className="pf-input pf-input-lg"
          placeholder="비중 % (선택)"
          type="number"
          value={weight}
          onChange={(e) => setWeight(e.target.value)}
        />
        <button className="pf-add pf-add-lg" type="submit" disabled={!picked || !avg}>추가</button>
      </form>
    </div>
  )
}

function MorningBrief({ data }) {
  if (!data || data.error) return null
  const b = data.brief || {}
  return (
    <div className="brief-block">
      <div className="brief-headline">{b.headline}</div>

      {data.global && Object.keys(data.global).length > 0 && (
        <div className="brief-section">
          <div className="brief-label">밤사이 해외 시장</div>
          <div className="global-grid">
            {Object.entries(data.global).map(([name, d]) => (
              <div key={name} className="global-cell">
                <div className="global-name">{name}</div>
                <div className={`global-chg ${(d.change || 0) >= 0 ? 'up' : 'down'}`}>
                  {d.change !== null && d.change !== undefined ? `${d.change >= 0 ? '+' : ''}${d.change}%` : '—'}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {b.overseas && (
        <div className="brief-section">
          <div className="brief-label">흐름</div>
          <div className="brief-text">{b.overseas}</div>
        </div>
      )}

      {b.domestic_impact && (
        <div className="brief-section">
          <div className="brief-label">국내 시장 예상</div>
          <div className="brief-text">{b.domestic_impact}</div>
        </div>
      )}

      {b.stock_impact?.length > 0 && (
        <div className="brief-section">
          <div className="brief-label">내 종목별 분석</div>
          {b.stock_impact.map((s, i) => {
            const isPos = (s.expected || '').includes('강세') || (s.expected || '').includes('우호')
            const isNeg = (s.expected || '').includes('약세') || (s.expected || '').includes('주의') || (s.expected || '').includes('우려')
            return (
              <div key={i} className="stock-impact-block">
                <div className="stock-impact-head">
                  <span className="stock-impact-name">{s.name}</span>
                  <span className={`stock-impact-tag ${isPos ? 'pos' : isNeg ? 'neg' : ''}`}>{s.expected}</span>
                </div>
                {s.thesis && (
                  <div className="stock-impact-thesis">{s.thesis}</div>
                )}
                {s.drivers?.length > 0 && s.drivers.some((d) => d) && (
                  <div className="stock-driver-block">
                    <div className="stock-mini-label">호재</div>
                    <ul className="stock-mini-list">
                      {s.drivers.filter((d) => d).map((d, j) => <li key={j}>{d}</li>)}
                    </ul>
                  </div>
                )}
                {s.risks?.length > 0 && s.risks.some((r) => r) && (
                  <div className="stock-risk-block">
                    <div className="stock-mini-label">리스크</div>
                    <ul className="stock-mini-list">
                      {s.risks.filter((r) => r).map((r, j) => <li key={j}>{r}</li>)}
                    </ul>
                  </div>
                )}
                {s.key_level && (
                  <div className="stock-impact-level">
                    <span className="stock-mini-label">가격대</span>
                    {s.key_level}
                  </div>
                )}
                {s.watchpoint && (
                  <div className="stock-impact-watch">{s.watchpoint}</div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {b.checklist?.length > 0 && (
        <div className="brief-section">
          <div className="brief-label">오늘 확인할 것</div>
          <ul className="checklist">
            {b.checklist.map((c, i) => <li key={i}>{c}</li>)}
          </ul>
        </div>
      )}

      {/* 가설은 백엔드만 저장 — 4시 brief에서 hypothesis_check로 자동 평가됨 */}
    </div>
  )
}

function EveningBrief({ data }) {
  if (!data || data.error) return null
  const b = data.brief || {}
  return (
    <div className="brief-block">
      <div className="brief-headline">{b.headline}</div>

      {b.market_summary && (
        <div className="brief-section">
          <div className="brief-label">오늘 시장</div>
          <div className="brief-text">{b.market_summary}</div>
        </div>
      )}

      {b.stock_results?.length > 0 && (
        <div className="brief-section">
          <div className="brief-label">내 종목별 결과</div>
          {b.stock_results.map((s, i) => (
            <div key={i} className="stock-impact-block">
              <div className="stock-impact-head">
                <span className="stock-impact-name">{s.name}</span>
                <span className={`stock-result-pct ${(s.today_pct || 0) >= 0 ? 'up' : 'down'}`}>
                  {(s.today_pct || 0) >= 0 ? '+' : ''}{(s.today_pct || 0).toFixed(2)}%
                </span>
                <span className="stock-impact-tag">{s.verdict}</span>
              </div>
              {s.summary && (
                <div className="stock-impact-thesis">{s.summary}</div>
              )}
              {s.key_drivers?.length > 0 && (
                <div className="stock-driver-block">
                  <div className="stock-mini-label">움직임 원인</div>
                  <ul className="stock-mini-list">
                    {s.key_drivers.filter((d) => d).map((d, j) => <li key={j}>{d}</li>)}
                  </ul>
                </div>
              )}
              {s.concerns?.length > 0 && (
                <div className="stock-risk-block">
                  <div className="stock-mini-label">우려</div>
                  <ul className="stock-mini-list">
                    {s.concerns.filter((c) => c).map((c, j) => <li key={j}>{c}</li>)}
                  </ul>
                </div>
              )}
              {s.holder_take && (
                <div className="stock-impact-level">
                  <span className="stock-mini-label">📦 보유자 시각</span>
                  {s.holder_take}
                </div>
              )}
              {s.tomorrow_watch && (
                <div className="stock-impact-watch">👀 내일: {s.tomorrow_watch}</div>
              )}
            </div>
          ))}
        </div>
      )}

      {b.hypothesis_check && (
        <div className="brief-section hypothesis-check">
          <div className="brief-label">🎯 가설 검증</div>
          <div className="brief-text">{b.hypothesis_check}</div>
        </div>
      )}

      {b.key_news?.length > 0 && (
        <div className="brief-section">
          <div className="brief-label">📰 오늘의 핵심 뉴스</div>
          <ul className="checklist">
            {b.key_news.map((n, i) => <li key={i}>{n}</li>)}
          </ul>
        </div>
      )}

      {b.tomorrow_checklist?.length > 0 && (
        <div className="brief-section">
          <div className="brief-label">📅 내일 체크리스트</div>
          <ul className="checklist">
            {b.tomorrow_checklist.map((c, i) => <li key={i}>{c}</li>)}
          </ul>
        </div>
      )}
    </div>
  )
}

export default function Briefing({ tabBar }) {
  const [portfolio, setPortfolio] = useState(loadPF)
  const [mode, setMode] = useState(() => {
    const h = new Date().getHours()
    return h >= 16 ? 'evening' : 'morning'
  })
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [autoTriggered, setAutoTriggered] = useState(false)
  const resultRef = useRef(null)

  // 결과 도착 시 첫 줄로 부드럽게 스크롤
  useEffect(() => {
    if (data && resultRef.current) {
      // 약간의 delay로 DOM 그려진 후 스크롤
      setTimeout(() => {
        resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }, 80)
    }
  }, [data])

  const fetchBrief = async () => {
    if (portfolio.length === 0) {
      setError('포트폴리오를 먼저 입력해주세요')
      return
    }
    setLoading(true); setError(null); setData(null)
    const history = loadHistory()
    const yesterday = history[yesterdayKey()]
    const today = history[todayKey()]
    const body = {
      portfolio: portfolio.map((p) => ({
        stock_code: p.stock_code, name: p.name,
        avg_price: p.avg_price, quantity: p.quantity || 0,
      })),
      yesterday_hypothesis: yesterday?.morning?.brief?.hypothesis || null,
      today_hypothesis: today?.morning?.brief?.hypothesis || null,
    }
    try {
      const r = await fetch(`/api/briefing/${mode}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const j = await r.json()
      if (j.error) throw new Error(j.error)
      setData(j)
      // 히스토리 저장 (가설 검증용)
      const histNew = { ...history }
      histNew[todayKey()] = histNew[todayKey()] || {}
      histNew[todayKey()][mode] = j
      saveHistory(histNew)
    } catch (e2) {
      setError(e2.message)
    } finally {
      setLoading(false)
    }
  }

  // 자동 트리거: 앱 열림 시 시간 + 포트폴리오 + 캐시 확인
  useEffect(() => {
    if (autoTriggered || portfolio.length === 0) return
    const history = loadHistory()
    const today = history[todayKey()] || {}
    const cached = today[mode]
    if (cached) {
      // 같은 날 같은 모드 이미 받았으면 캐시 즉시 표시
      setData(cached)
      setAutoTriggered(true)
    } else {
      // 시간 조건 (장전: 8시 이후 / 장마감: 16시 이후) 만족 시 자동 fetch
      const h = new Date().getHours()
      const ready = (mode === 'morning' && h >= 8) || (mode === 'evening' && h >= 16)
      if (ready) {
        fetchBrief()
        setAutoTriggered(true)
      }
    }
  }, [portfolio, mode, autoTriggered])

  // 모드 토글 시 그 모드의 캐시도 같이 로드
  const switchMode = (next) => {
    setMode(next)
    setData(null)
    setError(null)
    const history = loadHistory()
    const cached = (history[todayKey()] || {})[next]
    if (cached) setData(cached)
  }

  // 시간이 8시/16시 도달 시 자동 트리거 (사용자 앱 열어두면 정시 발동)
  useEffect(() => {
    const tick = () => {
      const now = new Date()
      const h = now.getHours()
      const m = now.getMinutes()
      // 8:00 / 16:00 정각에 자동 트리거 (이미 받았으면 skip)
      if ((h === 8 && m === 0) || (h === 16 && m === 0)) {
        const desiredMode = h >= 16 ? 'evening' : 'morning'
        const history = loadHistory()
        const cached = (history[todayKey()] || {})[desiredMode]
        if (!cached && portfolio.length > 0) {
          setMode(desiredMode)
          setAutoTriggered(false)  // 트리거 재허용
        }
      }
    }
    const id = setInterval(tick, 30_000)  // 30초마다 체크
    return () => clearInterval(id)
  }, [portfolio])

  return (
    <PhoneFrame tabBar={tabBar}>
      <div className="app-bar">
        <div>
          <h1>오늘의 브리핑</h1>
          <div className="sub">
            딸깍<span style={{ color: '#d92e2e' }}>.</span> · {new Date().toLocaleDateString('ko-KR', { month: 'long', day: 'numeric', weekday: 'short' })}
          </div>
        </div>
      </div>

      <div className="scroll">
        <div className="mode-switch" style={{ marginBottom: 12 }}>
          <button className={`mode-btn ${mode === 'morning' ? 'on' : ''}`} onClick={() => switchMode('morning')}>
            장전 08:00
          </button>
          <button className={`mode-btn ${mode === 'evening' ? 'on' : ''}`} onClick={() => switchMode('evening')}>
            장마감 16:00
          </button>
        </div>

        <div className="section-title"><span>내 포트폴리오</span></div>
        <PortfolioInput portfolio={portfolio} setPortfolio={setPortfolio} />

        {(() => {
          const h = new Date().getHours()
          const ready = (mode === 'morning' && h >= 8) || (mode === 'evening' && h >= 16)
          const targetTime = mode === 'morning' ? '08:00' : '16:00'
          if (loading) return <button className="brief-fetch-btn" disabled>브리핑 작성 중…</button>
          if (data) return null  // 결과 있으면 버튼 숨김
          return (
            <>
              <button
                className="brief-fetch-btn"
                onClick={fetchBrief}
                disabled={portfolio.length === 0}
              >
                {ready ? `${mode === 'morning' ? '장전' : '장마감'} 브리핑 받기` : `${targetTime} 이후 자동 생성 · 미리 보기`}
              </button>
              {!ready && portfolio.length > 0 && (
                <div className="brief-auto-note">
                  {mode === 'morning' ? '08:00' : '16:00'}에 자동 인퍼런스됩니다. 미리 받고 싶으면 위 버튼 클릭.
                </div>
              )}
            </>
          )
        })()}

        {error && <div className="empty">⚠️ {error}</div>}

        {data && (
          <div ref={resultRef}>
            <button
              className="brief-reset-btn"
              onClick={() => { setData(null); setError(null) }}
            >← 처음으로</button>
            {mode === 'morning' && <MorningBrief data={data} />}
            {mode === 'evening' && <EveningBrief data={data} />}
          </div>
        )}
      </div>
    </PhoneFrame>
  )
}
