'use client'

import { createContext, useContext, useLayoutEffect, useRef, useState, type ReactNode } from 'react'
import { createMobileScrollManager } from '@/lib/mobile-scroll'

const MobileScrollContext = createContext<ReturnType<typeof createMobileScrollManager> | null>(null)

/** Key this provider by auth session, so navigation state cannot cross sign-ins. */
export function MobileScrollProvider({ children }: { children: ReactNode }) {
  const [manager] = useState(createMobileScrollManager)
  useLayoutEffect(() => manager.start(), [manager])
  return <MobileScrollContext.Provider value={manager}>{children}</MobileScrollContext.Provider>
}

export function useMobileScrollRestoration() {
  const manager = useContext(MobileScrollContext)
  const ref = useRef<HTMLElement>(null)
  useLayoutEffect(() => {
    if (manager && ref.current) return manager.attach(ref.current)
  }, [manager])
  // A query-only navigation preserves AppShell. Read its URL after each commit
  // without useSearchParams, which would add Suspense requirements to every page.
  useLayoutEffect(() => manager?.sync())
  return ref
}
