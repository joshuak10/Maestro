import { useEffect, useState } from 'react'
import { apiFetch } from '../api'
import ErrorMessage from './ErrorMessage'

export default function StudentPanel() {
  const [assignments, setAssignments] = useState([])
  const [loadState, setLoadState] = useState('loading') //'loading' | 'error' | 'ready'
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    // TODO step 17: apiFetch('/assignments/me')
    //  .then -> if (!cancelled) setAssignments(data), setLoadState('ready')
    //  .catch -> if (!cancelled) setError(err.message), setLoadState('error')
    setError('TODO step 17: load assignments')
    setLoadState('error')
    return () => { cancelled = true }
  }, [])

  return (
    <section className="card panel">
      <header className="heading">
        <h1>My scales</h1>
        <p className="subtitle">Assigned by your teachers</p>
      </header>

      {loadState === 'loading' && <p className="muted">Loading…</p>}
      {loadState === 'error' && <ErrorMessage message={error} />}
      {loadState === 'ready' && assignments.length === 0 && <p className="muted">No assignments yet</p>}

      {loadState === 'ready' && assignments.length > 0 && (
        <ul className="assignment-list">
          {assignments.map(a => (
            <li key={a.id} className="assignment">
              <span className="assignment-scale">{a.scale.name}</span>
              <span className="muted">
                from {a.teacher.name} · {new Date(a.created_at).toLocaleDateString()}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
