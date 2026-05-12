import { useEffect, useState } from 'react'

const KEY = 'hi_market'
const EVENT = 'hi-market-change'

export function getMarket() {
  return localStorage.getItem(KEY) === 'us' ? 'us' : 'kr'
}

export function setMarket(next) {
  const v = next === 'us' ? 'us' : 'kr'
  localStorage.setItem(KEY, v)
  document.documentElement.setAttribute('data-market', v)
  window.dispatchEvent(new CustomEvent(EVENT, { detail: v }))
}

export function useMarket() {
  const [market, setLocal] = useState(getMarket)
  useEffect(() => {
    const handler = (e) => setLocal(e.detail)
    window.addEventListener(EVENT, handler)
    return () => window.removeEventListener(EVENT, handler)
  }, [])
  return market
}
