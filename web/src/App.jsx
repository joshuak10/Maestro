import { useState } from 'react'
import { AuthProvider, useAuth } from './auth/AuthContext'
import AppHeader from './components/AppHeader'
import AuthCard from './components/AuthCard'
import StudentPanel from './components/StudentPanel'
import TeacherPanel from './components/TeacherPanel'
import TunerPage from './pages/TunerPage'

//no router: what's on screen is decided by auth status, then a tab
export default function App() {
  return (
    <AuthProvider>
      <Shell />
    </AuthProvider>
  )
}

function Shell() {
  const { user, status, logout } = useAuth()

  if (status === 'loading') {
    return <main className="page"><p className="muted">Loading…</p></main>
  }
  if (status === 'anonymous' || !user) {
    return <main className="page"><AuthCard /></main>
  }
  //key: a different user gets fresh tab state (always lands on Assignments)
  return <LoggedIn key={user.id} user={user} onLogout={logout} />
}

function LoggedIn({ user, onLogout }) {
  const [tab, setTab] = useState('assignments')

  return (
    <div className="shell">
      <AppHeader user={user} tab={tab} onTabChange={setTab} onLogout={onLogout} />
      {/* switching away unmounts the tuner, which stops the mic */}
      {tab === 'tuner' ? (
        <TunerPage />
      ) : (
        <main className="page">
          {user.role === 'teacher' ? <TeacherPanel /> : <StudentPanel />}
        </main>
      )}
    </div>
  )
}
