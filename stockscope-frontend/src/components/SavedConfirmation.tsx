'use client'

import { motion, useReducedMotion } from 'motion/react'
import { Check } from 'lucide-react'

export default function SavedConfirmation({ children }: { children: React.ReactNode }) {
  const reducedMotion = useReducedMotion()
  return <motion.span role="status" initial={reducedMotion ? false : { opacity: 0, scale: 0.85 }} animate={{ opacity: 1, scale: 1 }} transition={{ type: 'spring', stiffness: 400, damping: 22 }} className="inline-flex min-h-11 items-center gap-2 text-xs text-sage-300">
    <Check aria-hidden="true" className="h-4 w-4 shrink-0" />{children}
  </motion.span>
}
