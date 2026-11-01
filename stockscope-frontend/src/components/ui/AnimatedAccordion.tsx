'use client'

import type { ReactNode } from 'react'
import { ChevronDown } from 'lucide-react'
import * as Accordion from '@animate-ui/react/primitives/radix-ui/accordion'

interface AnimatedAccordionProps {
  title: ReactNode
  children: ReactNode
  className?: string
  triggerClassName?: string
  defaultOpen?: boolean
  headerAction?: ReactNode
  headingLevel?: 2 | 3 | 4
}

/** Shared Animate UI disclosure with retained form state and inert closed content. */
export default function AnimatedAccordion({
  title,
  children,
  className = '',
  triggerClassName = '',
  defaultOpen = false,
  headerAction,
  headingLevel = 3,
}: AnimatedAccordionProps) {
  const Heading = `h${headingLevel}` as 'h2' | 'h3' | 'h4'

  return (
    <Accordion.Root type="single" collapsible defaultValue={defaultOpen ? 'content' : undefined} className={className}>
      <Accordion.Item value="content">
        <div className="flex items-center gap-2">
          <Accordion.Header asChild>
            <Heading className="min-w-0 flex-1">
              <Accordion.Trigger className={`group/accordion flex min-h-11 w-full items-center justify-between gap-3 rounded-md text-left hover:text-sage-200 ${triggerClassName}`}>
                <span className="min-w-0">{title}</span>
                <ChevronDown aria-hidden="true" className="h-4 w-4 shrink-0 text-slate-400 transition-transform duration-300 ease-out group-data-[state=open]/accordion:rotate-180 motion-reduce:transition-none" />
              </Accordion.Trigger>
            </Heading>
          </Accordion.Header>
          {headerAction && <div className="shrink-0">{headerAction}</div>}
        </div>
        <Accordion.Content forceMount className="overflow-hidden">
          <div className="flow-root">{children}</div>
        </Accordion.Content>
      </Accordion.Item>
    </Accordion.Root>
  )
}
