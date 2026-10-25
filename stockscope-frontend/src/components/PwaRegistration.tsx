'use client'

import { useEffect } from 'react'

/** Register after the first page load so installation does not compete with research data. */
export function PwaRegistration() {
  useEffect(() => {
    if (process.env.NODE_ENV !== 'production' || !('serviceWorker' in navigator)) return

    let disposed = false
    let registration: ServiceWorkerRegistration | undefined
    let registering = false
    let lastUpdate = 0

    const register = async () => {
      if (disposed || registering || registration) return
      registering = true
      try {
        registration = await navigator.serviceWorker.register('/sw.js', {
          scope: '/',
          updateViaCache: 'none',
        })
        lastUpdate = Date.now()
      } catch {
        // Offline/private browsing must never prevent the workspace from opening.
      } finally {
        registering = false
      }
    }

    const checkForUpdate = () => {
      if (document.visibilityState !== 'visible') return
      if (!registration) {
        void register()
      } else if (Date.now() - lastUpdate > 60 * 60 * 1000) {
        lastUpdate = Date.now()
        void registration.update().catch(() => {})
      }
    }

    if (document.readyState === 'complete') void register()
    else window.addEventListener('load', register, { once: true })
    window.addEventListener('online', checkForUpdate)
    document.addEventListener('visibilitychange', checkForUpdate)

    return () => {
      disposed = true
      window.removeEventListener('load', register)
      window.removeEventListener('online', checkForUpdate)
      document.removeEventListener('visibilitychange', checkForUpdate)
    }
  }, [])

  return null
}
