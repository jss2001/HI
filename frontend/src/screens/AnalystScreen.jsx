import { useEffect, useRef, useState } from 'react'
import PhoneFrame from '../components/PhoneFrame'

const QUICK_PICKS = ['삼성전자', 'SK하이닉스', 'LG에너지솔루션', '셀트리온', '현대차']
const COMPARE_PICKS = [['삼성전자', 'SK하이닉스'], ['현대차', '기아'], ['NAVER', '카카오']]

const VERDICT_STYLE = {
  BULL_WINS: { label: '강세 우세', emoji: '🐂', color: '#dc2626' },
  BEAR_WINS: { label: '약세 우세', emoji: '🐻', color: '#2563eb' },
  TIE: { label: '팽팽함', emoji: '⚖️', color: '#7c3aed' },
  NEEDS_MORE_DATA: { label: '데이터 부족', emoji: '🔍', color: '#6b7280' },
}

// 페르소나 — Threads 인플루언서 처럼 커리어 시그널
const PERSONA = {
  bull: {
    name: '강세론자 김불',
    bio: '10년 전업 · 적극 매수파',
    handle: '@bull_ai',
  },
  bear: {
    name: '약세론자 박베어',
    bio: '前 헤지펀드 RM 13년 · 위험관리 전문',
    handle: '@bear_ai',
  },
  judge: {
    name: 'Judge',
    bio: '데이터 종합 중재자',
    handle: '@judge_ai',
  },
  community: {
    name: 'Community',
    bio: '네이버 블로그·카페 종합',
    handle: '@community',
  },
  timeline: {
    name: 'Timeline',
    bio: '시계열 이벤트 기록',
    handle: '@timeline',
  },
  action: {
    name: 'Action',
    bio: '시각 정리 (투자권유 X)',
    handle: '@action',
  },
  system: {
    name: 'HI Brief',
    bio: '오늘의 한 줄',
    handle: '@hi',
  },
  quant: {
    name: 'Quant',
    bio: '시세·수급·공매도·컨센서스',
    handle: '@quant',
  },
}

function StockSearchInput({ value, onChange, onPick, placeholder, style }) {
  const [results, setResults] = useState([])
  const [searching, setSearching] = useState(false)
  const [open, setOpen] = useState(false)
  const blurTimer = useRef(null)

  useEffect(() => {
    const q = (value || '').trim()
    if (!q) { setResults([]); return }
    setSearching(true)
    const h = setTimeout(async () => {
      try {
        const r = await fetch(`/api/search?q=${encodeURIComponent(q)}`)
        const j = await r.json()
        setResults(j.results || [])
      } catch {} finally { setSearching(false) }
    }, 200)
    return () => clearTimeout(h)
  }, [value])

  return (
    <div className="search-suggest-wrap" style={style}>
      <input
        className="search-input"
        placeholder={placeholder}
        value={value}
        onChange={(e) => { onChange(e.target.value); setOpen(true) }}
        onFocus={() => setOpen(true)}
        onBlur={() => { blurTimer.current = setTimeout(() => setOpen(false), 150) }}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && open && results[0]) {
            e.preventDefault()
            onPick(results[0])
            setOpen(false)
          }
        }}
      />
      {open && results.length > 0 && (
        <div className="search-suggest">
          {results.map((r) => (
            <div
              key={r.stock_code}
              className="search-suggest-row"
              onMouseDown={(e) => {
                e.preventDefault()
                clearTimeout(blurTimer.current)
                onPick(r)
                setOpen(false)
              }}
            >
              <span className="search-suggest-name">{r.corp_name}</span>
              <span className="search-suggest-code">{r.stock_code}</span>
            </div>
          ))}
        </div>
      )}
      {open && searching && results.length === 0 && value && (
        <div className="search-suggest-loading">검색 중…</div>
      )}
    </div>
  )
}


function ThreadPost({ kind, children, last }) {
  const p = PERSONA[kind]
  const icons = {
    bull: '🐂', bear: '🐻', judge: '⚖️',
    community: '💬', timeline: '📅', action: '💡', system: '✦', quant: '📊',
  }
  return (
    <div className={`tp ${last ? 'tp-last' : ''}`}>
      <div className="tp-avatar-col">
        <div className={`tp-avatar ${kind}`}>{icons[kind]}</div>
        {!last && <div className="tp-line" />}
      </div>
      <div className="tp-body">
        <div className="tp-head">
          <span className="tp-name">{p.name}</span>
          <span className="tp-verified">✓</span>
          <span className="tp-handle">{p.handle}</span>
        </div>
        <div className="tp-bio">{p.bio}</div>
        <div className="tp-content">{children}</div>
      </div>
    </div>
  )
}

function MiniChart({ closes, ma20, dates }) {
  if (!closes?.length) return null
  const w = 320, h = 100
  const valid = closes.filter(v => v != null)
  const min = Math.min(...valid)
  const max = Math.max(...valid)
  const range = max - min || 1
  const toX = (i) => (i / (closes.length - 1)) * w
  const toY = (v) => h - ((v - min) / range) * (h - 8) - 4
  const closesPath = closes
    .map((v, i) => `${i === 0 ? 'M' : 'L'}${toX(i).toFixed(1)},${toY(v).toFixed(1)}`)
    .join(' ')
  const ma20Path = ma20
    .map((v, i) => v == null ? null : `${toX(i).toFixed(1)},${toY(v).toFixed(1)}`)
    .filter(Boolean)
    .map((p, i) => `${i === 0 ? 'M' : 'L'}${p}`)
    .join(' ')
  const last = closes[closes.length - 1]
  const first = closes[0]
  const up = last >= first
  return (
    <svg viewBox="0 0 320 100" preserveAspectRatio="none" className="tech-chart">
      <defs>
        <linearGradient id="cgrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={up ? '#d92e2e' : '#2563eb'} stopOpacity="0.18" />
          <stop offset="100%" stopColor={up ? '#d92e2e' : '#2563eb'} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={`${closesPath} L${w},${h} L0,${h} Z`} fill="url(#cgrad)" />
      <path d={closesPath} fill="none" stroke={up ? '#d92e2e' : '#2563eb'} strokeWidth="1.6" strokeLinejoin="round" />
      {ma20Path && <path d={ma20Path} fill="none" stroke="#94a3b8" strokeWidth="1" strokeDasharray="3,3" />}
    </svg>
  )
}

function TechSignals({ tech }) {
  if (!tech) return null
  const sigs = []
  if (tech.rsi != null) sigs.push({ label: `RSI ${tech.rsi}`, sub: tech.rsi_label, signal: tech.rsi_signal })
  if (tech.ma_align) sigs.push({ label: tech.ma_align, sub: '이평선', signal: tech.ma_signal })
  if (tech.vol_label && tech.vol_label !== '—') sigs.push({ label: tech.vol_label, sub: tech.vol_ratio ? `${tech.vol_ratio}배` : '', signal: tech.vol_signal })
  if (tech.cross_event) sigs.push({ label: tech.cross_event, sub: '⚠️ 최근', signal: tech.cross_event === '골든크로스' ? 'positive' : 'negative' })
  return (
    <div className="tech-sig-row">
      {sigs.map((s, i) => (
        <div key={i} className={`tech-sig ${s.signal}`}>
          <div className="tech-sig-main">{s.label}</div>
          {s.sub && <div className="tech-sig-sub">{s.sub}</div>}
        </div>
      ))}
    </div>
  )
}

function PointList({ points, side }) {
  return (
    <ul className="tp-points">
      {points.map((p, i) => (
        <li key={i} className="tp-point">
          <span>{p.text}</span>
          {p.sources?.length > 0 && (
            <span className="tp-srcs">
              {p.sources.map((s, j) => <span key={j} className={`tp-src ${side}`}>{s}</span>)}
            </span>
          )}
        </li>
      ))}
    </ul>
  )
}

function QuotedPost({ q, side }) {
  return (
    <a href={q.link} target="_blank" rel="noreferrer" className={`tp-quoted ${side}`}>
      <div className="tp-quoted-meta">
        <span className="tp-quoted-source">{q.source === 'cafe' ? '카페' : '블로그'}</span>
        <span className="tp-quoted-date">· {q.date}</span>
        {q.verified && <span className="tp-quoted-vrf">✓ 진짜 글</span>}
      </div>
      <div className="tp-quoted-title">{q.title}</div>
      <div className="tp-quoted-snippet">"{q.snippet}"</div>
    </a>
  )
}

export default function AnalystScreen({ tabBar }) {
  const [mode, setMode] = useState('single')
  const [query, setQuery] = useState('')
  const [queryB, setQueryB] = useState('')
  const [data, setData] = useState(null)
  const [compareData, setCompareData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [showSources, setShowSources] = useState(false)
  const [phaseText, setPhaseText] = useState('')
  const phaseTimer = useRef(null)

  useEffect(() => () => clearTimeout(phaseTimer.current), [])

  const fetchBrief = async (company) => {
    setLoading(true); setError(null); setData(null); setCompareData(null); setShowSources(false)
    const phases = ['DART 공시 수집…', '뉴스 클러스터링…', '커뮤니티 글 수집…', 'Bull 분석…', 'Bear 반박…', 'Judge 중재…']
    let i = 0; setPhaseText(phases[0])
    const tick = () => {
      i++
      if (i < phases.length) { setPhaseText(phases[i]); phaseTimer.current = setTimeout(tick, 1400) }
    }
    phaseTimer.current = setTimeout(tick, 1400)
    try {
      const r = await fetch(`/api/analyst?company=${encodeURIComponent(company)}`)
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        throw new Error(j.detail || '분석 실패')
      }
      setData(await r.json())
    } catch (e) { setError(e.message) }
    finally { clearTimeout(phaseTimer.current); setLoading(false) }
  }

  const fetchCompare = async (aName, bName) => {
    setLoading(true); setError(null); setData(null); setCompareData(null); setShowSources(false)
    setPhaseText(`${aName} vs ${bName} 동시 분석…`)
    try {
      const r = await fetch(`/api/compare?a=${encodeURIComponent(aName)}&b=${encodeURIComponent(bName)}`)
      if (!r.ok) {
        const j = await r.json().catch(() => ({}))
        throw new Error(j.detail || '비교 실패')
      }
      setCompareData(await r.json())
    } catch (e) { setError(e.message) }
    finally { setLoading(false) }
  }

  const switchMode = (next) => {
    setMode(next); setData(null); setCompareData(null); setError(null); setQueryB(''); setShowSources(false)
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (mode === 'compare') {
      if (query.trim() && queryB.trim()) fetchCompare(query.trim(), queryB.trim())
    } else {
      if (query.trim()) fetchBrief(query.trim())
    }
  }

  const verdict = data?.brief?.judge ? (VERDICT_STYLE[data.brief.judge.verdict] || VERDICT_STYLE.TIE) : null

  return (
    <PhoneFrame tabBar={tabBar}>
      <div className="app-bar">
        <div>
          <h1>종목 분석</h1>
          <div className="sub">Bull · Bear · Judge 페르소나 종합 분석</div>
        </div>
      </div>

      <div className="scroll">
        <div className="mode-switch">
          <button className={`mode-btn ${mode === 'single' ? 'on' : ''}`} onClick={() => switchMode('single')}>단일 분석</button>
          <button className={`mode-btn ${mode === 'compare' ? 'on' : ''}`} onClick={() => switchMode('compare')}>VS 비교</button>
        </div>

        <form onSubmit={handleSubmit} style={{ marginBottom: 10 }}>
          <div className="search-row">
            <StockSearchInput
              value={query}
              onChange={setQuery}
              onPick={(r) => setQuery(r.corp_name)}
              placeholder={mode === 'compare' ? '종목 A (이름/코드)' : '회사명 / 종목코드 / 영문 ticker'}
            />
            {mode === 'compare' && (
              <StockSearchInput
                value={queryB}
                onChange={setQueryB}
                onPick={(r) => setQueryB(r.corp_name)}
                placeholder="종목 B (이름/코드)"
                style={{ borderLeft: '1px solid var(--line)' }}
              />
            )}
            <button className="search-btn" type="submit">{mode === 'compare' ? '비교' : '분석'}</button>
          </div>
        </form>

        {mode === 'single' ? (
          <div className="tabs-pill" style={{ marginBottom: 14 }}>
            {QUICK_PICKS.map((c) => (
              <button key={c} className={`pill ${data?.company === c ? 'active' : ''}`}
                onClick={() => { setQuery(c); fetchBrief(c) }}>{c}</button>
            ))}
          </div>
        ) : (
          <div className="tabs-pill" style={{ marginBottom: 14 }}>
            {COMPARE_PICKS.map(([a, b]) => (
              <button key={`${a}-${b}`} className="pill"
                onClick={() => { setQuery(a); setQueryB(b); fetchCompare(a, b) }}>{a} vs {b}</button>
            ))}
          </div>
        )}

        {loading && (
          <div className="analyst-loading">
            <div className="brain-pulse">
              <div className="ring r1" /><div className="ring r2" /><div className="ring r3" />
              <div className="brain">🧠</div>
            </div>
            <div className="phase-text">{phaseText}</div>
            <div className="phase-sub">Bull · Bear · Judge 페르소나 종합 분석</div>
          </div>
        )}
        {error && <div className="empty">⚠️ {error}</div>}

        {/* 비교 모드 결과 */}
        {mode === 'compare' && compareData && !loading && (
          <div className="compare-grid">
            {[compareData.a, compareData.b].map((c, idx) => {
              const v = c.brief.judge ? VERDICT_STYLE[c.brief.judge.verdict] : null
              return (
                <div key={idx} className="compare-card">
                  <div className="compare-head">
                    <div className="compare-name">{c.company}</div>
                    <div className="compare-code">{c.stock_code}</div>
                  </div>
                  <div className="compare-headline">{c.brief.headline}</div>
                  {v && (
                    <div className="compare-verdict" style={{ color: v.color }}>
                      {v.emoji} {v.label} · {c.brief.judge.confidence}%
                    </div>
                  )}
                  <div className="compare-section">
                    <div className="compare-label">🐂 강세</div>
                    <div className="compare-text">{c.brief.bull.thesis}</div>
                  </div>
                  <div className="compare-section">
                    <div className="compare-label">🐻 약세</div>
                    <div className="compare-text">{c.brief.bear.thesis}</div>
                  </div>
                  {c.buzz && (
                    <div className="compare-foot">
                      {c.buzz.buzz_emoji} {c.buzz.buzz_label}
                      {c.brief.sentiment && ` · ${c.brief.sentiment.label}`}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}

        {/* 단일 분석 — Threads 피드 */}
        {mode === 'single' && data && !loading && (
          <div className="thread-feed">
            <div className="feed-head">
              <div>
                <div className="feed-company">{data.company}</div>
                <div className="feed-code">
                  {data.stock_code} · {data.brief.data_quality}
                </div>
              </div>
              <div className="feed-effort">
                {data.sources.filings.length}공시
                {' · '}{data.sources.news.length}뉴스
                {data.buzz && ` · ${data.buzz.counts.recent_month}커뮤니티`}
              </div>
            </div>

            <ThreadPost kind="system">
              <div className="tp-headline">{data.brief.headline}</div>
            </ThreadPost>

            {data.market && (data.market.finance || data.market.flow) && (
              <ThreadPost kind="quant">
                {data.market.finance && (
                  <div className="quant-grid">
                    {data.market.finance.price && (
                      <div className="quant-cell">
                        <div className="quant-label">현재가</div>
                        <div className={`quant-value ${(data.market.finance.change_pct || 0) >= 0 ? 'up' : 'down'}`}>
                          {data.market.finance.price.toLocaleString()}
                          {data.market.finance.change_pct !== null && data.market.finance.change_pct !== undefined && (
                            <span className="quant-chg">
                              {data.market.finance.change_pct >= 0 ? '+' : ''}{data.market.finance.change_pct.toFixed(2)}%
                            </span>
                          )}
                        </div>
                      </div>
                    )}
                    {data.market.finance.target_price && (
                      <div className="quant-cell">
                        <div className="quant-label">컨센 목표가</div>
                        <div className="quant-value">{data.market.finance.target_price.toLocaleString()}</div>
                      </div>
                    )}
                    {data.market.finance.per && (
                      <div className="quant-cell">
                        <div className="quant-label">PER</div>
                        <div className="quant-value">{data.market.finance.per}</div>
                      </div>
                    )}
                    {data.market.finance.pbr && (
                      <div className="quant-cell">
                        <div className="quant-label">PBR</div>
                        <div className="quant-value">{data.market.finance.pbr}</div>
                      </div>
                    )}
                    {data.market.finance.foreign_ratio && (
                      <div className="quant-cell">
                        <div className="quant-label">외국인 보유율</div>
                        <div className="quant-value">{data.market.finance.foreign_ratio}%</div>
                      </div>
                    )}
                    {data.market.short?.short_ratio_pct && (
                      <div className="quant-cell">
                        <div className="quant-label">공매도 잔고</div>
                        <div className="quant-value">{data.market.short.short_ratio_pct}%</div>
                      </div>
                    )}
                  </div>
                )}
                {data.market.flow && data.market.flow.foreign_5d_net !== undefined && (
                  <div className="flow-row">
                    <div className={`flow-pill ${data.market.flow.foreign_5d_net >= 0 ? 'pos' : 'neg'}`}>
                      외인 5일: {data.market.flow.foreign_5d_net >= 0 ? '+' : ''}{data.market.flow.foreign_5d_net.toLocaleString()}주
                    </div>
                    <div className={`flow-pill ${data.market.flow.institution_5d_net >= 0 ? 'pos' : 'neg'}`}>
                      기관 5일: {data.market.flow.institution_5d_net >= 0 ? '+' : ''}{data.market.flow.institution_5d_net.toLocaleString()}주
                    </div>
                  </div>
                )}
                {data.market.tech?.closes?.length > 0 && (
                  <div className="tech-block">
                    <div className="tech-meta">
                      <span>3개월 차트</span>
                      <span className="tech-meta-range">
                        {data.market.tech.low_3mo?.toLocaleString()} ~ {data.market.tech.high_3mo?.toLocaleString()}
                      </span>
                    </div>
                    <MiniChart closes={data.market.tech.closes} ma20={data.market.tech.ma20} dates={data.market.tech.dates} />
                    <TechSignals tech={data.market.tech} />
                    {data.brief.tech_take && (
                      <div className="tech-take">📈 {data.brief.tech_take}</div>
                    )}
                  </div>
                )}
              </ThreadPost>
            )}

            <ThreadPost kind="bull">
              {data.brief.bull.single_quote && (
                <div className="tp-quote-hl bull">"{data.brief.bull.single_quote}"</div>
              )}
              <div className="tp-thesis bull">{data.brief.bull.thesis}</div>
              <PointList points={data.brief.bull.points} side="bull" />
              {data.brief.bull.echoed_by?.length > 0 && (
                <div className="tp-echoed">
                  <div className="tp-echoed-label">↳ 같은 시각의 사람 글</div>
                  {data.brief.bull.echoed_by.map((q, i) => <QuotedPost key={i} q={q} side="bull" />)}
                </div>
              )}
              <div className="tp-self">
                <span className="tp-self-label">솔직히…</span> {data.brief.bull.weakness}
              </div>
            </ThreadPost>

            <ThreadPost kind="bear">
              {data.brief.bear.single_quote && (
                <div className="tp-quote-hl bear">"{data.brief.bear.single_quote}"</div>
              )}
              {data.brief.bear.rebuts_bull && (
                <div className="tp-rebut">
                  <span className="tp-rebut-arrow">↪</span>
                  <span className="tp-rebut-name">@bull_ai</span>{' '}
                  {data.brief.bear.rebuts_bull}
                </div>
              )}
              <div className="tp-thesis bear">{data.brief.bear.thesis}</div>
              <PointList points={data.brief.bear.points} side="bear" />
              {data.brief.bear.echoed_by?.length > 0 && (
                <div className="tp-echoed">
                  <div className="tp-echoed-label">↳ 같은 시각의 사람 글</div>
                  {data.brief.bear.echoed_by.map((q, i) => <QuotedPost key={i} q={q} side="bear" />)}
                </div>
              )}
              <div className="tp-self">
                <span className="tp-self-label">솔직히…</span> {data.brief.bear.weakness}
              </div>
            </ThreadPost>

            {verdict && (
              <ThreadPost kind="judge">
                <div className="tp-verdict-row">
                  <span className="tp-verdict-emoji">{verdict.emoji}</span>
                  <span className="tp-verdict-label" style={{ color: verdict.color }}>{verdict.label}</span>
                  <span className="tp-verdict-conf">{data.brief.judge.confidence}%</span>
                </div>
                <div className="tp-conf-bar">
                  <div className="tp-conf-fill" style={{ width: `${data.brief.judge.confidence}%`, background: verdict.color }} />
                </div>
                <div className="tp-judge-text">{data.brief.judge.reasoning}</div>
                <div className="tp-swing">
                  <b>판단이 뒤집힐 변수:</b> {data.brief.judge.swing_factor}
                </div>
              </ThreadPost>
            )}

            {(data.buzz || data.brief.sentiment) && (
              <ThreadPost kind="community">
                <div className="tp-vibe-row">
                  {data.buzz && (
                    <div className="tp-vibe-pill">
                      {data.buzz.buzz_emoji} {data.buzz.buzz_label}
                      <span className="tp-vibe-sub">
                        {data.buzz.api_saturated
                          ? `3일 ${data.buzz.counts.recent_3d}건`
                          : data.buzz.buzz_ratio !== null ? `${data.buzz.buzz_ratio}배` : ''}
                      </span>
                    </div>
                  )}
                  {data.brief.sentiment && (
                    <div className="tp-vibe-pill">
                      {data.brief.sentiment.label}
                      <span className="tp-vibe-sub">{data.brief.sentiment.score}점</span>
                    </div>
                  )}
                </div>
                {data.brief.sentiment && (
                  <>
                    <div className="tp-sent-bar">
                      <div className="tp-sent-track" />
                      <div className="tp-sent-marker" style={{ left: `${(data.brief.sentiment.score + 100) / 2}%` }} />
                    </div>
                    <div className="tp-judge-text">{data.brief.sentiment.summary}</div>
                    {data.brief.sentiment.tone_notes && (
                      <div className="tp-tone">자주 등장: {data.brief.sentiment.tone_notes}</div>
                    )}
                  </>
                )}
              </ThreadPost>
            )}

            {data.brief.timeline?.length > 0 && (
              <ThreadPost kind="timeline">
                <div className="tp-tone">
                  {data.period_days <= 7 ? '최근 7일' :
                   data.period_days <= 30 ? '최근 30일' :
                   data.period_days <= 90 ? '최근 3개월' : '최근 6개월'}
                  {data.period_days > 7 && ' · 단기 부족 → 자동 확장'}
                </div>
                <div className="tp-tl-list">
                  {data.brief.timeline.map((t, i) => (
                    <div key={i} className={`tp-tl-item ${t.vibe || 'neutral'}`}>
                      <div className="tp-tl-dot" />
                      <div className="tp-tl-body">
                        <div className="tp-tl-row">
                          <span className="tp-tl-date">{t.date}</span>
                          <span className={`tp-tl-kind ${t.kind}`}>{t.kind}</span>
                        </div>
                        <div className="tp-tl-event">{t.event}</div>
                        {t.why_matters && <div className="tp-tl-why">→ {t.why_matters}</div>}
                      </div>
                    </div>
                  ))}
                </div>
                {data.brief.trend_summary && <div className="tp-trend">{data.brief.trend_summary}</div>}
              </ThreadPost>
            )}

            {(data.brief.today_one_thing || data.brief.for_holders || data.brief.for_non_holders) && (
              <ThreadPost kind="action" last>
                {data.brief.today_one_thing && (
                  <div className="tp-onething">
                    <span className="tp-onething-label">⭐ 오늘 단 한 가지</span>
                    <div className="tp-onething-text">{data.brief.today_one_thing}</div>
                  </div>
                )}
                <div className="tp-action-row">
                  {data.brief.for_holders && (
                    <div className="tp-action-block holder">
                      <div className="tp-action-head">📦 보유자에게</div>
                      <div className="tp-action-text">{data.brief.for_holders}</div>
                    </div>
                  )}
                  {data.brief.for_non_holders && (
                    <div className="tp-action-block non-holder">
                      <div className="tp-action-head">👀 미보유자에게</div>
                      <div className="tp-action-text">{data.brief.for_non_holders}</div>
                    </div>
                  )}
                </div>
              </ThreadPost>
            )}

            <button className="src-toggle" onClick={() => setShowSources(!showSources)}>
              {showSources ? '▲ 원본 자료 닫기' : '▼ 원본 자료 보기'} (공시 {data.sources.filings.length}건 · 뉴스 {data.sources.news.length}건)
            </button>

            {showSources && (
              <div className="src-panel">
                <div className="src-label">📋 DART 공시</div>
                {data.sources.filings.length === 0 && <div className="src-empty">최근 공시 없음</div>}
                {data.sources.filings.map((f, i) => (
                  <a key={i} href={f.link} target="_blank" rel="noreferrer" className="src-link">
                    <span className="src-date">{f.date}</span>
                    <span className="src-title">{f.report_nm}</span>
                  </a>
                ))}
                <div className="src-label" style={{ marginTop: 14 }}>📰 뉴스</div>
                {data.sources.news.map((n, i) => (
                  <a key={i} href={n.link} target="_blank" rel="noreferrer" className="src-link">
                    <span className="src-source">[{n.source}]</span>
                    <span className="src-title">{n.title}</span>
                  </a>
                ))}
              </div>
            )}

            <div className="result-foot">
              ⚠️ 위 페르소나는 AI 시뮬레이션. 단호한 톤으로 발언하지만 투자 자문 아님.
              <br />
              {data.model}{data.tokens && ` · ${data.tokens.prompt + data.tokens.completion}t`} · DART + 네이버 + 커뮤니티 통합
            </div>
          </div>
        )}

        {!data && !compareData && !loading && !error && (
          <div className="empty-hero">
            <div className="empty-icon">🤖</div>
            <div className="empty-msg">종목 입력하면<br/><b>Bull · Bear · Judge 페르소나 종합 분석</b></div>
            <div className="empty-tags">
              <span>🐂 강세론자</span><span>🐻 약세론자</span><span>⚖️ 판단자</span>
              <span>💬 커뮤니티 분석</span><span>📅 시계열 분석</span>
            </div>
          </div>
        )}
      </div>
    </PhoneFrame>
  )
}
