'use client'

import { useEffect, useRef, useState, type ReactNode } from 'react'

/** Load deeper research when it approaches the viewport, then keep it mounted. */
export default function DeferredPanel({ children, label }: { children: (enabled: boolean) => ReactNode; label: string }) {
  const container = useRef<HTMLDivElement>(null)
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    if (visible || !container.current) return
    if (!('IntersectionObserver' in window)) {
      setVisible(true)
      return
    }
    const panel = container.current
    const desktop = window.matchMedia('(min-width: 1024px)')
    let observer: IntersectionObserver | undefined
    const observe = () => {
      observer?.disconnect()
      observer = new IntersectionObserver((entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setVisible(true)
          observer?.disconnect()
        }
      }, {
        // Expand the actual scrolling viewport so mobile research starts loading
        // before entering the shell's clipped content area.
        root: desktop.matches ? null : panel.closest('.shell-main'),
        rootMargin: '400px 0px',
      })
      observer.observe(panel)
    }
    observe()
    desktop.addEventListener('change', observe)
    return () => {
      observer?.disconnect()
      desktop.removeEventListener('change', observe)
    }
  }, [visible])

  return (
    <div ref={container} className="relative">
      {!visible && <button type="button" onClick={() => setVisible(true)} className="sr-only focus:not-sr-only button-secondary">
        Load {label}
      </button>}
      {children(visible)}
    </div>
  )
}
