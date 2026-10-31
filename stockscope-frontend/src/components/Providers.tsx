'use client'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { useEffect, useState } from 'react'
import LoginForm from './LoginForm'
import { MobileScrollProvider } from '@/hooks/useMobileScrollRestoration'
import { apiFetch, ApiError, AUTH_CHANGED_EVENT, AuthSession, clearAuthSession, getAuthSession, restoreDeviceSession, DEVICE_STATE_KEY } from '@/lib/api'

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        // iOS resumes installed apps via visibilitychange. Refresh only stale
        // active queries, while keeping their cached observations on screen.
        refetchOnWindowFocus: true,
        staleTime: 5 * 60 * 1000,
        gcTime: 10 * 60 * 1000,
        retry: (count, error) => !(error instanceof ApiError && [401, 403, 429].includes(error.status)) && count < 2,
      },
      mutations: { retry: false },
    },
  }))
  const [session, setSession] = useState<AuthSession | null>(null)
  const [invitation, setInvitation] = useState(false)
  const [ready, setReady] = useState(false)
  const [boot, setBoot] = useState(0)
  const [restoreError, setRestoreError] = useState(false)
  const [sessionVersion, setSessionVersion] = useState(0)

  useEffect(() => {
    let active = true
    const syncSession = (event?: Event) => {
      void queryClient.cancelQueries()
      queryClient.clear()
      const current = getAuthSession()
      setSession(previous => previous?.accessToken === current?.accessToken ? previous : current)
      setSessionVersion(version => version + 1)
      // Signing in on a phone can leave the document at the password field's
      // scroll position. Preserve reload restoration, but reset auth transitions.
      if (event) window.scrollTo(0, 0)
    }
    window.addEventListener(AUTH_CHANGED_EVENT, syncSession)
    const joining = new URLSearchParams(window.location.hash.slice(1)).has('invite')
    setInvitation(joining)
    setReady(false)
    setRestoreError(false)
    const initialize = async () => {
      try {
        if (!joining && !getAuthSession()) await restoreDeviceSession()
        if (active) syncSession()
      } catch {
        if (active) setRestoreError(true)
      } finally {
        if (active) setReady(true)
      }
    }
    void initialize()
    // A sign-out or account switch in another window clears its private data here too.
    const deviceChanged = (event: StorageEvent) => {
      if (event.key !== DEVICE_STATE_KEY) return
      clearAuthSession()
      setBoot(value => value + 1)
    }
    window.addEventListener('storage', deviceChanged)
    return () => {
      active = false
      window.removeEventListener(AUTH_CHANGED_EVENT, syncSession)
      window.removeEventListener('storage', deviceChanged)
    }
  }, [queryClient, boot])

  useEffect(() => {
    if (!session) return
    const renewIfExpired = () => {
      if (Date.now() < session.expiresAt) return
      clearAuthSession()
      setBoot(value => value + 1)
    }
    const expiry = setTimeout(renewIfExpired, Math.min(session.expiresAt - Date.now(), 2147483647))
    const onResume = () => { if (document.visibilityState === 'visible') renewIfExpired() }
    document.addEventListener('visibilitychange', onResume)
    void apiFetch('/api/auth/session').catch(() => {})
    return () => { clearTimeout(expiry); document.removeEventListener('visibilitychange', onResume) }
  }, [session])

  return (
    <QueryClientProvider client={queryClient}>
      {!ready ? <div className="min-h-screen bg-slate-900" /> : restoreError ? (
        <main className="flex min-h-dvh flex-col items-center justify-center gap-4 px-6 text-center">
          <h1 className="text-xl">Couldn’t reconnect to StockScope</h1>
          <p className="text-sm text-slate-400">Check your connection and try again to restore your session.</p>
          <button className="button-secondary" onClick={() => setBoot(value => value + 1)}>Retry connection</button>
        </main>
      ) : session && !invitation ? (
        <div key={sessionVersion}>
          <MobileScrollProvider>{children}</MobileScrollProvider>
        </div>
      ) : <LoginForm onLoginSuccess={() => setInvitation(false)} />}
      {process.env.NODE_ENV === 'development' && <ReactQueryDevtools initialIsOpen={false} />}
    </QueryClientProvider>
  )
}
