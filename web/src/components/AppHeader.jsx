const TABS = [
  { id: 'assignments', label: 'Assignments' },
  { id: 'tuner', label: 'Tuner' },
]

export default function AppHeader({ user, tab, onTabChange, onLogout }) {
  return (
    <header className="app-header">
      <span className="app-header-user">
        {user.name} <span className="app-header-role">· {user.role}</span>
      </span>

      <nav className="tabs" aria-label="Sections">
        {TABS.map(t => (
          <button
            key={t.id}
            type="button"
            className="tab"
            aria-pressed={tab === t.id}
            onClick={() => onTabChange(t.id)}
          >
            {t.label}
          </button>
        ))}
      </nav>

      <button type="button" className="link-button" onClick={onLogout}>
        Log Out
      </button>
    </header>
  )
}
