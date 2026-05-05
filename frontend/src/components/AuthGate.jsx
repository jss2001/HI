import { useEffect, useState } from 'react'

const TOKEN_KEY = 'hi_auth_token'
const EXP_KEY = 'hi_auth_exp'
const SESSION_MIN = 120  // 2시간

function getStored() {
  const token = localStorage.getItem(TOKEN_KEY)
  const exp = parseInt(localStorage.getItem(EXP_KEY) || '0', 10)
  if (!token || !exp) return null
  if (Date.now() > exp) {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(EXP_KEY)
    return null
  }
  return { token, exp }
}

function saveToken(token) {
  const exp = Date.now() + SESSION_MIN * 60 * 1000
  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(EXP_KEY, String(exp))
  return exp
}

// 모든 fetch에 X-App-Token 자동 첨부 (한 번만 patch)
let _patched = false
function patchFetch() {
  if (_patched) return
  _patched = true
  const orig = window.fetch
  window.fetch = (input, init = {}) => {
    const stored = getStored()
    if (stored && (typeof input === 'string' ? input.startsWith('/api') : (input.url || '').includes('/api'))) {
      init.headers = { ...(init.headers || {}), 'X-App-Token': stored.token }
    }
    return orig(input, init)
  }
}

export default function AuthGate({ children }) {
  const [authed, setAuthed] = useState(() => !!getStored())
  const [authRequired, setAuthRequired] = useState(null)
  const [pwd, setPwd] = useState('')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const [remainingMs, setRemainingMs] = useState(0)

  // 첫 mount 시 서버에 인증 필요 여부 확인
  useEffect(() => {
    patchFetch()
    fetch('/api/auth/check').then((r) => r.json()).then((j) => {
      setAuthRequired(j.auth_required)
      // 인증 미필요면 통과
      if (!j.auth_required) setAuthed(true)
    }).catch(() => setAuthRequired(false))
  }, [])

  // 만료 카운터
  useEffect(() => {
    if (!authed || !authRequired) return
    const tick = () => {
      const stored = getStored()
      if (!stored) {
        setAuthed(false)
        return
      }
      setRemainingMs(stored.exp - Date.now())
    }
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [authed, authRequired])

  const submit = async (e) => {
    e.preventDefault()
    if (!pwd.trim()) return
    setLoading(true); setError(null)
    try {
      const r = await fetch(`/api/auth/check?token=${encodeURIComponent(pwd)}`)
      const j = await r.json()
      if (r.ok && j.ok) {
        saveToken(pwd)
        setAuthed(true)
        setPwd('')
      } else {
        setError('비밀번호가 틀렸습니다')
      }
    } catch (e) {
      setError('연결 실패')
    } finally {
      setLoading(false)
    }
  }

  // 인증 체크 중
  if (authRequired === null) {
    return <div className="auth-loading">로딩 중…</div>
  }

  if (!authed) {
    return (
      <div className="auth-screen">
        <div className="auth-container">
          <div className="auth-brand">
            <div className="auth-mark">HI</div>
            <span className="auth-brand-name">Human Intelligence</span>
          </div>

          <h1 className="auth-h1">딸깍<span className="auth-h1-dot">.</span></h1>

          <p className="auth-tagline">
            한 번 누르면 내 포트폴리오 분석이 끝납니다.<br/>
            장전·장마감, 매일.
          </p>

          <div className="auth-features">
            <div className="auth-feat">매일 장전·장마감 자동 브리핑</div>
            <div className="auth-feat">Bull · Bear · Judge 페르소나 종합 분석</div>
            <div className="auth-feat">섹터·테마 시장 흐름</div>
          </div>

          <form className="auth-form" onSubmit={submit}>
            <input
              type="password"
              className="auth-input"
              placeholder="초대 코드"
              value={pwd}
              onChange={(e) => setPwd(e.target.value)}
              autoFocus
            />
            <button className="auth-btn" type="submit" disabled={loading || !pwd.trim()}>
              {loading ? '확인 중' : '입장'}
            </button>
            {error && <div className="auth-error">{error}</div>}
          </form>

          <div className="auth-foot">
            <span className="auth-foot-dot" />
            비공개 베타 · 2시간 세션 · DART · Naver · OpenAI
          </div>
        </div>
      </div>
    )
  }

  const logout = () => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(EXP_KEY)
    setAuthed(false)
  }

  // 만료까지 남은 시간 hh:mm:ss
  const totalSec = Math.floor(remainingMs / 1000)
  const hr = Math.floor(totalSec / 3600)
  const min = Math.floor((totalSec % 3600) / 60)
  const sec = totalSec % 60
  const showTimer = authRequired && remainingMs > 0

  return (
    <>
      {children}
      {authRequired && (
        <div className="auth-bottom">
          {showTimer && (
            <div className="auth-timer">
              ⏱ {String(hr).padStart(2, '0')}:{String(min).padStart(2, '0')}:{String(sec).padStart(2, '0')}
            </div>
          )}
          <button className="auth-logout" onClick={logout}>로그아웃</button>
        </div>
      )}
    </>
  )
}
