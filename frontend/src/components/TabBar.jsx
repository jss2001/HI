const tabs = [
  {
    key: 'home',
    label: '홈',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 12l9-9 9 9"/><path d="M5 10v10h14V10"/></svg>
    ),
  },
  {
    key: 'sectors',
    label: '섹터',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg>
    ),
  },
  {
    key: 'news',
    label: '뉴스',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 4h16v16H4z"/><path d="M8 8h8M8 12h8M8 16h5"/></svg>
    ),
  },
  {
    key: 'star',
    label: '관심',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="12 2 15 9 22 9.3 16.5 14 18.5 21 12 17.3 5.5 21 7.5 14 2 9.3 9 9 12 2"/></svg>
    ),
  },
  {
    key: 'me',
    label: '내정보',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 4-7 8-7s8 3 8 7"/></svg>
    ),
  },
]

export default function TabBar({ active, onChange }) {
  return (
    <div className="tab-bar">
      {tabs.map((t) => (
        <button
          key={t.key}
          className={`tab ${active === t.key ? 'active' : ''}`}
          onClick={() => onChange(t.key)}
        >
          {t.icon}
          <span>{t.label}</span>
        </button>
      ))}
    </div>
  )
}
