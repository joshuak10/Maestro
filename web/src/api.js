//one way to call the API: JSON in/out, token attached, errors turned into readable ApiErrors
export const API_BASE = import.meta.env.DEV ? 'http://localhost:8000' : ''

const TOKEN_KEY = 'token'

//localStorage can throw (private mode, blocked storage) -> treat that as "no token"
export function getToken() {
  try { return localStorage.getItem(TOKEN_KEY) } catch { return null }
}
export function setToken(token) {
  try { localStorage.setItem(TOKEN_KEY, token) } catch { /* ignore */ }
}
export function clearToken() {
  try { localStorage.removeItem(TOKEN_KEY) } catch { /* ignore */ }
}

//AuthContext registers this so any 401 on an authed request logs the user out
let onUnauthorized = null
export function setOnUnauthorized(fn) {
  onUnauthorized = fn
}

export class ApiError extends Error {
  constructor(status, message) {
    super(message)
    this.name = 'ApiError'
    this.status = status //0 = network error
  }
}

//FastAPI errors: ours have detail as a string, 422s have detail as a list of {loc, msg}
function messageFrom(data, res) {
  const detail = data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map(d => `${d.loc?.at(-1) ?? 'request'}: ${d.msg}`).join('; ')
  }
  return `Request failed (${res.status})`
}

/**
 * apiFetch('/scales')
 * apiFetch('/assignments', { method: 'POST', body: {...} })
 * apiFetch('/auth/login', { method: 'POST', body: {...}, auth: false })
 * Resolves to the parsed JSON; throws ApiError on any non-2xx or network failure.
 */
export async function apiFetch(path, { method = 'GET', body, auth = true } = {}) {
  const headers = { Accept: 'application/json' }
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  const token = auth ? getToken() : null
  if (token) headers.Authorization = `Bearer ${token}`

  let res
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    throw new ApiError(0, 'Could not reach the server')
  }

  const data = await res.json().catch(() => null)
  if (!res.ok) {
    //only a token we SENT being rejected means "logged out"; a failed login is just a 401 message
    if (res.status === 401 && token) {
      clearToken()
      onUnauthorized?.()
    }
    throw new ApiError(res.status, messageFrom(data, res))
  }
  return data
}
