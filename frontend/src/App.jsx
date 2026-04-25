import { useState } from 'react'
import SectorCheck from './screens/SectorCheck'
import SectorDetail from './screens/SectorDetail'
import NewsTimeline from './screens/NewsTimeline'
import TabBar from './components/TabBar'

export default function App() {
  const [view, setView] = useState({ name: 'home' })
  const [tab, setTab] = useState('home')

  const handleTab = (key) => {
    setTab(key)
    if (key === 'home') setView({ name: 'home' })
    else if (key === 'news') setView({ name: 'news' })
    else if (key === 'sectors') setView({ name: 'detail', sectorId: 'semiconductor' })
    else setView({ name: key })
  }

  const tabBar = <TabBar active={tab} onChange={handleTab} />

  let screen
  if (view.name === 'home') {
    screen = (
      <SectorCheck
        tabBar={tabBar}
        onOpenSector={(id) => { setView({ name: 'detail', sectorId: id }); setTab('sectors') }}
      />
    )
  } else if (view.name === 'detail') {
    screen = (
      <SectorDetail
        sectorId={view.sectorId}
        tabBar={tabBar}
        onBack={() => { setView({ name: 'home' }); setTab('home') }}
      />
    )
  } else if (view.name === 'news') {
    screen = <NewsTimeline tabBar={tabBar} />
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

  return <div className="stage">{screen}</div>
}
