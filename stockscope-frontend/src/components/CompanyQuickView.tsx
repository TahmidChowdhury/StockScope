'use client'

import { useEffect, useId, useRef, useState, type ReactNode } from 'react'
import Link from 'next/link'
import { ArrowUpRight, X } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import * as Popover from '@animate-ui/react/primitives/radix-ui/popover'
import { apiFetch } from '@/lib/api'
import { observed } from '@/lib/financial-format'
import { companyResearchHref } from '@/lib/research-workflow'
import type { StockMetadata } from '@/types'

export const shareClass = (symbol: string) => symbol === 'GOOGL' ? 'Class A' : symbol === 'GOOG' ? 'Class C' : null

function dateLabel(value?: string | null) {
  if (!value || Number.isNaN(Date.parse(value))) return 'Not available'
  return new Date(value).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' })
}

type Preview = {
  sentiment?: { avg_sentiment: number | null; sample_size: number }
  quote?: { price: number | null; currency: string | null; as_of: string | null }
}

/** Animate UI's anchored animation with hover intent and an accessible tap/focus popover. */
export default function CompanyQuickView({ stock, children }: { stock: Pick<StockMetadata, 'symbol'> & Partial<StockMetadata>; children: ReactNode }) {
  const [open, setOpen] = useState(false)
  const titleId = useId()
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const held = useRef(false)
  const restoreFocus = useRef(false)
  const content = useRef<HTMLDivElement>(null)
  const cancelTimer = () => { if (timer.current) clearTimeout(timer.current); timer.current = null }
  useEffect(() => () => { if (timer.current) clearTimeout(timer.current) }, [])
  const changeOpen = (next: boolean) => { cancelTimer(); setOpen(next); if (!next) { restoreFocus.current = held.current; held.current = false } }
  const leave = () => {
    cancelTimer()
    if (!held.current) timer.current = setTimeout(() => setOpen(false), 180)
  }
  const preview = useQuery({
    queryKey: ['company-preview', stock.symbol],
    enabled: open,
    queryFn: async ({ signal }): Promise<Preview> => {
      const response = await apiFetch(`/api/fundamentals/${encodeURIComponent(stock.symbol)}/preview`, { signal })
      if (!response.ok) throw new Error('Saved preview is unavailable.')
      return response.json()
    },
    staleTime: 5 * 60_000,
    refetchOnWindowFocus: false,
    retry: false,
  })
  const quote = preview.data?.quote
  const sentiment = preview.data?.sentiment ? preview.data.sentiment.avg_sentiment : stock.avg_sentiment
  const sampleSize = preview.data?.sentiment?.sample_size
  const kind = shareClass(stock.symbol)
  return <Popover.Root open={open} onOpenChange={changeOpen}>
    <Popover.Trigger asChild>
      <button type="button" aria-label={`Quick view ${stock.symbol}`} className="group/preview min-w-0 flex-1 basis-28 rounded-md text-left outline-none focus-visible:ring-2 focus-visible:ring-[#b6c8ab] focus-visible:ring-offset-4 focus-visible:ring-offset-[#171a22]"
        onPointerEnter={event => { if (event.pointerType !== 'mouse') return; cancelTimer(); timer.current = setTimeout(() => setOpen(true), 250) }}
        onPointerLeave={leave}
        onClick={event => { event.preventDefault(); held.current = true; changeOpen(true) }}
        onKeyDown={event => { if (event.key === 'ArrowDown') { event.preventDefault(); if (open) content.current?.focus(); else { held.current = true; changeOpen(true) } } }}>
        {children}
      </button>
    </Popover.Trigger>
    <Popover.Portal>
      <Popover.Content data-company-preview ref={content} tabIndex={-1} aria-labelledby={titleId} side="bottom" align="start" sideOffset={10} collisionPadding={16}
        transition={{ type: 'spring', stiffness: 320, damping: 30 }}
        className="z-[80] max-h-[var(--radix-popover-content-available-height)] w-80 max-w-[calc(100vw-32px)] overflow-y-auto rounded-2xl border border-white/15 bg-[#1b201d] p-4 text-slate-200 shadow-2xl shadow-black/50 outline-none"
        onOpenAutoFocus={event => event.preventDefault()}
        onCloseAutoFocus={event => { if (!restoreFocus.current) event.preventDefault() }}
        onPointerEnter={cancelTimer} onPointerLeave={leave}
        onFocusCapture={() => { held.current = true; cancelTimer() }}>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 id={titleId} className="text-lg font-semibold">{stock.symbol}{kind && <span className="ml-2 text-xs font-normal text-slate-400">{kind}</span>}</h3>
            {stock.companyName && stock.companyName !== stock.symbol && <p className="truncate text-xs text-slate-400">{stock.companyName}</p>}
          </div>
          <Popover.Close className="-mr-2 -mt-2 flex h-11 w-11 shrink-0 items-center justify-center rounded-lg hover:bg-white/5" aria-label="Close quick view"><X className="h-4 w-4" /></Popover.Close>
        </div>
        <dl className="mt-3 grid grid-cols-2 gap-3 border-y border-white/10 py-3 text-xs">
          <div>
            <dt className="text-slate-400">Saved stock price</dt>
            <dd className="mt-1 text-base tabular-nums">{observed(quote?.price)
              ? `${quote.price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${quote.currency ?? ''}`.trim()
              : preview.isPending ? 'Loading…' : 'Unavailable'}</dd>
            {observed(quote?.price) && <dd className="mt-1 text-slate-400">{quote.as_of ? dateLabel(quote.as_of) : 'Quote date unknown'}</dd>}
          </div>
          <div>
            <dt className="text-slate-400">Average news tone</dt>
            <dd className="mt-1 text-base">{observed(sentiment)
              ? sentiment >= 0.05 ? 'Positive' : sentiment <= -0.05 ? 'Negative' : 'Neutral'
              : preview.isPending ? 'Loading…' : preview.isError ? 'Unavailable' : 'Unscored'}</dd>
            {observed(sentiment) && sampleSize != null && <dd className="mt-1 text-slate-400">Across {sampleSize} scored {sampleSize === 1 ? 'article' : 'articles'}</dd>}
          </div>
        </dl>
        <Link href={companyResearchHref(stock.symbol, '', 'news')} prefetch={false}
          className="mt-1 flex min-h-11 items-center justify-between rounded-md text-sm font-medium text-[#b6c8ab] hover:underline focus-visible:outline-offset-2">
          View saved news sources<ArrowUpRight aria-hidden="true" className="h-4 w-4" />
        </Link>
      </Popover.Content>
    </Popover.Portal>
  </Popover.Root>
}
