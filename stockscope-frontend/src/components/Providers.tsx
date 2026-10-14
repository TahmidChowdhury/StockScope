'use client'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import LoginForm from './LoginForm'
import { apiFetch, ApiError, AUTH_CHANGED_EVENT, AuthSession, clearAuthSession, getAuthSession } from '@/lib/api'

export function Providers({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        refetchOnWindowFocus: false,
        staleTime: 5 * 60 * 1000,
        gcTime: 10 * 60 * 1000,
        retry: (count, error) => !(error instanceof ApiError && error.status === 401) && count < 2,
      },
      mutations: { retry: false },
    },
  }))
  const [session, setSession] = useState<AuthSession | null>(null)
  const [ready, setReady] = useState(false)
  const [sessionVersion, setSessionVersion] = useState(0)

  useEffect(() => {
    const syncSession = () => {
      void queryClient.cancelQueries()
      queryClient.clear()
      setSession(getAuthSession())
      setSessionVersion(version => version + 1)
    }
    window.addEventListener(AUTH_CHANGED_EVENT, syncSession)
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
      {!ready ? <div className="min-h-screen bg-slate-900" /> : session ? (
        <div key={sessionVersion}>
          {(pathname.startsWith('/fundamentals/') || pathname.startsWith('/stock/')) && (
            <nav aria-label="Session controls" className="flex items-center justify-between border-b border-white/10 bg-slate-900 px-4 py-3 text-sm text-white">
              <Link href="/" className="text-blue-300">Dashboard</Link>
              <button onClick={clearAuthSession}>Logout</button>
            </nav>
          )}
          {children}
        </div>
      ) : <LoginForm onLoginSuccess={() => {}} />}
      {process.env.NODE_ENV === 'development' && <ReactQueryDevtools initialIsOpen={false} />}
    </QueryClientProvider>
  )
}
