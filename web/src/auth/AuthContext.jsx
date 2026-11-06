import { createContext, useContext, useEffect, useState } from 'react'
import { apiFetch, getToken, setOnUnauthorized, setToken, clearToken} from '../api'

const AuthContext = createContext(null)

//status: 'loading' (checking a stored token) | 'authenticated' | 'anonymous'
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [status, setStatus] = useState(() => (getToken() ? 'loading' : 'anonymous'))

  //any 401 on an authed request (expired/garbage token) -> back to the login card
  useEffect(() => {
    setOnUnauthorized(() => {
      setUser(null)
      setStatus('anonymous')
    })
    return () => setOnUnauthorized(null)
  }, [])

  //on startup: a stored token is only trusted once /auth/me accepts it
  //(StrictMode runs this twice in dev -> two /auth/me calls in Network; the cancel flag handles it)
  useEffect(() => {
    if (!getToken()) return
    let cancelled = false
    apiFetch('/auth/me')
      .then(me => {
        if (cancelled) return
        setUser(me)
        setStatus('authenticated')
      })
      .catch(() => {
        //a 401 already cleared the token in apiFetch; a network error keeps it for the next reload
        if (!cancelled) setStatus('anonymous')
      })
    return () => { cancelled = true }
  }, [])

  const login = async (username, password) => {
    //no try/catch: ApiErrors propagate so AuthCard can show err.message
    
    const { access_token } = await apiFetch('/auth/login', {
      method: 'POST',
      body: { username, password },
      auth: false, 
    })
    setToken(access_token)
    const me = await apiFetch('/auth/me')
    setUser(me)
    setStatus('authenticated')
  }

  const signup = async ({ name, username, password, role }) => {
    // TODO step 14: POST /auth/signup (auth: false), then `await login(username, password)`
      const { user } = await apiFetch('/auth/signup', {
        method: 'POST',
        body: {name, username, password, role},
        auth: false,
      })
      await login(username, password)
  }

  const logout = () => {
    // TODO step 14: clearToken(), setUser(null), setStatus('anonymous')
    clearToken()
    setUser(null)
    setStatus('anonymous')
  }

  return (
    <AuthContext.Provider value={{ user, status, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
