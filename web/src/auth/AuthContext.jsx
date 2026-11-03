import { createContext, useContext, useEffect, useState } from 'react'
import { apiFetch, getToken, setOnUnauthorized } from '../api'

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
    // TODO step 14:
    //  1. POST /auth/login with { username, password }, auth: false
    //  2. setToken(access_token)
    //  3. GET /auth/me -> setUser(me), setStatus('authenticated')
    //  Let ApiErrors propagate: AuthCard shows err.message.
    throw new Error('TODO step 14: login')
  }

  const signup = async ({ name, username, password, role }) => {
    // TODO step 14: POST /auth/signup (auth: false), then `await login(username, password)`
    throw new Error('TODO step 14: signup')
  }

  const logout = () => {
    // TODO step 14: clearToken(), setUser(null), setStatus('anonymous')
    throw new Error('TODO step 14: logout')
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
