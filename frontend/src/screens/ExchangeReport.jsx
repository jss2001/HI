import { useEffect, useState } from 'react'
import PhoneFrame from '../components/PhoneFrame'

const FLAGS = {
  "USD": "🇺🇸",
  "EUR": "🇪🇺",
  "JPY": "🇯🇵",
  "CNY": "🇨🇳"
}

export default function ExchangeReport({ tabBar, onBack }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const r = await fetch('/api/exchange/report')
        const j = await r.json()
        if (j.detail) throw new Error(j.detail)
        setData(j)
      } catch (e) {
        setError(e.message)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  return (
    <PhoneFrame tabBar={tabBar} hideTopActions>
      <div className="exchange-screen">
        <div className="app-bar ex-app-bar">
          <button className="ex-back-btn" onClick={onBack}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
          </button>
          <div className="ex-title-group">
            <h1 className="ex-title">환율 리포트</h1>
            <div className="ex-subtitle">Market Exchange Analysis</div>
          </div>
          <div style={{ width: 40 }} />
        </div>

        <div className="scroll ex-scroll">
          {loading && (
            <div className="ex-loading">
              <div className="spinner" />
              <p>시장 데이터를 분석하고 있습니다…</p>
            </div>
          )}
          
          {error && <div className="ex-error">⚠️ {error}</div>}

          {data && (
            <div className="ex-body fade-in">
              <div className="ex-section-label">주요 통화 현황</div>
              <div className="ex-grid-v2">
                {data.analysis.map((item) => (
                  <div key={item.code} className={`ex-glass-card ${item.is_outlier ? 'ex-alert' : 'ex-normal'}`}>
                    <div className="ex-card-head">
                      <span className="ex-card-code">
                        <span className="ex-flag">{FLAGS[item.code] || '🌐'}</span>
                        {item.code}
                      </span>
                      {item.is_outlier && <span className="ex-card-tag">이상 변동</span>}
                    </div>
                    <div className="ex-card-price">
                      <span className="ex-unit">₩</span>
                      {item.current_price.toLocaleString()}
                    </div>
                    <div className={`ex-card-chg ${item.change_pct >= 0 ? 'up' : 'down'}`}>
                      {item.change_pct >= 0 ? '▲' : '▼'} {Math.abs(item.change_pct)}%
                    </div>
                    <div className="ex-card-footer">
                      {item.signal ? (
                        <span className="ex-card-signal">{item.signal}</span>
                      ) : (
                        <span className="ex-card-vol">변동성 {item.volatility}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              <div className="ex-section-label">자동 분석 리포트</div>
              <div className="ex-report-card-v2">
                <div className="ex-report-header">
                  <span className="ex-report-icon">📊</span>
                  <span className="ex-report-title">AI 마켓 분석 전문</span>
                </div>
                <div className="ex-report-body">
                  <pre>{data.report}</pre>
                </div>
              </div>
              
              <div style={{ height: 60 }} />
            </div>
          )}
        </div>
      </div>
    </PhoneFrame>
  )
}
