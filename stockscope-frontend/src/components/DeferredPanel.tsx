'use client'

import { useEffect, useRef, useState, type ReactNode } from 'react'

/** Load deeper research when it approaches the viewport, then keep it mounted. */
export default function DeferredPanel({ children, label }: { children: ReactNode; label: string }) {
  const container = useRef<HTMLDivElement>(null)
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    if (!container.current) return
    if (!('IntersectionObserver' in window)) {
      setVisible(true)
      return
    }
    const observer = new IntersectionObserver((entries) => {
      if (entries.some((entry) => entry.isIntersecting)) {
        setVisible(true)
        observer.disconnect()
      }
    }, { rootMargin: '400px 0px' })
    observer.observe(container.current)
    return () => observer.disconnect()
  }, [])

  return (
    <div ref={container}>
      {visible ? children : (
        <div className="surface flex min-h-64 items-center justify-center p-6">
          <button
            type="button"
            onClick={() => setVisible(true)}
            className="button-secondary"
          >
            Load {label}
          </button>
        </div>
      )}
    </div>
  )
}
