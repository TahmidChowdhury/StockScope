import type { SimpleAuthResponse } from '@/types'

export const API_BASE_URL = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(/\/$/, '')
export const AUTH_CHANGED_EVENT = 'stockscope:auth-changed'
const SESSION_KEY = 'stockscope_session'
export const DEVICE_STATE_KEY = 'stockscope_device_state'
let generation = 0
let pendingRestore: { state: string; generation: number; promise: Promise<void> } | undefined
let endingSession: Promise<unknown> | undefined

export async function requestDeviceSession(action: string, credentials?: object, signal?: AbortSignal) {
  if (action !== 'forget' && endingSession) await endingSession
  return fetch('/api/device-session', {
    method: 'POST', headers: { 'Content-Type': 'application/json', 'X-StockScope-Device': '1' },
    credentials: 'same-origin', cache: 'no-store', redirect: 'error', signal,
    body: JSON.stringify({ action, credentials }),
  })
}

export function rememberDevice(enabled: boolean) {
  // Non-secret signal for logout while offline and for open windows to sync.
  window.localStorage.setItem(DEVICE_STATE_KEY, (enabled ? 'remember:' : 'forget:') + Date.now())
}

export function restoreDeviceSession(): Promise<void> {
  const state = window.localStorage.getItem(DEVICE_STATE_KEY)
  if (!state?.startsWith('remember:')) return Promise.resolve()
  if (pendingRestore?.state === state && pendingRestore.generation === generation) return pendingRestore.promise
  const started = generation
  const promise = (async () => {
    const response = await requestDeviceSession('resume')
    if (started !== generation || window.localStorage.getItem(DEVICE_STATE_KEY) !== state) return
    if (response.status === 401) { rememberDevice(false); return }
    const session = await readApiJson<SimpleAuthResponse>(response, 'Could not reconnect to your workspace.')
    if (started === generation && window.localStorage.getItem(DEVICE_STATE_KEY) === state) saveAuthSession(session)
  })().finally(() => { if (pendingRestore?.promise === promise) pendingRestore = undefined })
  pendingRestore = { state, generation: started, promise }
  return promise
}

export function signOut() {
  const revoke = getAuthSession()?.user ? apiFetch('/api/auth/sign-out', { method: 'POST' }) : Promise.resolve()
  rememberDevice(false)
  clearAuthSession()
  endingSession = Promise.allSettled([revoke, requestDeviceSession('forget')]).finally(() => { endingSession = undefined })
}
const ROLES = ['admin', 'demo', 'guest', 'member', 'viewer'] as const

export interface AuthSession {
  isFirstSession?: boolean
  user?: { id: string; name: string; email: string; role: string }
  accessToken: string
  role: 'admin' | 'demo' | 'guest' | 'member' | 'viewer'
  expiresAt: number
}

export class ApiError extends Error {
  constructor(message: string, public readonly status: number, public readonly retryAt: number | null = null) {
    super(message)
    this.name = 'ApiError'
  }
}

/** Retry-After supports delay seconds and HTTP dates. Invalid values allow manual retry. */
export function retryAfterDeadline(value: string | null, now = Date.now()): number | null {
  if (!value?.trim()) return null
  const text = value.trim()
  const numeric = /^[+-]?\d+(?:\.\d+)?$/.test(text)
  const seconds = Number(text)
  const time = numeric ? (seconds >= 0 ? now + seconds * 1000 : NaN) : Date.parse(text)
  return Number.isFinite(time) && Math.abs(time) <= 8.64e15 ? time : null
}

/** Preserve actionable API errors instead of turning rate limits into missing data. */
export async function readApiJson<T>(response: Response, fallback: string): Promise<T> {
  if (response.ok) return response.json()
  const retryAt = response.status === 429 ? retryAfterDeadline(response.headers.get('Retry-After')) : null
  let message = fallback
  try {
    const body = await response.json()
    if (typeof body.detail === 'string') message = body.detail
  } catch { /* Proxy errors may not be JSON. */ }
  if (retryAt !== null) message += ` Available after ${new Date(retryAt).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', timeZoneName: 'short' })}.`
  throw new ApiError(message, response.status, retryAt)
}

function removeLegacyCredentials() {
  window.localStorage.removeItem('stockscope_password')
  window.localStorage.removeItem('stockscope_authenticated')
}

export function clearAuthSession(): void {
  if (typeof window === 'undefined') return
  generation++
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

export function saveAuthSession(response: SimpleAuthResponse, isFirstSession = false): void {
  if (
    !response.success || !response.access_token || response.token_type !== 'bearer' ||
    !ROLES.includes(response.role) || !Number.isFinite(response.expires_in_seconds) ||
    response.expires_in_seconds <= 0
  ) throw new Error('The server did not return a valid session. Please sign in again.')
  const session: AuthSession = {
    isFirstSession,
    user: response.user,
    accessToken: response.access_token,
    role: response.role,
    expiresAt: Date.now() + response.expires_in_seconds * 1000,
  }
  removeLegacyCredentials()
  generation++
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
