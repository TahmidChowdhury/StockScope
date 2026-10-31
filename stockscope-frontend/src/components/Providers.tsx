'use client'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { useEffect, useState } from 'react'
import LoginForm from './LoginForm'
import { MobileScrollProvider } from '@/hooks/useMobileScrollRestoration'
import { apiFetch, ApiError, AUTH_CHANGED_EVENT, AuthSession, clearAuthSession, getAuthSession } from '@/lib/api'

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
  const [sessionVersion, setSessionVersion] = useState(0)

  useEffect(() => {
    const syncSession = (event?: Event) => {
      void queryClient.cancelQueries()
      queryClient.clear()
      setSession(getAuthSession())
      setSessionVersion(version => version + 1)
      // Signing in on a phone can leave the document at the password field's
      // scroll position. Preserve reload restoration, but reset auth transitions.
      if (event) window.scrollTo(0, 0)
    }
    window.addEventListener(AUTH_CHANGED_EVENT, syncSession)
    setInvitation(new URLSearchParams(window.location.hash.slice(1)).has('invite'))
    syncSession()
    setReady(true)
    return () => window.removeEventListener(AUTH_CHANGED_EVENT, syncSession)
  }, [queryClient])

  useEffect(() => {
    if (!session) return
    const expiry = setTimeout(clearAuthSession, Math.min(session.expiresAt - Date.now(), 2147483647))
    // The server remains authoritative if credentials or signing keys changed.
    void apiFetch('/api/auth/session').catch(() => {})
    return () => clearTimeout(expiry)
  }, [session])

  return (
    <QueryClientProvider client={queryClient}>
      {!ready ? <div className="min-h-screen bg-slate-900" /> : session && !invitation ? (
        <div key={sessionVersion}>
          <MobileScrollProvider>{children}</MobileScrollProvider>
        </div>
      ) : <LoginForm onLoginSuccess={() => setInvitation(false)} />}
      {process.env.NODE_ENV === 'development' && <ReactQueryDevtools initialIsOpen={false} />}
    </QueryClientProvider>
  )
}
