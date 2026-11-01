'use client'

import type { ComponentPropsWithoutRef } from 'react'

export default function SpotlightCard({
  children,
  className = '',
  selected = false,
  ...props
}: ComponentPropsWithoutRef<'article'> & { selected?: boolean }) {
  return (
    <article
      {...props}
      data-selected={selected || undefined}
      className={`spotlight-card group ${className}`}
    >
      {children}
    </article>
  )
}
