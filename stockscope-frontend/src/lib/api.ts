import type { SimpleAuthResponse } from '@/types'

export const API_BASE_URL = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(/\/$/, '')
export const AUTH_CHANGED_EVENT = 'stockscope:auth-changed'
const SESSION_KEY = 'stockscope_session'
const ROLES = ['admin', 'demo', 'guest'] as const

export interface AuthSession {
  accessToken: string
  role: 'admin' | 'demo' | 'guest'
  expiresAt: number
}

export class ApiError extends Error {
  constructor(message: string, public readonly status: number) {
    super(message)
    this.name = 'ApiError'
  }
}

function removeLegacyCredentials() {
  window.localStorage.removeItem('stockscope_password')
  window.localStorage.removeItem('stockscope_authenticated')
}

export function clearAuthSession(): void {
  if (typeof window === 'undefined') return
  window.sessionStorage.removeItem(SESSION_KEY)
  removeLegacyCredentials()
  window.dispatchEvent(new Event(AUTH_CHANGED_EVENT))
}

export function getAuthSession(): AuthSession | null {
  if (typeof window === 'undefined') return null
  removeLegacyCredentials()
  const stored = window.sessionStorage.getItem(SESSION_KEY)
  if (!stored) return null
  try {
    const session = JSON.parse(stored) as AuthSession
    if (
      typeof session.accessToken !== 'string' || !session.accessToken ||
      !ROLES.includes(session.role) ||
      !Number.isFinite(session.expiresAt) || session.expiresAt <= Date.now()
    ) {
      clearAuthSession()
      return null
    }
    return session
  } catch {
    clearAuthSession()
    return null
  }
}

export function saveAuthSession(response: SimpleAuthResponse): void {
  if (
    !response.success || !response.access_token || response.token_type !== 'bearer' ||
    !ROLES.includes(response.role) || !Number.isFinite(response.expires_in_seconds) ||
    response.expires_in_seconds <= 0
  ) throw new Error('The server did not return a valid session. Please sign in again.')
  const session: AuthSession = {
    accessToken: response.access_token,
    role: response.role,
    expiresAt: Date.now() + response.expires_in_seconds * 1000,
  }
  removeLegacyCredentials()
  window.sessionStorage.setItem(SESSION_KEY, JSON.stringify(session))
  window.dispatchEvent(new Event(AUTH_CHANGED_EVENT))
}

/** Authenticated requests are limited to this application's API origin. */
export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  if (!path.startsWith('/api/') || /[?&]password=/i.test(path)) {
    throw new Error('Use an API path without password query parameters')
  }
  const session = getAuthSession()
  if (!session) {
    clearAuthSession()
    throw new ApiError('Your session has ended. Please sign in again.', 401)
  }
  const headers = new Headers(init.headers)
  headers.set('Authorization', `Bearer ${session.accessToken}`)
  const controller = new AbortController()
  const cancel = () => controller.abort()
  if (init.signal?.aborted) cancel()
  else init.signal?.addEventListener('abort', cancel, { once: true })
  let timedOut = false
  const timer = setTimeout(() => {
    timedOut = true
    controller.abort()
  }, !init.method || init.method === 'GET' ? 45000 : 180000)
  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { ...init, signal: controller.signal, headers, cache: 'no-store', redirect: 'error' })
  } catch (error) {
    if (timedOut) throw new ApiError('The server took too long to respond. Please try again.', 504)
    throw error
  } finally {
    clearTimeout(timer)
    init.signal?.removeEventListener('abort', cancel)
  }
  if (response.status === 401) {
    // An old in-flight request must not clear a newer login session.
    if (getAuthSession()?.accessToken === session.accessToken) clearAuthSession()
    throw new ApiError('Your session has ended. Please sign in again.', 401)
  }
  return response
}
