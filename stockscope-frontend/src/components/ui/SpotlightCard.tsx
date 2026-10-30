'use client'

import { useRef, type ComponentPropsWithoutRef } from 'react'

// Aceternity-inspired spotlight, kept local to fit the workspace's surfaces.
// Pointer updates avoid React renders and never intercept the card's controls.
export default function SpotlightCard({
  children,
  className = '',
  selected = false,
  ...props
}: ComponentPropsWithoutRef<'article'> & { selected?: boolean }) {
  const card = useRef<HTMLElement>(null)

  return (
    <article
      {...props}
      ref={card}
      data-selected={selected || undefined}
      className={`spotlight-card group ${className}`}
      onPointerMove={(event) => {
        if (event.pointerType !== 'mouse') return
        const bounds = event.currentTarget.getBoundingClientRect()
        card.current?.style.setProperty('--spotlight-x', `${event.clientX - bounds.left}px`)
        card.current?.style.setProperty('--spotlight-y', `${event.clientY - bounds.top}px`)
      }}
    >
      {children}
    </article>
  )
}
