import { useEffect, useState } from 'react'
import { apiFetch } from '../api'
import ErrorMessage from './ErrorMessage'

export default function TeacherPanel() {
  const [scales, setScales] = useState([])
  const [loadState, setLoadState] = useState('loading') //'loading' | 'error' | 'ready'
  const [loadError, setLoadError] = useState(null)

  const [studentUsername, setStudentUsername] = useState('')
  const [selected, setSelected] = useState(() => new Set()) //scale ids
  const [pending, setPending] = useState(false)
  const [status, setStatus] = useState(null) //{ kind: 'success' | 'error', text }

  useEffect(() => {
    let cancelled = false //d

    // TODO step 16: apiFetch('/scales')
    //  .then -> if (!cancelled) setScales(data), setLoadState('ready')
    //  .catch -> if (!cancelled) setLoadError(err.message), setLoadState('error')
    apiFetch('/scales')
      .then(data=>{
        if(cancelled) return
        setScales(data)
        setLoadState('ready')
      })
      .catch(err=>{
        if (cancelled) return
        setLoadError(err.message)
        setLoadState('error')
      })
    return () => { cancelled = true }
  }, [])

  //replace the Set instead of mutating it, or React won't see the change
  const toggleScale = (id) => {
    setSelected(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const canSend = studentUsername.trim() !== '' && selected.size > 0 && !pending

  const handleSend = async (e) => {
    e.preventDefault()
    setPending(true)
    setStatus(null)
    try{
      const created = await apiFetch('/assignments', {
        method: 'POST', body: { student_username: studentUsername, scale_ids: [...selected]}
      })

      if (created.length === 0){
        setStatus({kind: "success", text: "Already assigned, nothing new"})
      }else{
        setStatus({kind: "success", text: "Assigned scales"})
      }
      setSelected(new Set())
    } catch (err){
      setStatus({kind: 'error', text: err.message})
    } finally{
      setPending(false)
    }
  }
  

  return (
    <section className="card panel">
      <header className="heading">
        <h1>Assign scales</h1>
        <p className="subtitle">Type a student's username and pick scales</p>
      </header>

      {loadState === 'loading' && <p className="muted">Loading scales…</p>}
      {loadState === 'error' && <ErrorMessage message={loadError} />}

      {loadState === 'ready' && (
        <form className="form" onSubmit={handleSend}>
          <label className="field">
            <span>Student username</span>
            <input
              value={studentUsername}
              onChange={e => setStudentUsername(e.target.value)}
              autoCapitalize="none"
              spellCheck={false}
              placeholder="e.g. alex"
            />
          </label>

          <fieldset className="field checklist">
            <legend>Scales</legend>
            {scales.map(s => (
              <label key={s.id} className="check">
                <input type="checkbox" checked={selected.has(s.id)} onChange={() => toggleScale(s.id)} />
                {s.name}
              </label>
            ))}
          </fieldset>

          <button type="submit" className="switch" disabled={!canSend}>
            {pending ? 'Sending…' : 'Send'}
          </button>
        </form>
      )}

      {/* always rendered so screen readers announce changes */}
      <div aria-live="polite" className="status">
        {status && <p className={status.kind === 'error' ? 'error' : 'success'}>{status.text}</p>}
      </div>
    </section>
  )
}
