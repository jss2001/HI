import { useEffect, useState } from 'react'
import AuthGate from './components/AuthGate'
import Briefing from './screens/Briefing'
import SectorCheck from './screens/SectorCheck'
import SectorDetail from './screens/SectorDetail'
import NewsTimeline from './screens/NewsTimeline'
import AnalystScreen from './screens/AnalystScreen'
import ThemeDetail from './screens/ThemeDetail'
import ExchangeReport from './screens/ExchangeReport'
import TabBar from './components/TabBar'

export default function App() {
  const [view, setView] = useState({ name: 'home' })
  const [tab, setTab] = useState('home')

  // 초기 테마 + 마켓 모드 적용 (PhoneFrame이 토글 버튼 가짐)
  useEffect(() => {
    const savedTheme = localStorage.getItem('hi_theme') || 'light'
    document.documentElement.setAttribute('data-theme', savedTheme)
    const savedMarket = localStorage.getItem('hi_market') === 'us' ? 'us' : 'kr'
    document.documentElement.setAttribute('data-market', savedMarket)

    const handleNav = (e) => setView(e.detail)
    window.addEventListener('hi-nav', handleNav)
    return () => window.removeEventListener('hi-nav', handleNav)
  }, [])

  const handleTab = (key) => {
    setTab(key)
    if (key === 'home') setView({ name: 'home' })  // Briefing
    else if (key === 'news') setView({ name: 'news' })
    else if (key === 'sectors') setView({ name: 'sector_home' })
    else if (key === 'analyst') setView({ name: 'analyst' })
    else setView({ name: key })
  }

  const tabBar = <TabBar active={tab} onChange={handleTab} />

  let screen
  if (view.name === 'home') {
    screen = <Briefing tabBar={tabBar} />
  } else if (view.name === 'sector_home') {
    screen = (
      <SectorCheck
        tabBar={tabBar}
        onOpenSector={(id) => { setView({ name: 'detail', sectorId: id }); setTab('sectors') }}
        onOpenTheme={(kw) => setView({ name: 'theme', keyword: kw })}
      />
    )
  } else if (view.name === 'detail') {
    screen = (
      <SectorDetail
        sectorId={view.sectorId}
        tabBar={tabBar}
        onBack={() => { setView({ name: 'home' }); setTab('home') }}
        onOpenNews={(name) => { setView({ name: 'news', tag: name }); setTab('news') }}
      />
    )
  } else if (view.name === 'news') {
    screen = <NewsTimeline tabBar={tabBar} initialTag={view.tag} />
  } else if (view.name === 'analyst') {
    screen = <AnalystScreen tabBar={tabBar} />
  } else if (view.name === 'theme') {
    screen = (
      <ThemeDetail
        keyword={view.keyword}
        tabBar={tabBar}
        onBack={() => { setView({ name: 'home' }); setTab('home') }}
        onOpenNews={(kw) => { setView({ name: 'news', tag: kw }); setTab('news') }}
      />
    )
  } else if (view.name === 'exchange') {
    screen = <ExchangeReport tabBar={tabBar} onBack={() => setView({ name: 'home' })} />
  } else {
    screen = <SectorCheck tabBar={tabBar} onOpenSector={(id) => setView({ name: 'detail', sectorId: id })} />
  }

  const showcase = window.location.hash === '#showcase'

  if (showcase) {
    return (
      <div className="stage">
        <SectorCheck tabBar={<TabBar active="home" onChange={() => {}} />} onOpenSector={() => {}} />
        <SectorDetail sectorId="semiconductor" tabBar={<TabBar active="sectors" onChange={() => {}} />} onBack={() => {}} />
        <NewsTimeline tabBar={<TabBar active="news" onChange={() => {}} />} />
      </div>
    )
  }

  return (
    <AuthGate>
      <div className="stage">{screen}</div>
    </AuthGate>
  )
}
