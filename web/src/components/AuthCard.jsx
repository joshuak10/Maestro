import { useState } from 'react'
import { useAuth } from '../auth/AuthContext'
import ErrorMessage from './ErrorMessage'

export default function AuthCard() {
  const { login, signup } = useAuth()
  const [mode, setMode] = useState('login') //'login' | 'signup'
  const [name, setName] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState('student')
  const [pending, setPending] = useState(false)
  const [error, setError] = useState(null)
  const isSignup = mode === 'signup'

  const switchMode = (next) => {
    setMode(next)
    setError(null)
  }

  const handleSubmit = async (e) => {
    e.preventDefault() //onSubmit on the <form> -> Enter works too
    setError(null)
    setPending(true)
    try{
      if (isSignup){
        await signup({name,username,password,role})
      }else{
        await login(username,password)
      }
    } catch (err){
        setError(err.message)
    } finally {
      setPending(false)
    }
  }
 
  return (
    <section className="card auth-card">
      <header className="heading">
        <h1>Maestro</h1>
        <p className="subtitle">{isSignup ? 'Create an account' : 'Log in to practice'}</p>
      </header>

      <div className="tabs" role="group" aria-label="Log in or sign up">
        <button type="button" className="tab" aria-pressed={!isSignup} onClick={() => switchMode('login')}>
          Log In
        </button>
        <button type="button" className="tab" aria-pressed={isSignup} onClick={() => switchMode('signup')}>
          Sign Up
        </button>
      </div>

      <form className="form" onSubmit={handleSubmit}>
        {isSignup && (
          <label className="field">
            <span>Name</span>
            <input value={name} onChange={e => setName(e.target.value)} autoComplete="name" required maxLength={100} />
          </label>
        )}

        <label className="field">
          <span>Username</span>
          <input
            value={username}
            onChange={e => setUsername(e.target.value)}
            autoComplete="username"
            autoCapitalize="none"
            spellCheck={false}
            required
            minLength={3}
            maxLength={30}
          />
        </label>

        <label className="field">
          <span>Password</span>
          <input
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            autoComplete={isSignup ? 'new-password' : 'current-password'}
            required
            minLength={8}
          />
        </label>

        {isSignup && (
          <fieldset className="field radio-group">
            <legend>I am a</legend>
            {['student', 'teacher'].map(r => (
              <label key={r} className="radio">
                <input type="radio" name="role" value={r} checked={role === r} onChange={() => setRole(r)} />
                {r}
              </label>
            ))}
          </fieldset>
        )}

        {error && <ErrorMessage message={error} />}

        <button type="submit" className="switch" disabled={pending}>
          {pending ? 'Please wait…' : isSignup ? 'Sign Up' : 'Log In'}
        </button>
      </form>
    </section>
  )
}
